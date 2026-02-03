import asyncio
from pathlib import Path
from typing import Any, Dict, List

from _common import (
    build_arg_parser,
    call_openrouter,
    ensure_run_context,
    parse_numbered_list,
    search_ddg,
    scrape_urls,
    setup_logger,
    update_status,
    JsonStore,
    write_checkpoint,
)


def build_search_prompt(query: str) -> str:
    return (
        "Erstelle 10 präzise Suchbegriffe (nummerierte Liste) für die folgende Nutzerfrage. "
        "Vermeide Duplikate und nutze akademische Formulierungen.\n\n"
        f"Nutzerfrage: {query}"
    )


def build_questions_prompt(query: str, scraped_summary: str) -> str:
    return (
        "Du bist ein Research-Assistent. Stelle 5-8 gezielte Rückfragen, "
        "die nötig sind, um einen akademischen Forschungsplan zu erstellen. "
        "Nutze die Quellenzusammenfassung zur Einordnung.\n\n"
        f"Nutzerfrage: {query}\n\n"
        f"Quellenzusammenfassung:\n{scraped_summary}"
    )


def summarize_scrapes(scrapes: List[Dict[str, Any]]) -> str:
    summary_parts = []
    for entry in scrapes:
        if entry.get("success"):
            content = entry.get("content", "")
            summary_parts.append(f"URL: {entry['url']}\nInhalt: {content[:800]}\n")
        else:
            summary_parts.append(f"URL: {entry['url']}\nFehler: {entry.get('error', 'Unbekannt')}\n")
    return "\n".join(summary_parts)


def main() -> None:
    parser = build_arg_parser("Stage 1: Query -> Search terms -> URLs -> Scrape -> Questions")
    parser.add_argument("--query", required=True, help="User query to research")
    args = parser.parse_args()

    context = ensure_run_context(args.id, Path(args.output_root), "stage1")
    logger = setup_logger(context.log_file)
    store = JsonStore(context.output_root / context.run_id / context.stage, logger)

    update_status(store, "started", {"query": args.query})
    write_checkpoint(store, {"stage": "init", "query": args.query})

    logger.info("Generating search terms")
    search_prompt = build_search_prompt(args.query)
    search_response = call_openrouter(search_prompt, "search_terms", store, logger)
    terms = parse_numbered_list(search_response)
    if len(terms) < 10:
        terms.extend([args.query] * (10 - len(terms)))
    terms = terms[:10]

    store.write_named("search_terms.json", {"query": args.query, "terms": terms})
    write_checkpoint(store, {"stage": "search_terms", "terms": terms})

    logger.info("Searching DDG and collecting URLs")
    urls: List[str] = []
    search_results: List[Dict[str, Any]] = []
    for term in terms:
        results = asyncio.run(search_ddg(term, max_results=3))
        search_results.append({"term": term, "results": results})
        for result in results:
            url = result.get("url")
            if url and url not in urls:
                urls.append(url)
            if len(urls) >= 10:
                break
        if len(urls) >= 10:
            break

    store.write_named("search_results.json", {"query": args.query, "search_results": search_results})
    store.write_named("urls.json", {"urls": urls})
    write_checkpoint(store, {"stage": "urls", "urls": urls})

    logger.info("Scraping URLs (max concurrency 10)")
    scrapes = asyncio.run(scrape_urls(urls, logger))
    store.write_named("scrapes.json", {"scrapes": scrapes})
    write_checkpoint(store, {"stage": "scrapes", "count": len(scrapes)})

    summary = summarize_scrapes(scrapes)
    questions_prompt = build_questions_prompt(args.query, summary)
    questions_response = call_openrouter(questions_prompt, "clarification_questions", store, logger)
    questions = parse_numbered_list(questions_response)

    store.write_named(
        "questions.json",
        {"query": args.query, "questions": questions, "raw": questions_response},
    )

    final_payload = {
        "query": args.query,
        "terms": terms,
        "urls": urls,
        "scrapes": scrapes,
        "questions": questions,
    }
    store.write_named("final_output.json", final_payload)

    update_status(store, "completed", {"questions_count": len(questions)})
    logger.info("Stage 1 completed")


if __name__ == "__main__":
    main()
