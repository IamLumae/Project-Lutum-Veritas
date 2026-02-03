import asyncio
import re
from pathlib import Path
from typing import Any, Dict, List

from _common import (
    build_arg_parser,
    call_openrouter,
    ensure_run_context,
    load_json,
    parse_numbered_list,
    scrape_urls,
    search_ddg,
    setup_logger,
    update_status,
    JsonStore,
    write_checkpoint,
    MAX_SCRAPE_CONCURRENCY,
)


def slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9\-_. ]", "", text).strip().replace(" ", "_")
    return value[:60] if value else "section"


def build_section_queries_prompt(query: str, section: str) -> str:
    return (
        "Erstelle 3-5 präzise Suchanfragen für den folgenden Forschungsabschnitt. "
        "Gib sie als nummerierte Liste aus.\n\n"
        f"Nutzerfrage: {query}\n\n"
        f"Abschnitt: {section}"
    )


def build_section_dossier_prompt(query: str, section: str, sources: str) -> str:
    return (
        "Erstelle ein akademisches Dossier für den Abschnitt. "
        "Nutze die Quelleninhalte, bewerte Zuverlässigkeit, und gib wichtige Befunde strukturiert aus.\n\n"
        f"Nutzerfrage: {query}\n\n"
        f"Abschnitt: {section}\n\n"
        f"Quelleninhalte:\n{sources}"
    )


def build_synthesis_prompt(query: str, dossiers: List[Dict[str, Any]]) -> str:
    combined = "\n\n".join(
        f"Abschnitt: {dossier['section']}\n{dossier['dossier']}" for dossier in dossiers
    )
    return (
        "Erstelle eine akademische Synthese mit Schlussfolgerung. "
        "Strukturiere in: Zusammenfassung, zentrale Befunde, offene Fragen, finale Conclusion.\n\n"
        f"Nutzerfrage: {query}\n\n"
        f"Dossiers:\n{combined}"
    )


def summarize_scrapes(scrapes: List[Dict[str, Any]]) -> str:
    parts = []
    for entry in scrapes:
        if entry.get("success"):
            content = entry.get("content", "")
            parts.append(f"URL: {entry['url']}\nInhalt: {content[:1200]}\n")
        else:
            parts.append(f"URL: {entry['url']}\nFehler: {entry.get('error', 'Unbekannt')}\n")
    return "\n".join(parts)


async def run_section(
    query: str,
    section: str,
    index: int,
    total: int,
    output_dir: Path,
    logger,
    semaphore: asyncio.Semaphore,
) -> Dict[str, Any]:
    section_store = JsonStore(output_dir, logger)
    logger.info("Section %s/%s started: %s", index, total, section)

    query_prompt = build_section_queries_prompt(query, section)
    queries_response = await asyncio.to_thread(
        call_openrouter, query_prompt, f"section_queries_{index}", section_store, logger
    )
    queries = parse_numbered_list(queries_response)
    if not queries:
        queries = [section]

    section_store.write_named("queries.json", {"queries": queries, "raw": queries_response})

    urls: List[str] = []
    for term in queries:
        results = await search_ddg(term, max_results=3)
        for result in results:
            url = result.get("url")
            if url and url not in urls:
                urls.append(url)
            if len(urls) >= 10:
                break
        if len(urls) >= 10:
            break

    section_store.write_named("urls.json", {"urls": urls})

    scrapes = await scrape_urls(urls, logger, semaphore=semaphore)
    section_store.write_named("scrapes.json", {"scrapes": scrapes})

    sources_summary = summarize_scrapes(scrapes)
    dossier_prompt = build_section_dossier_prompt(query, section, sources_summary)
    dossier_response = await asyncio.to_thread(
        call_openrouter, dossier_prompt, f"section_dossier_{index}", section_store, logger
    )

    section_payload = {
        "section": section,
        "queries": queries,
        "urls": urls,
        "scrapes": scrapes,
        "dossier": dossier_response,
    }
    section_store.write_named("section_output.json", section_payload)

    logger.info("Section %s/%s completed", index, total)
    return section_payload


def main() -> None:
    parser = build_arg_parser("Stage 3: Research plan -> Deep research execution")
    parser.add_argument(
        "--plan-file",
        default=None,
        help="Optional path to stage2 plan.json",
    )
    args = parser.parse_args()

    context = ensure_run_context(args.id, Path(args.output_root), "stage3")
    logger = setup_logger(context.log_file)
    store = JsonStore(context.output_root / context.run_id / context.stage, logger)

    update_status(store, "started")

    plan_path = (
        Path(args.plan_file)
        if args.plan_file
        else context.output_root / context.run_id / "stage2" / "plan.json"
    )
    plan_payload = load_json(plan_path)
    query = plan_payload.get("query", "")
    plan_items = plan_payload.get("plan_items", [])
    if not plan_items:
        plan_items = parse_numbered_list(plan_payload.get("plan_raw", ""))

    store.write_named("inputs.json", {"query": query, "plan_items": plan_items})
    write_checkpoint(store, {"stage": "inputs_loaded", "plan_items": len(plan_items)})

    semaphore = asyncio.Semaphore(MAX_SCRAPE_CONCURRENCY)
    section_outputs: List[Dict[str, Any]] = []
    tasks = []

    for idx, section in enumerate(plan_items, 1):
        section_dir = store.base_dir / "sections" / f"{idx:02d}_{slugify(section)}"
        tasks.append(
            run_section(
                query,
                section,
                idx,
                len(plan_items),
                section_dir,
                logger,
                semaphore,
            )
        )

    async def run_all() -> List[Dict[str, Any]]:
        return await asyncio.gather(*tasks)

    section_outputs = asyncio.run(run_all())

    store.write_named("sections.json", {"sections": section_outputs})
    write_checkpoint(store, {"stage": "sections_completed", "sections": len(section_outputs)})

    synthesis_prompt = build_synthesis_prompt(query, section_outputs)
    synthesis_response = call_openrouter(synthesis_prompt, "final_synthesis", store, logger)

    final_payload = {
        "query": query,
        "plan_items": plan_items,
        "sections": section_outputs,
        "synthesis": synthesis_response,
    }
    store.write_named("final_output.json", final_payload)

    update_status(store, "completed", {"sections": len(section_outputs)})
    logger.info("Stage 3 completed")


if __name__ == "__main__":
    main()
