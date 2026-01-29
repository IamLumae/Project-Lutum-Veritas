"""
Search Module
=============
Step 2: Führt Queries auf 3 Engines aus für Diversifizierung.

Queries → DuckDuckGo + Google + Bing → Top Results → LLM picks URLs

NUTZT:
- duckduckgo-search Library für DDG
- search-engines-scraper für Google & Bing
Kein Browser nötig, stabil, schnell.
"""

import asyncio
import requests
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from lutum.core.log_config import get_logger
from lutum.core.api_config import get_api_key

logger = get_logger(__name__)


# === MULTI-ENGINE SEARCH ===
# 3 Engines für Diversifizierung: DDG, Google, Bing

def _search_ddg_sync(query: str, max_results: int = 20) -> list[dict]:
    """
    Führt eine DuckDuckGo Suche aus (sync).
    Nutzt ddgs Library (neue Version von duckduckgo-search).

    Args:
        query: Suchbegriff
        max_results: Anzahl Ergebnisse

    Returns:
        Liste von {title, url, snippet}
    """
    try:
        from ddgs import DDGS

        # Query bereinigen - keine Quotes, die verwirren DDG
        clean_query = query.strip().replace('"', '').replace("'", '')
        logger.debug(f"DDG search: {clean_query[:40]}...")

        # Suche ausführen mit neuer ddgs API
        with DDGS() as ddgs:
            results = list(ddgs.text(
                clean_query,  # Positional argument, nicht keyword!
                region="wt-wt",  # Worldwide
                safesearch="moderate",
                max_results=max_results
            ))

        # Zu unserem Format konvertieren
        formatted = []
        for r in results:
            formatted.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", "")
            })

        logger.info(f"DDG '{clean_query[:30]}...': {len(formatted)} results")
        return formatted

    except Exception as e:
        logger.error(f"DDG search failed: {query[:30]} - {e}")
        return []


async def _search_ddg_async(query: str, max_results: int = 20) -> list[dict]:
    """Async wrapper für DDG search."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search_ddg_sync, query, max_results)


def _search_google_sync(query: str, max_results: int = 20) -> list[dict]:
    """
    Führt eine Google Suche aus (sync).
    Nutzt search-engines-scraper Library.
    """
    try:
        from search_engines import Google

        clean_query = query.strip().replace('"', '').replace("'", '')
        logger.debug(f"Google search: {clean_query[:40]}...")

        engine = Google()
        results = engine.search(clean_query, pages=1)

        formatted = []
        for i, link in enumerate(results.links()):
            if i >= max_results:
                break
            # Titles und Snippets aus results extrahieren
            title = results.titles()[i] if i < len(results.titles()) else ""
            snippet = results.text()[i] if i < len(results.text()) else ""
            formatted.append({
                "title": title,
                "url": link,
                "snippet": snippet
            })

        logger.info(f"Google '{clean_query[:30]}...': {len(formatted)} results")
        return formatted

    except Exception as e:
        logger.warning(f"Google search failed: {query[:30]} - {e}")
        return []


def _search_bing_sync(query: str, max_results: int = 20) -> list[dict]:
    """
    Führt eine Bing Suche aus (sync).
    Nutzt search-engines-scraper Library.
    """
    try:
        from search_engines import Bing

        clean_query = query.strip().replace('"', '').replace("'", '')
        logger.debug(f"Bing search: {clean_query[:40]}...")

        engine = Bing()
        results = engine.search(clean_query, pages=1)

        formatted = []
        for i, link in enumerate(results.links()):
            if i >= max_results:
                break
            title = results.titles()[i] if i < len(results.titles()) else ""
            snippet = results.text()[i] if i < len(results.text()) else ""
            formatted.append({
                "title": title,
                "url": link,
                "snippet": snippet
            })

        logger.info(f"Bing '{clean_query[:30]}...': {len(formatted)} results")
        return formatted

    except Exception as e:
        logger.warning(f"Bing search failed: {query[:30]} - {e}")
        return []


async def _search_google_async(query: str, max_results: int = 20) -> list[dict]:
    """Async wrapper für Google search."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search_google_sync, query, max_results)


