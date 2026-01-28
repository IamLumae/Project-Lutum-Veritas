"""
Overview Module
===============
Step 1: User Message → LLM → Search Queries

Bevor wir planen, holen wir uns erstmal eine Übersicht.
LLM analysiert was der User will und generiert Google Queries.
"""

import requests
from typing import Optional

from lutum.core.log_config import get_logger
from lutum.core.api_config import get_api_key

logger = get_logger(__name__)

# === CONFIG ===
MODEL = "google/gemini-3-flash-preview"


# === PROMPT ===
GET_OVERVIEW_PROMPT = """Du bekommst eine Nutzer-Anfrage. Deine Aufgabe:

1. Verstehe was der Nutzer will
2. Erstelle 10 Google-Suchanfragen mit PFLICHT-Diversifizierung
3. Gib einen kurzen Session-Titel (2-5 Wörter)

## REGELN:
- Englische Queries bevorzugen (mehr Ergebnisse)
- Session-Titel auf Deutsch, kurz und prägnant

## FORMAT (EXAKT SO - Kategorie ist PFLICHT!):

session: <kurzer titel 2-5 wörter>
query 1 (Primär): <offizielle Quelle, Docs, Repo, Paper>
query 2 (Primär): <offizielle Quelle, Docs, Repo, Paper>
query 3 (Community): <Reddit, HN, Forum, Diskussion>
query 4 (Community): <Reddit, HN, Forum, Diskussion>
query 5 (Praktisch): <Tutorial, How-to, Beispiel, Implementation>
query 6 (Praktisch): <Tutorial, How-to, Beispiel, Implementation>
query 7 (Kritisch): <Probleme, Limitationen, Alternativen, Vergleich>
query 8 (Kritisch): <Probleme, Limitationen, Alternativen, Vergleich>
query 9 (Aktuell): <News, 2024, 2025, neu, latest, Trends>
query 10 (Aktuell): <News, 2024, 2025, neu, latest, Trends>

Nutzer-Anfrage:
"""


def _parse_response(response: str) -> tuple[str, list[str]]:
    """
    Parst LLM Response zu Session-Titel und Queries.

    Args:
        response: LLM Response mit "session: ..." und "query N: ..." Format

    Returns:
        Tuple (session_title, queries_list)
    """
    logger.debug(f"Parsing response ({len(response)} chars)")

    session_title = ""
    queries = []

    try:
        for line in response.strip().split("\n"):
            line = line.strip()

            # Session-Titel extrahieren
            if line.lower().startswith("session:"):
                session_title = line.split(":", 1)[1].strip()
                logger.debug(f"Extracted session title: {session_title}")

            # Suche nach "query N:" Pattern
            elif line.lower().startswith("query"):
                # Alles nach dem ersten ":" nehmen
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


def _call_llm(user_message: str, max_tokens: int = 2000) -> Optional[str]:
    """
    Ruft LLM mit Get-Overview Prompt auf.

    Args:
        user_message: Die Nutzer-Anfrage
        max_tokens: Max Response Tokens

    Returns:
        LLM Response oder None bei Fehler
    """
    logger.debug(f"Calling LLM for overview: {user_message[:100]}...")

    full_prompt = GET_OVERVIEW_PROMPT + user_message

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {get_api_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "user", "content": full_prompt}
                ],
                "max_tokens": max_tokens
            },
            timeout=60
        )

        result = response.json()

        if "choices" not in result:
            logger.error(f"LLM error: {result}")
            return None

        answer = result["choices"][0]["message"]["content"]
        logger.info(f"LLM response: {len(answer)} chars")
        logger.info(f"[OVERVIEW] RAW LLM RESPONSE:\n{answer}")
        return answer

    except requests.Timeout:
        logger.error("LLM timeout (60s)")
        return None

    except requests.RequestException as e:
        logger.error(f"LLM request failed: {e}")
        return None

    except Exception as e:
        logger.error(f"LLM unexpected error: {e}")
        return None


def get_overview_queries(user_message: str) -> dict:
    """
    Step 1: Generiert Google Queries für Übersicht + Session-Titel.

    Args:
        user_message: Die ursprüngliche Nutzer-Anfrage

    Returns:
        Dict mit:
            - session_title: LLM-generierter Titel (2-5 Wörter)
            - queries_initial: Liste der generierten Queries
            - raw_response: Rohe LLM Antwort
            - error: Fehlermeldung falls aufgetreten
    """
    logger.info(f"get_overview_queries called: {user_message[:100]}...")

    try:
        # LLM aufrufen
        raw_response = _call_llm(user_message)

        if not raw_response:
            return {
                "session_title": "",
                "queries_initial": [],
                "raw_response": None,
                "error": "LLM call failed"
            }

        # Session-Titel + Queries parsen
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
