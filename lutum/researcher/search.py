"""
Search Module
=============
Step 2: Executes queries on search engines for diversification.

Queries → DuckDuckGo → Top Results → LLM picks URLs

USES:
- duckduckgo-search library for DDG
No browser needed, stable, fast.
"""

import asyncio
import requests
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from lutum.core.log_config import get_logger
from lutum.core.api_config import get_work_model
from lutum.core.llm_client import call_chat_completion

logger = get_logger(__name__)


# === SEARCH ENGINE ===

def _search_ddg_sync(query: str, max_results: int = 20) -> list[dict]:
    """
    Executes a DuckDuckGo search (sync).
    Uses ddgs library (new version of duckduckgo-search).

    Args:
        query: Search term
        max_results: Number of results

    Returns:
        List of {title, url, snippet}
    """
    try:
        from ddgs import DDGS

        # Clean query - no quotes, they confuse DDG
        clean_query = query.strip().replace('"', '').replace("'", '')
        logger.debug(f"DDG search: {clean_query[:40]}...")

        # Execute search with new ddgs API
        with DDGS() as ddgs:
            results = list(ddgs.text(
                clean_query,  # Positional argument, not keyword!
                region="wt-wt",  # Worldwide
                safesearch="moderate",
                max_results=max_results
            ))

        # Convert to our format
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
    """Async wrapper for DDG search."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search_ddg_sync, query, max_results)


async def _execute_all_searches_async(queries: list[str], results_per_query: int = 20) -> dict[str, list[dict]]:
    """
    Executes all queries on DDG.

    No browser needed - library handles everything!

    Args:
        queries: List of search terms
        results_per_query: Results per query

    Returns:
        Dict {query: [results]}
    """
    import time as search_time

    logger.info(f"Executing {len(queries)} DDG searches...")
    start_time = search_time.time()

    all_results = {}

    # Only DDG - Google/Bing are unreliable (0 results, redirect URLs)
    for i, query in enumerate(queries, 1):
        logger.info(f"[{i}/{len(queries)}] DDG: {query[:40]}...")
        results = await _search_ddg_async(query, results_per_query)
        all_results[query] = results
        logger.info(f"[{i}/{len(queries)}] {len(results)} results")

        # Longer pause between queries to avoid rate-limiting
        if i < len(queries):
            await asyncio.sleep(1.5)

    total_results = sum(len(r) for r in all_results.values())
    duration = search_time.time() - start_time
    logger.info(f"DDG SEARCH COMPLETE: {total_results} results from {len(queries)} queries in {duration:.1f}s")

    return all_results


# Legacy function - called by research.py
async def _close_google_session():
    """Legacy - no longer needed as no browser is used."""
    logger.debug("_close_google_session called (no-op, using duckduckgo-search library)")
    pass


# === CONFIG ===

def _format_results_for_llm(search_results: dict[str, list[dict]]) -> str:
    """
    Formats search results for LLM prompt.

    Args:
        search_results: Dict {query: [results]}

    Returns:
        Formatted string
    """
    logger.debug("Formatting search results for LLM")

    try:
        lines = []

        for query, results in search_results.items():
            lines.append(f"=== Query: {query} ===")

            if not results:
                lines.append("(no results)")
            else:
                for i, r in enumerate(results, 1):
                    lines.append(f"{i}. {r['title']}")
                    lines.append(f"   URL: {r['url']}")
                    lines.append(f"   {r['snippet']}")

            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Result formatting failed: {e}")
        return "Error formatting results."


# === LLM PROMPT (Query-Aware + Diversified) ===
# Split into SYSTEM + USER prompt like pick_urls.py

PICK_URLS_SYSTEM_PROMPT = """You select URLs from search results.

═══════════════════════════════════════════════════════════════════
                    OUTPUT FORMAT (MANDATORY!)
═══════════════════════════════════════════════════════════════════

RULE 1: NO ANALYSIS. NO EXPLANATION. ONLY URLS.
RULE 2: Start IMMEDIATELY with "=== SELECTED ===" - NO text before!
RULE 3: Each line: "url N: https://..." - nothing else.
RULE 4: EXACTLY 10 URLs. Not 3, not 5, not 9 - exactly 10.
RULE 5: The number of items in the user query is IRRELEVANT. If user asks about "3 tools" you still pick 10 URLs. If user asks about "5 companies" you still pick 10 URLs. ALWAYS 10.

═══════════════════════════════════════════════════════════════════
                    QUERY AWARENESS (MANDATORY!)
═══════════════════════════════════════════════════════════════════

Adapt your selection strategy to the TASK:
- "unknown/small/niche/experimental" → LESS obvious sources
- "established/enterprise/proven/production-ready" → known, highly-referenced sources
- "academic/scientific" → prioritize papers and research
- "practical/hands-on/tutorial" → prioritize code examples and guides

═══════════════════════════════════════════════════════════════════
                    DIVERSIFICATION (MANDATORY!)
═══════════════════════════════════════════════════════════════════

Select URLs from DIFFERENT perspectives:
- Not 5x GitHub, but: GitHub + Reddit + Paper + Blog + Docs
- Not 5x the same topic, but: cover different aspects

SOURCE MIX (distribution for 10 URLs):
- 2-3x Primary: Official docs, company blogs, papers
- 2-3x Community: Reddit, HN, forums, Stack Overflow
- 2-3x Practical: Tutorials, Medium, Dev.to, guides
- 2-3x Analysis: Comparisons, benchmarks, reviews