async def _search_bing_async(query: str, max_results: int = 20) -> list[dict]:
    """Async wrapper für Bing search."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search_bing_sync, query, max_results)


async def _execute_all_searches_async(queries: list[str], results_per_query: int = 20) -> dict[str, list[dict]]:
    """
    Führt alle Queries auf 3 Engines aus für Diversifizierung:
    DuckDuckGo, Google, Bing

    Kein Browser nötig - Libraries machen alles!

    Args:
        queries: Liste der Suchbegriffe
        results_per_query: Ergebnisse pro Query

    Returns:
        Dict {query: [results]} - Results von allen Engines gemerged & dedupliziert
    """
    import time as search_time

    logger.info(f"Executing {len(queries)} DDG searches...")
    start_time = search_time.time()

    all_results = {}

    # Nur DDG - Google/Bing sind unzuverlässig (0 results, redirect URLs)
    for i, query in enumerate(queries, 1):
        logger.info(f"[{i}/{len(queries)}] DDG: {query[:40]}...")
        results = await _search_ddg_async(query, results_per_query)
        all_results[query] = results
        logger.info(f"[{i}/{len(queries)}] {len(results)} results")

        # Längere Pause zwischen Queries um Rate-Limiting zu vermeiden
        if i < len(queries):
            await asyncio.sleep(1.5)

    total_results = sum(len(r) for r in all_results.values())
    duration = search_time.time() - start_time
    logger.info(f"DDG SEARCH COMPLETE: {total_results} results from {len(queries)} queries in {duration:.1f}s")

    return all_results


# Legacy function - wird von research.py aufgerufen
async def _close_google_session():
    """Legacy - nicht mehr nötig da kein Browser verwendet wird."""
    logger.debug("_close_google_session called (no-op, using duckduckgo-search library)")
    pass


# === CONFIG ===
MODEL = "google/gemini-2.5-flash-lite-preview-09-2025"


def _format_results_for_llm(search_results: dict[str, list[dict]]) -> str:
    """
    Formatiert Suchergebnisse für LLM-Prompt.

    Args:
        search_results: Dict {query: [results]}

    Returns:
        Formatierter String
    """
    logger.debug("Formatting search results for LLM")

    try:
        lines = []

        for query, results in search_results.items():
            lines.append(f"=== Query: {query} ===")

            if not results:
                lines.append("(keine Ergebnisse)")
            else:
                for i, r in enumerate(results, 1):
                    lines.append(f"{i}. {r['title']}")
                    lines.append(f"   URL: {r['url']}")
                    lines.append(f"   {r['snippet']}")

            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Result formatting failed: {e}")
        return "Fehler beim Formatieren der Ergebnisse."


# === LLM PROMPT (Query-Aware + Diversifiziert) ===
GET_INITIAL_DATA_PROMPT = """Du bist ein Experte für Quellenauswahl.

## KRITISCH: QUERY-AWARENESS (PFLICHT!)

Passe deine Auswahlstrategie an den AUFTRAG an:
- Wenn der User "unbekannte/kleine/nische/experimental" sucht → bevorzuge WENIGER offensichtliche Quellen, nicht die mit den meisten Stars
- Wenn der User "etablierte/Enterprise/bewährt/production-ready" sucht → bevorzuge bekannte, viel-referenzierte Quellen
- Wenn der User "akademisch/wissenschaftlich" sucht → priorisiere Papers und Forschung
- Wenn der User "praktisch/hands-on/tutorial" sucht → priorisiere Code-Beispiele und Guides

## DIVERSIFIZIERUNG (PFLICHT!)

Wähle URLs aus VERSCHIEDENEN Perspektiven:
- Nicht 5x GitHub, sondern: GitHub + Reddit + Paper + Blog + Docs
- Nicht 5x dasselbe Thema, sondern: verschiedene Aspekte abdecken

## AUSWAHLKRITERIEN

1. **Relevanz**: Passt die Quelle zum Auftrag?
2. **Qualität**: Fachquellen > Blogs > Foren
3. **Aktualität**: Neuere Quellen bevorzugen
4. **Vielfalt**: Verschiedene Perspektiven abdecken

## QUELLEN-RANKING

**Hochwertig:** GitHub Repos, Papers (arxiv), Offizielle Docs, Experten-Blogs
**Mittelwertig:** Medium/Dev.to, Reddit (wenn substantiell), Stack Overflow
**Vermeiden:** Generische Newsseiten, SEO-Spam, Veraltetes

---

URSPRÜNGLICHER AUFTRAG:
{user_message}

{context_block}

SUCHERGEBNISSE:
{search_results}

---

Wähle die besten URLs (max 10). FORMAT:
url 1: <url>
url 2: <url>
...
url 10: <url>
"""


def _call_llm_pick_urls(
    user_message: str,
    search_results: str,
    previous_learnings: list[str] | None = None,
    max_tokens: int = 1500
) -> Optional[str]:
    """
    LLM wählt beste URLs aus Suchergebnissen (Query-Aware + Kontext).

    Args:
        user_message: Ursprüngliche User-Anfrage
        search_results: Formatierte Suchergebnisse
        previous_learnings: Key Learnings aus vorherigen Dossiers (optional)
        max_tokens: Max Response Tokens

    Returns:
        LLM Response oder None
    """
    logger.debug("Calling LLM to pick URLs...")

    # Kontext-Block bauen wenn Learnings vorhanden
    if previous_learnings and len(previous_learnings) > 0:
        learnings_text = "\n".join(f"- {learning}" for learning in previous_learnings)
        context_block = f"""
