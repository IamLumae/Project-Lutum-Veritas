"""
Step 4: Research Plan Generation
================================
LLM erstellt einen tiefgehenden Recherche-Plan basierend auf:
- User Query
- Rückfragen + Antworten

Output: Mindestens 5 Recherche-Punkte.
"""

import re
import requests
from typing import Optional
from lutum.core.log_config import get_logger
from lutum.core.api_config import get_api_key
from lutum.researcher.context_state import ContextState

logger = get_logger(__name__)

# OpenRouter Config
MODEL = "google/gemini-3-flash-preview"


PLAN_SYSTEM_PROMPT = """Du bist ein Research-Experte, der tiefe, reproduzierbare Recherche-Pläne erstellt.

Der User hat eine Frage gestellt und Rückfragen wurden bereits beantwortet.

DEIN ZIEL:
Erstelle einen Recherche-Plan, der so konkret ist, dass ein anderer Researcher ihn 1:1 ausführen kann
(inkl. Suchstrings, Filter, erwartete Deliverables).

═══════════════════════════════════════════════════════════════════
                         HARTREGELN (PFLICHT)
═══════════════════════════════════════════════════════════════════

- Ausgabe besteht NUR aus nummerierten Punkten: (1), (2), (3) ...
- Zwischen JEDEM Punkt: eine LEERE ZEILE.
- Jeder Punkt beginnt mit einem Verb (Suche, Recherchiere, Identifiziere, Prüfe, Untersuche, Vergleiche, Extrahiere, Validiere ...).
- Keine Einleitung, keine Meta-Erklärung, kein Fazit außerhalb der Punkte.
- Mindestens 5 Punkte; mehr wenn thematisch nötig.
- KEIN Scope-Drift: Halte Zeitfenster und Plattformen exakt ein.

═══════════════════════════════════════════════════════════════════
                         QUALITÄT (PFLICHT)
═══════════════════════════════════════════════════════════════════

Jeder Punkt MUSS diese Mini-Struktur enthalten:

a) **Ziel** (1 Satz): Was genau soll gefunden/überprüft werden?
b) **Suchstrings**: Mind. 2 konkrete Suchabfragen (mit Operatoren wenn sinnvoll)
c) **Filter/Constraints**: z.B. Zeitraum, Plattform, Sprache, etc.
d) **Output**: Welches Artefakt entsteht? (Liste, Tabelle, Vergleich)
e) **Validierung** (1 Satz): Wie prüfst du Relevanz/Qualität?

═══════════════════════════════════════════════════════════════════
                         LEDGER-TYPEN (Referenz)
═══════════════════════════════════════════════════════════════════

Schreibe in jedem Punkt, welches Ledger befüllt wird:

**Repo-Ledger** (für GitHub/GitLab):
Repo | Link | Technik/Keyword | Claim (1 Satz) | Evidenz-Snippet | Reifegrad | Notes

**Paper-Ledger** (für Arxiv/Papers):
Paper | Link | Jahr | Beitrag | Kernergebnis | Evidenz-Snippet | Limitations

**Thread-Ledger** (für Reddit/HN/Foren):
Plattform | Link | Thema | Hauptargument | Takeaway | Evidenz-Snippet | Credibility

**Issue-Ledger** (für GitHub Issues/PRs):
Projekt | Issue/PR | Status | Feature | Link | Notes

═══════════════════════════════════════════════════════════════════
                         BEISPIEL-FORMAT
═══════════════════════════════════════════════════════════════════

(1) Suche nach GitHub-Repositories für adaptive RAG-Chunking.
**Ziel:** Identifiziere aktive Open-Source-Projekte die dynamische Chunk-Größen implementieren.
**Suchstrings:** "adaptive chunking RAG" site:github.com, "dynamic chunk size langchain"
**Filter:** Nur Repos mit >10 Stars, letzter Commit <12 Monate
**Output:** Repo-Ledger mit 5-10 Einträgen
**Validierung:** Repo muss funktionierenden Code haben, nicht nur README.

(2) Recherchiere in r/LocalLLaMA nach Erfahrungsberichten zu Chunk-Strategien.
**Ziel:** Sammle praktische Erkenntnisse aus der Community zu Chunking-Problemen.
**Suchstrings:** "chunking" site:reddit.com/r/LocalLLaMA, "chunk size RAG reddit"
**Filter:** Posts der letzten 6 Monate, >10 Upvotes
**Output:** Thread-Ledger mit Bottlenecks und Workarounds
**Validierung:** Nur Threads mit konkreten Erfahrungen, keine Fragen ohne Antworten.

(3) ...usw."""


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> Optional[str]:
    """
    Ruft LLM via OpenRouter auf.
    """
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
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
            timeout=60
        )

        result = response.json()

        if "choices" not in result:
            logger.error(f"LLM error: {result}")
            return None

        answer = result["choices"][0]["message"]["content"]
        logger.info(f"[PLAN] RAW LLM RESPONSE:\n{answer[:2000]}...")
        return answer

    except requests.Timeout:
        logger.error("LLM timeout")
        return None
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return None


