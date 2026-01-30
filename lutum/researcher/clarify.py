"""
Clarify Module
==============
Step 3: Analyze scraped content + ask follow-up questions.

Scrape URLs → Content + User Query to LLM → Follow-up questions (if needed)
"""

import asyncio
from typing import Optional, Tuple

from lutum.core.log_config import get_logger
from lutum.core.api_config import get_work_model
from lutum.core.llm_client import call_chat_completion
from lutum.scrapers.camoufox_scraper import scrape_urls_batch

logger = get_logger(__name__)


def _format_scraped_for_llm(scraped: dict[str, str], max_chars_per_page: int = 3000) -> str:
    """
    Formats scrape results for LLM.
    """
    logger.debug(f"Formatting {len(scraped)} scraped pages for LLM")

    try:
        lines = []

        for i, (url, content) in enumerate(scraped.items(), 1):
            lines.append(f"=== PAGE {i}: {url} ===")

            if content:
                if len(content) > max_chars_per_page:
                    content = content[:max_chars_per_page] + "\n[... truncated ...]"
                lines.append(content)
            else:
                lines.append("[Could not load]")

            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Format scraped failed: {e}")
        return "Error formatting content."


# === LLM PROMPT ===
CLARIFY_PROMPT = """You are a research assistant. The user has given a research task.

You have just performed an initial overview search and found and read the following pages.

Your task now:
1. Understand what the user really wants
2. Consider whether you have enough information to start
3. If necessary: Ask up to 5 clarifying follow-up questions

IMPORTANT:
- ALWAYS begin positively and encouragingly (e.g. "Great question!" or "Interesting topic!")
- ONLY ask questions if truly necessary
- Questions should help focus the research
- No examples in the questions - let the user answer freely

FORMAT:
Begin with 1-2 sentences of positive reaction.
Then if needed: Transition to follow-up questions (e.g. "To focus my research effectively, a few quick questions:")
Then numbered questions (max 5).
If NO questions needed: Say that you can start right away.

=== USER TASK ===
{user_message}

=== FOUND INFORMATION ===
{scraped_content}

CRITICAL: Your response must ALWAYS be in the SAME LANGUAGE as the user's task above. If the user wrote in German, respond in German. If in English, respond in English.

Your response:"""


def _call_llm_clarify(user_message: str, scraped_content: str, max_tokens: int = 4000) -> Tuple[Optional[str], Optional[str]]:
    """
    LLM analyzes scrape results and asks follow-up questions.
    """
    logger.debug("Calling LLM for clarification...")

    prompt = CLARIFY_PROMPT.format(
        user_message=user_message,
        scraped_content=scraped_content
    )

    result = call_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        model=get_work_model(),
        max_tokens=max_tokens,
        timeout=60
    )

    if result.error:
        return None, result.error

    if not result.content:
        return None, "LLM response empty"

    answer = str(result.content)
    logger.info(f"LLM clarification: {len(answer)} chars")
    logger.info(f"[CLARIFY] RAW LLM RESPONSE:\n{answer}")
    return answer, None


async def get_clarification(user_message: str, urls: list[str]) -> dict:
    """
    Step 3: Scrape URLs and ask follow-up questions.

    Args:
        user_message: Original user task
        urls: List of URLs from Step 2

    Returns:
        Dict with:
            - clarification: LLM follow-up questions/response
            - scraped_content: Raw scrape result
            - success_count: Number of successful scrapes
            - error: Error message if occurred
    """
    logger.info(f"get_clarification called: {len(urls)} URLs")

    try:
        # Scrape URLs - SEQUENTIAL with 1 browser (RAM-safe, no parallel Firefox!)
        scraped = await scrape_urls_batch(urls, timeout=20)

        success_count = len(scraped)

        if success_count == 0:
            logger.warning("No URLs could be scraped")
            return {
                "clarification": "Unfortunately I couldn't load any of the pages. Would you like to try with different search terms?",
                "scraped_content": {},
                "success_count": 0,
                "error": "No URLs scraped successfully"
            }

        # Format for LLM
        formatted = _format_scraped_for_llm(scraped)

        # LLM follow-up questions
        clarification, error_message = _call_llm_clarify(user_message, formatted)

        if not clarification:
            return {
                "clarification": None,
                "scraped_content": scraped,
                "success_count": success_count,
                "error": error_message or "LLM call failed"
            }

        logger.info(f"Clarification complete: {success_count} pages scraped")

        return {
            "clarification": clarification,
            "scraped_content": scraped,
            "success_count": success_count,
            "error": None
        }

    except Exception as e:
        logger.error(f"get_clarification failed: {e}")
        return {
            "clarification": None,
            "scraped_content": {},
            "success_count": 0,
            "error": str(e)
        }


# === CLI TEST ===
if __name__ == "__main__":
    import sys

    test_urls = [
        "https://github.com/NirDiamant/RAG_Techniques",
        "https://github.com/HKUDS/LightRAG",
    ]

    test_query = "Find innovative RAG repos"

    async def test():
        result = await get_clarification(test_query, test_urls)
        print("=" * 60)
        print("CLARIFICATION:")
        print("=" * 60)
        print(result["clarification"])
        print(f"\nScraped: {result['success_count']} pages")
        if result["error"]:
            print(f"Error: {result['error']}")

    asyncio.run(test())
