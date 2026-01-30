"""
Overview Module
===============
Step 1: User Message → LLM → Search Queries

Before we plan, we first get an overview.
LLM analyzes what the user wants and generates Google queries.
"""

from typing import Optional, Tuple

from lutum.core.log_config import get_logger
from lutum.core.api_config import get_work_model
from lutum.core.llm_client import call_chat_completion

logger = get_logger(__name__)


# === PROMPT ===
GET_OVERVIEW_PROMPT = """You receive a user request. Your task:

1. Understand what the user wants
2. Create 10 Google search queries with MANDATORY diversification
3. Provide a short session title (2-5 words)

## RULES:
- Prefer English queries (more results)
- Session title should be concise and descriptive

## FORMAT (EXACTLY LIKE THIS - Category is MANDATORY!):

session: <short title 2-5 words>
query 1 (Primary): <official source, docs, repo, paper>
query 2 (Primary): <official source, docs, repo, paper>
query 3 (Community): <Reddit, HN, forum, discussion>
query 4 (Community): <Reddit, HN, forum, discussion>
query 5 (Practical): <tutorial, how-to, example, implementation>
query 6 (Practical): <tutorial, how-to, example, implementation>
query 7 (Critical): <problems, limitations, alternatives, comparison>
query 8 (Critical): <problems, limitations, alternatives, comparison>
query 9 (Current): <news, 2024, 2025, new, latest, trends>
query 10 (Current): <news, 2024, 2025, new, latest, trends>

CRITICAL: The session title must be in the SAME LANGUAGE as the user's request below.

User request:
"""


def _parse_response(response: str) -> tuple[str, list[str]]:
    """
    Parses LLM response to session title and queries.

    Args:
        response: LLM Response with "session: ..." and "query N: ..." format

    Returns:
        Tuple (session_title, queries_list)
    """
    logger.debug(f"Parsing response ({len(response)} chars)")

    session_title = ""
    queries = []

    try:
        for line in response.strip().split("\n"):
            line = line.strip()

            # Extract session title
            if line.lower().startswith("session:"):
                session_title = line.split(":", 1)[1].strip()
                logger.debug(f"Extracted session title: {session_title}")

            # Search for "query N:" pattern
            elif line.lower().startswith("query"):
                # Take everything after the first ":"
                if ":" in line:
                    query = line.split(":", 1)[1].strip()
                    if query:
                        queries.append(query)
                        logger.debug(f"Extracted query: {query[:50]}...")

        logger.info(f"Parsed session='{session_title}', {len(queries)} queries")
        logger.info(f"[OVERVIEW] PARSED QUERIES: {queries}")
        return session_title, queries

    except Exception as e:
        logger.error(f"Response parsing failed: {e}")
        return "", []


def _call_llm(user_message: str, max_tokens: int = 2000) -> Tuple[Optional[str], Optional[str]]:
    """
    Calls LLM with Get-Overview prompt.

    Args:
        user_message: The user request
        max_tokens: Max response tokens

    Returns:
        LLM response or None on error
    """
    logger.debug(f"Calling LLM for overview: {user_message[:100]}...")

    full_prompt = GET_OVERVIEW_PROMPT + user_message

    result = call_chat_completion(
        messages=[{"role": "user", "content": full_prompt}],
        model=get_work_model(),
        max_tokens=max_tokens,
        timeout=60
    )

    if result.error:
        return None, result.error

    if not result.content:
        return None, "LLM response empty"

    answer = str(result.content)
    logger.info(f"LLM response: {len(answer)} chars")
    logger.info(f"[OVERVIEW] RAW LLM RESPONSE:\n{answer}")
    return answer, None


def get_overview_queries(user_message: str) -> dict:
    """
    Step 1: Generates Google queries for overview + session title.

    Args:
        user_message: The original user request

    Returns:
        Dict with:
            - session_title: LLM-generated title (2-5 words)
            - queries_initial: List of generated queries
            - raw_response: Raw LLM response
            - error: Error message if occurred
    """
    logger.info(f"get_overview_queries called: {user_message[:100]}...")

    try:
        # Call LLM
        raw_response, error_message = _call_llm(user_message)

        if not raw_response:
            return {
                "session_title": "",
                "queries_initial": [],
                "raw_response": None,
                "error": error_message or "LLM call failed"
            }

        # Parse session title + queries
        session_title, queries = _parse_response(raw_response)

        if not queries:
            logger.warning("No queries extracted from response")
            return {
                "session_title": session_title,
                "queries_initial": [],
                "raw_response": raw_response,
                "error": "No queries extracted"
            }

        logger.info(f"Overview complete: '{session_title}', {len(queries)} queries generated")

        return {
            "session_title": session_title,
            "queries_initial": queries,
            "raw_response": raw_response,
            "error": None
        }

    except Exception as e:
        logger.error(f"get_overview_queries failed: {e}")
        return {
            "session_title": "",
            "queries_initial": [],
            "raw_response": None,
            "error": str(e)
        }


# === CLI TEST ===
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m lutum.researcher.overview \"<user message>\"")
        sys.exit(1)

    user_msg = " ".join(sys.argv[1:])
    print(f"User Message: {user_msg}\n")

    result = get_overview_queries(user_msg)

    print("=" * 60)
    print("QUERIES INITIAL:")
    print("=" * 60)

    for i, q in enumerate(result["queries_initial"], 1):
        print(f"  {i}. {q}")

    if result["error"]:
        print(f"\nError: {result['error']}")