def create_research_plan(context: ContextState) -> dict:
    """
    Erstellt einen Recherche-Plan basierend auf dem Context State.

    Args:
        context: ContextState mit Query, Rückfragen und Antworten

    Returns:
        dict mit:
        - plan_points: Liste der Plan-Punkte
        - plan_text: Formatierter Plan-Text
        - raw_response: Rohe LLM Antwort
        - error: Fehlermeldung falls aufgetreten
    """
    logger.info("Creating research plan...")

    try:
        # Context für LLM formatieren
        context_text = context.format_for_llm()

        # Prompt zusammenbauen
        user_prompt = f"""{context_text}

Erstelle jetzt einen tiefgehenden Recherche-Plan (mindestens 5 Punkte).
Nutze das vorgegebene Format mit Ziel/Suchstrings/Filter/Output/Validierung pro Punkt."""

        logger.debug(f"Plan prompt length: {len(user_prompt)} chars")

        # LLM aufrufen via OpenRouter
        raw_response = _call_llm(PLAN_SYSTEM_PROMPT, user_prompt)

        if not raw_response:
            return {"error": "LLM call failed", "plan_points": []}

        logger.debug(f"Plan response: {raw_response[:200]}...")

        # Plan-Punkte parsen
        plan_points = _parse_plan_points(raw_response)

        if len(plan_points) < 5:
            logger.warning(f"Only {len(plan_points)} plan points found, expected at least 5")

        return {
            "plan_points": plan_points,
            "plan_text": _format_plan(plan_points),
            "raw_response": raw_response,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Plan generation failed: {e}", exc_info=True)
        return {"error": str(e), "plan_points": []}


def revise_research_plan(context: ContextState, user_feedback: str) -> dict:
    """
    Überarbeitet den Recherche-Plan basierend auf User-Feedback.

    Args:
        context: ContextState mit bestehendem Plan
        user_feedback: Was der User ändern möchte

    Returns:
        dict mit neuem Plan
    """
    logger.info(f"Revising research plan based on feedback: {user_feedback[:100]}...")

    try:
        # Context für LLM formatieren
        context_text = context.format_for_llm()

        # Prompt mit Feedback
        user_prompt = f"""{context_text}

=== USER FEEDBACK ZUM PLAN ===
{user_feedback}

Überarbeite den Recherche-Plan basierend auf dem Feedback.
Behalte was gut war, ändere was der User kritisiert hat.
Mindestens 5 Punkte, nummeriert mit (1), (2), etc.
Nutze das vorgegebene Format mit Ziel/Suchstrings/Filter/Output/Validierung pro Punkt."""

        # LLM aufrufen via OpenRouter
        raw_response = _call_llm(PLAN_SYSTEM_PROMPT, user_prompt)

        if not raw_response:
            return {"error": "LLM call failed", "plan_points": []}

        # Plan-Punkte parsen
        plan_points = _parse_plan_points(raw_response)

        return {
            "plan_points": plan_points,
            "plan_text": _format_plan(plan_points),
            "raw_response": raw_response,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Plan revision failed: {e}", exc_info=True)
        return {"error": str(e), "plan_points": []}


def _parse_plan_points(text: str) -> list[str]:
    """
    Parst nummerierte Plan-Punkte aus LLM-Output.

    Erwartet Format:
    (1) Erster Punkt...
    (2) Zweiter Punkt...

    Args:
        text: Roher LLM Output

    Returns:
        Liste der Plan-Punkte (ohne Nummerierung)
    """
    # Pattern: (1), (2), etc. am Zeilenanfang
    pattern = r'\((\d+)\)\s*(.+?)(?=\n\(\d+\)|\n\n|\Z)'
    matches = re.findall(pattern, text, re.DOTALL)

    points = []
    for num, content in matches:
        # Cleanup: Zeilenumbrüche zu Leerzeichen, trimmen
        clean_content = " ".join(content.split())
        if clean_content:
            points.append(clean_content)

    logger.debug(f"Parsed {len(points)} plan points")
    logger.info(f"[PLAN] PARSED POINTS: {len(points)} points")
    for i, p in enumerate(points, 1):
        logger.info(f"[PLAN] POINT {i}: {p[:100]}...")
    return points


def _format_plan(points: list[str]) -> str:
    """Formatiert Plan-Punkte für Anzeige."""
    if not points:
        return "Kein Plan erstellt."

    lines = []
    for i, point in enumerate(points, 1):
        lines.append(f"({i}) {point}")

    return "\n\n".join(lines)


# === CLI TEST ===
if __name__ == "__main__":
    # Test mit Dummy-Context
    ctx = ContextState()
    ctx.user_query = "Was sind die neuesten RAG-Techniken für LLMs?"
    ctx.clarification_questions = [
        "Welche spezifischen Aspekte interessieren dich?",
        "Hast du bereits Erfahrung mit RAG-Systemen?",
    ]
    ctx.clarification_answers = [
        "Komprimierung und Token-Reduktion",
        "Ja, grundlegende Kenntnisse mit LangChain",
    ]

    print("Context for LLM:")
    print("=" * 60)
    print(ctx.format_for_llm())
    print("=" * 60)

    result = create_research_plan(ctx)

    if result.get("error"):
        print(f"Error: {result['error']}")
    else:
        print(f"\nGenerated Plan ({len(result['plan_points'])} points):")
        print(result["plan_text"])
