"""
Clarify Module
==============
Step 3: Scraped Content analysieren + Rückfragen stellen.

URLs scrapen → Content + User Query an LLM → Rückfragen (wenn nötig)
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
    Formatiert Scrape-Ergebnisse für LLM.
    """
    logger.debug(f"Formatting {len(scraped)} scraped pages for LLM")

    try:
        lines = []

        for i, (url, content) in enumerate(scraped.items(), 1):
            lines.append(f"=== SEITE {i}: {url} ===")

            if content:
                if len(content) > max_chars_per_page:
                    content = content[:max_chars_per_page] + "\n[... gekürzt ...]"
                lines.append(content)
            else:
                lines.append("[Konnte nicht geladen werden]")

            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Format scraped failed: {e}")
        return "Fehler beim Formatieren."


# === LLM PROMPT ===
CLARIFY_PROMPT = """Du bist ein Research-Assistent. Der Nutzer hat einen Recherche-Auftrag gegeben.

WICHTIG - SPRACHLICHE ANPASSUNG: Wenn die ursprüngliche Nutzer-Anfrage auf Englisch formuliert wurde, antworte auf Englisch. Wenn sie auf Deutsch war, antworte auf Deutsch.

Du hast gerade eine erste Übersichtssuche durchgeführt und folgende Seiten gefunden und gelesen.

Deine Aufgabe jetzt:
1. Verstehe was der Nutzer wirklich will
2. Überlege ob du genug Informationen hast um loszulegen
3. Wenn nötig: Stelle bis zu 5 klärende Rückfragen

WICHTIG:
- Beginne IMMER positiv und motivierend (z.B. "Hey, spannende Idee!" oder "Interessanter Auftrag!" - oder auf Englisch wenn der User Englisch schreibt)
- Stelle NUR Fragen wenn wirklich nötig
- Fragen sollten helfen die Recherche zu fokussieren
- Keine Beispiele in den Fragen - der Nutzer soll frei antworten

FORMAT:
Beginne mit 1-2 Sätzen positiver Reaktion.
Dann wenn nötig: "Damit ich gezielt recherchieren kann, ein paar kurze Fragen:"
Dann nummerierte Fragen (max 5).
Wenn KEINE Fragen nötig: Sage dass du direkt loslegen kannst.

=== NUTZER-AUFTRAG ===
{user_message}

=== GEFUNDENE INFORMATIONEN ===
{scraped_content}

Deine Antwort:"""


def _call_llm_clarify(user_message: str, scraped_content: str, max_tokens: int = 2000) -> Tuple[Optional[str], Optional[str]]:
    """
    LLM analysiert Scrape-Ergebnisse und stellt Rückfragen.
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
    Step 3: Scraped URLs und stellt Rückfragen.

    Args:
        user_message: Ursprünglicher User-Auftrag
        urls: Liste der URLs aus Step 2

    Returns:
        Dict mit:
            - clarification: LLM Rückfragen/Antwort
            - scraped_content: Rohes Scrape-Ergebnis
            - success_count: Anzahl erfolgreicher Scrapes
            - error: Fehlermeldung falls aufgetreten
    """
    logger.info(f"get_clarification called: {len(urls)} URLs")

    try:
        # URLs scrapen - SEQUENZIELL mit 1 Browser (RAM-safe, keine parallelen Firefox!)
        scraped = await scrape_urls_batch(urls, timeout=20)

        success_count = len(scraped)

        if success_count == 0:
            logger.warning("No URLs could be scraped")
            return {
                "clarification": "Leider konnte ich keine der Seiten laden. Möchtest du es mit anderen Suchbegriffen versuchen?",
                "scraped_content": {},
                "success_count": 0,
                "error": "No URLs scraped successfully"
            }

        # Für LLM formatieren
        formatted = _format_scraped_for_llm(scraped)

        # LLM Rückfragen
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

    test_query = "Finde innovative RAG Repos"

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