BISHERIGE ERKENNTNISSE (aus vorherigen Recherchen):
{learnings_text}

WICHTIG: Wähle URLs die NEUE Informationen liefern, nicht dieselben nochmal!
"""
    else:
        context_block = ""

    prompt = GET_INITIAL_DATA_PROMPT.format(
        user_message=user_message,
        search_results=search_results,
        context_block=context_block
    )

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {get_api_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            },
            timeout=60
        )

        result = response.json()

        if "choices" not in result:
            logger.error(f"LLM error: {result}")
            return None

        answer = result["choices"][0]["message"]["content"]
        logger.info(f"LLM picked URLs: {len(answer)} chars response")
        logger.info(f"[SEARCH] RAW LLM RESPONSE:\n{answer}")
        return answer

    except requests.Timeout:
        logger.error("LLM timeout")
        return None

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return None


def _parse_urls(response: str) -> list[str]:
    """
    Parst URL-Liste aus LLM Response.
    Flexibler Parser - findet ALLE URLs in der Response.

    Args:
        response: LLM Response (beliebiges Format)

    Returns:
        Liste der URLs (dedupliziert, max 10)
    """
    import re
    logger.debug("Parsing URLs from LLM response")
    logger.debug(f"Response preview: {response[:200]}...")

    urls = []
    seen = set()

    try:
        # Finde ALLE URLs mit Regex
        url_pattern = r'https?://[^\s<>"\')\]]+[^\s<>"\')\].,;:!?]'
        matches = re.findall(url_pattern, response)

        for url in matches:
            # Bereinige URL (manchmal hängt Müll dran)
            url = url.rstrip('.,;:!?')
            if url not in seen and len(urls) < 10:
                urls.append(url)
                seen.add(url)
                logger.debug(f"Extracted URL: {url[:60]}...")

        logger.info(f"Parsed {len(urls)} URLs")
        logger.info(f"[SEARCH] PARSED URLs: {urls}")
        return urls

    except Exception as e:
        logger.error(f"URL parsing failed: {e}")
        return []


async def get_initial_data(
    user_message: str,
    queries: list[str],
    previous_learnings: list[str] | None = None
) -> dict:
    """
    Step 2: Sucht Queries und LLM wählt beste URLs (async, Query-Aware).

    Args:
        user_message: Ursprüngliche User-Anfrage
        queries: Liste der Search Queries aus Step 1
        previous_learnings: Key Learnings aus vorherigen Dossiers (optional, für Kontext)

    Returns:
        Dict mit:
            - urls_picked: Liste der ausgewählten URLs
            - search_results_raw: Rohe Suchergebnisse
            - llm_response: Rohe LLM Antwort
            - error: Fehlermeldung falls aufgetreten
    """
    logger.info(f"get_initial_data called: {len(queries)} queries")

    try:
        # Searches ausführen (async) - 20 results pro query für ~50-100 total
        search_results = await _execute_all_searches_async(queries, results_per_query=20)

        if not search_results or all(len(r) == 0 for r in search_results.values()):
            logger.warning("No search results found")
            return {
                "urls_picked": [],
                "search_results_raw": {},
                "llm_response": None,
                "error": "Keine Suchergebnisse gefunden"
            }

        # Für LLM formatieren
        formatted_results = _format_results_for_llm(search_results)

        # LLM picks URLs (mit Kontext wenn vorhanden)
        llm_response = _call_llm_pick_urls(user_message, formatted_results, previous_learnings)

        if not llm_response:
            return {
                "urls_picked": [],
                "search_results_raw": search_results,
                "llm_response": None,
                "error": "LLM call failed"
            }

        # URLs parsen
        urls = _parse_urls(llm_response)

        logger.info(f"Initial data complete: {len(urls)} URLs picked")

        return {
            "urls_picked": urls,
            "search_results_raw": search_results,
            "llm_response": llm_response,
            "error": None
        }

    except Exception as e:
        logger.error(f"get_initial_data failed: {e}")
        return {
            "urls_picked": [],
            "search_results_raw": {},
            "llm_response": None,
            "error": str(e)
        }


# === CLI TEST ===
if __name__ == "__main__":
    import asyncio

    test_queries = [
        "new RAG pipeline techniques github",
        "novel RAG compression methods",
    ]

    async def test():
        result = await get_initial_data("Find innovative RAG repos", test_queries)

        print("=" * 60)
        print("URLS PICKED:")
        print("=" * 60)

        for i, url in enumerate(result["urls_picked"], 1):
            print(f"  {i}. {url}")

        if result["error"]:
            print(f"\nError: {result['error']}")

    asyncio.run(test())
