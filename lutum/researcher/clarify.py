"""
Clarify Module
==============
Step 3: Scraped Content analysieren + Rückfragen stellen.

URLs scrapen → Content + User Query an LLM → Rückfragen (wenn nötig)
"""

import asyncio
import requests
from typing import Optional

from lutum.core.log_config import get_logger
from lutum.core.api_config import get_api_key
from lutum.scrapers.camoufox_scraper import scrape_urls_batch

logger = get_logger(__name__)

# === CONFIG ===
MODEL = "google/gemini-3-flash-preview"


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

Du hast gerade eine erste Übersichtssuche durchgeführt und folgende Seiten gefunden und gelesen.

Deine Aufgabe jetzt:
1. Verstehe was der Nutzer wirklich will
2. Überlege ob du genug Informationen hast um loszulegen
3. Wenn nötig: Stelle bis zu 5 klärende Rückfragen

WICHTIG:
- Beginne IMMER positiv und motivierend (z.B. "Hey, spannende Idee!" oder "Interessanter Auftrag!")
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


def _call_llm_clarify(user_message: str, scraped_content: str, max_tokens: int = 2000) -> Optional[str]:
    """
    LLM analysiert Scrape-Ergebnisse und stellt Rückfragen.
    """
    logger.debug("Calling LLM for clarification...")

    prompt = CLARIFY_PROMPT.format(
        user_message=user_message,
        scraped_content=scraped_content
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
        logger.info(f"LLM clarification: {len(answer)} chars")
        logger.info(f"[CLARIFY] RAW LLM RESPONSE:\n{answer}")
        return answer

    except requests.Timeout:
        logger.error("LLM timeout")
        return None

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return None


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
        clarification = _call_llm_clarify(user_message, formatted)

        if not clarification:
            return {
                "clarification": None,
                "scraped_content": scraped,
                "success_count": success_count,
                "error": "LLM call failed"
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