═══════════════════════════════════════════════════════════════════
                    SOURCE RANKING
═══════════════════════════════════════════════════════════════════

**High quality:** GitHub repos, papers (arxiv), official docs, expert blogs
**Medium quality:** Medium/Dev.to, Reddit (if substantial), Stack Overflow
**Avoid:** Generic news sites, SEO spam, outdated content"""

PICK_URLS_USER_PROMPT = """
# CONTEXT

## User Task
{user_message}

{context_block}

---

# SEARCH RESULTS

{search_results}

---

# TASK

Select EXACTLY 10 URLs. NO ANALYSIS. NO EXPLANATION. ONLY URLS.

CRITICAL: Start IMMEDIATELY with "=== SELECTED ===" - NO text before!

=== SELECTED ===
url 1:
url 2:
url 3:
url 4:
url 5:
url 6:
url 7:
url 8:
url 9:
url 10:
"""


def _call_llm_pick_urls(
    user_message: str,
    search_results: str,
    previous_learnings: list[str] | None = None,
    max_tokens: int = 1500
) -> Optional[str]:
    """
    LLM selects best URLs from search results (Query-Aware + Context).

    Args:
        user_message: Original user request
        search_results: Formatted search results
        previous_learnings: Key learnings from previous dossiers (optional)
        max_tokens: Max response tokens

    Returns:
        LLM response or None
    """
    logger.debug("Calling LLM to pick URLs...")

    # Build context block if learnings available
    if previous_learnings and len(previous_learnings) > 0:
        learnings_text = "\n".join(f"- {learning}" for learning in previous_learnings)
        context_block = f"""
PREVIOUS FINDINGS (from earlier research):
{learnings_text}

IMPORTANT: Select URLs that provide NEW information, not the same again!
"""
    else:
        context_block = ""

    user_prompt = PICK_URLS_USER_PROMPT.format(
        user_message=user_message,
        search_results=search_results,
        context_block=context_block
    )

    # DEBUG: Log FULL prompts sent to LLM
    logger.info(f"[SEARCH] ===== SYSTEM PROMPT =====\n{PICK_URLS_SYSTEM_PROMPT}")
    logger.info(f"[SEARCH] ===== USER PROMPT (first 3000 chars) =====\n{user_prompt[:3000]}")
    logger.info(f"[SEARCH] ===== USER PROMPT LENGTH: {len(user_prompt)} chars =====")

    result = call_chat_completion(
        messages=[
            {"role": "system", "content": PICK_URLS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        model=get_work_model(),
        max_tokens=max_tokens,
        timeout=60
    )

    if result.error:
        logger.error(f"LLM call failed: {result.error}")
        return None

    if not result.content:
        logger.error("LLM response empty")
        return None

    answer = str(result.content)
    logger.info(f"LLM picked URLs: {len(answer)} chars response")
    logger.info(f"[SEARCH] ===== FULL LLM RESPONSE =====\n{answer}")
    logger.info(f"[SEARCH] ===== RAW API RESULT =====\n{result.raw}")
    return answer


def _parse_urls(response: str) -> list[str]:
    """
    Parses URL list from LLM response.
    Flexible parser - finds ALL URLs in the response.

    Args:
        response: LLM response (any format)

    Returns:
        List of URLs (deduplicated, max 10)
    """
    import re
    logger.debug("Parsing URLs from LLM response")
    logger.debug(f"Response preview: {response[:200]}...")

    urls = []
    seen = set()

    try:
        # Find ALL URLs with regex
        url_pattern = r'https?://[^\s<>"\')\]]+[^\s<>"\')\].,;:!?]'
        matches = re.findall(url_pattern, response)

        for url in matches:
            # Clean URL (sometimes garbage hangs on)
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
    Step 2: Searches queries and LLM selects best URLs (async, Query-Aware).

    Args:
        user_message: Original user request
        queries: List of search queries from Step 1
        previous_learnings: Key learnings from previous dossiers (optional, for context)

    Returns:
        Dict with:
            - urls_picked: List of selected URLs
            - search_results_raw: Raw search results
            - llm_response: Raw LLM response
            - error: Error message if occurred
    """
    logger.info(f"get_initial_data called: {len(queries)} queries")

    try:
        # Execute searches (async) - 20 results per query for ~50-100 total
        search_results = await _execute_all_searches_async(queries, results_per_query=20)

        if not search_results or all(len(r) == 0 for r in search_results.values()):
            logger.warning("No search results found")
            return {
                "urls_picked": [],
                "search_results_raw": {},
                "llm_response": None,
                "error": "No search results found"
            }

        # Format for LLM
        formatted_results = _format_results_for_llm(search_results)

        # DEBUG: Log what we're sending to LLM
        logger.info(f"[SEARCH] Formatted results length: {len(formatted_results)} chars")
        logger.info(f"[SEARCH] First 2000 chars of search results:\n{formatted_results[:2000]}")

        # LLM picks URLs (with context if available)
        llm_response = _call_llm_pick_urls(user_message, formatted_results, previous_learnings)

        if not llm_response:
            return {
                "urls_picked": [],
                "search_results_raw": search_results,
                "llm_response": None,
                "error": "LLM call failed"
            }

        # Parse URLs
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
            logger.error("Error: %s", result["error"])

    asyncio.run(test())
