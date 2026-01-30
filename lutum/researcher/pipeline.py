"""
Pipeline Orchestrator (Setup-Phase)
===================================
Lädt und führt Steps 1-3 dynamisch aus (sync + async).

Architektur:
- Steps 1-3: Setup-Phase (Overview, Search, Clarify)
- Nach Step 3: User beantwortet Rückfragen, reviewed Plan
- Deep Research Loop: Wird direkt in research.py orchestriert (nicht hier)

Steps:
- step_01_overview.py → get_overview_queries()
- step_02_search.py → get_initial_data() [async]
- step_03_clarify.py → get_clarification()
"""

import asyncio
import inspect
from typing import Any, Optional, Callable
from lutum.core.log_config import get_logger

logger = get_logger(__name__)


# === STEP REGISTRY ===
# Hier werden alle Steps registriert - EINMAL.
# Neue Steps = hier hinzufügen, alte NICHT ändern.

STEPS = {
    1: {
        "name": "overview",
        "module": "lutum.researcher.overview",
        "function": "get_overview_queries",
        "input_key": "user_message",
        "output_key": "queries_initial",
    },
    2: {
        "name": "search",
        "module": "lutum.researcher.search",
        "function": "get_initial_data",
        "input_keys": ["user_message", "queries_initial"],
        "output_key": "urls_picked",
    },
    3: {
        "name": "clarify",
        "module": "lutum.researcher.clarify",
        "function": "get_clarification",
        "input_keys": ["user_message", "urls_picked"],
        "output_key": "clarification",
    },
    # Deep Research: Wird in research.py orchestriert (nicht hier)
}


def _load_step_function(step_config: dict) -> Optional[Callable]:
    """
    Lädt eine Step-Funktion dynamisch.

    Args:
        step_config: Step-Konfiguration aus STEPS

    Returns:
        Die Funktion oder None bei Fehler
    """
    module_name = step_config["module"]
    function_name = step_config["function"]

    logger.debug(f"Loading step: {module_name}.{function_name}")

    try:
        import importlib
        module = importlib.import_module(module_name)
        func = getattr(module, function_name)
        return func

    except ImportError as e:
        logger.error(f"Module not found: {module_name} - {e}")
        return None

    except AttributeError as e:
        logger.error(f"Function not found: {function_name} in {module_name} - {e}")
        return None

    except Exception as e:
        logger.error(f"Failed to load step: {e}")
        return None


async def _execute_step(step_num: int, context: dict) -> dict:
    """
    Führt einen einzelnen Step aus (sync oder async).

    Args:
        step_num: Step-Nummer (1, 2, 3, ...)
        context: Pipeline-Kontext mit allen bisherigen Daten

    Returns:
        Aktualisierter Kontext
    """
    if step_num not in STEPS:
        logger.error(f"Step {step_num} not found in registry")
        context["error"] = f"Step {step_num} not found"
        return context

    step_config = STEPS[step_num]
    step_name = step_config["name"]

    logger.info(f"=== STEP {step_num}: {step_name.upper()} ===")

    try:
        # Funktion laden
        func = _load_step_function(step_config)
        if not func:
            context["error"] = f"Failed to load step {step_num}"
            return context

        # Input vorbereiten
        if "input_keys" in step_config:
            # Mehrere Inputs
            args = [context.get(key) for key in step_config["input_keys"]]
            result = func(*args)
        elif "input_key" in step_config:
            # Einzelner Input
            input_val = context.get(step_config["input_key"])
            result = func(input_val)
        else:
            # Kein Input
            result = func()

        # Wenn async, awaiten
        if inspect.iscoroutine(result):
            result = await result

        # Result verarbeiten
        if isinstance(result, dict):
            # Step gibt dict zurück - alles in context mergen
            context.update(result)

            # Auch error checken
            if result.get("error"):
                logger.warning(f"Step {step_num} returned error: {result['error']}")
        else:
            # Step gibt einzelnen Wert zurück
            output_key = step_config.get("output_key", f"step_{step_num}_result")
            context[output_key] = result

        logger.info(f"Step {step_num} complete")
        return context

    except Exception as e:
        logger.error(f"Step {step_num} failed: {e}", exc_info=True)
        context["error"] = str(e)
        return context


# Step-spezifische Status-Messages (menschenfreundlich)
STEP_MESSAGES = {
    1: {
        "start": "Ich verschaffe mir eine Übersicht...",
        "done": "Übersicht erstellt",
    },
    2: {
        "start": "Ich durchsuche Google-Ergebnisse...",
        "done": "Vielversprechende Quellen gefunden",
    },
    3: {
        "start": "Ich lese die Quellen...",
        "done": "Erste Erkenntnisse gesammelt",
    },
}


async def run_pipeline(
    user_message: str,
    max_step: int = 3,
    on_status: Callable[[str, str], None] | None = None
) -> dict:
    """
    Führt die Research Pipeline bis zum angegebenen Step aus (async).

    Args:
        user_message: Die User-Anfrage
        max_step: Bis zu welchem Step ausführen (default: 3 = scrape)
        on_status: Optional callback für Status-Updates (event_type, message)

    Returns:
        Pipeline-Kontext mit allen Ergebnissen
    """
    logger.info(f"Pipeline started: max_step={max_step}")
    logger.info(f"User message: {user_message[:100]}...")

    def emit(event_type: str, message: str):
        """Helper für Status-Events."""
        if on_status:
            on_status(event_type, message)

    # Initialer Kontext
    context = {
        "user_message": user_message,
        "error": None,
    }

    emit("step_start", "Recherche gestartet...")

    try:
        # Steps durchlaufen
        for step_num in range(1, max_step + 1):
            if step_num not in STEPS:
                logger.warning(f"Step {step_num} not implemented yet")
                break

            # Status: Step startet
            step_msg = STEP_MESSAGES.get(step_num, {})
            emit("step_progress", step_msg.get("start", f"Step {step_num} läuft..."))

            context = await _execute_step(step_num, context)

            # Bei Fehler abbrechen
            if context.get("error"):
                emit("error", f"Fehler: {context['error']}")
                logger.error(f"Pipeline stopped at step {step_num}: {context['error']}")
                break

            # Status: Step fertig (mit Details)
            done_msg = step_msg.get("done", f"Step {step_num} fertig")
            if step_num == 1:
                count = len(context.get("queries_initial", []))
                emit("step_done", f"{done_msg} ({count} Suchanfragen)")
            elif step_num == 2:
                count = len(context.get("urls_picked", []))
                emit("step_done", f"{done_msg} ({count} URLs)")
            elif step_num == 3:
                count = context.get("success_count", 0)
                emit("step_done", f"{done_msg} ({count} Seiten)")
            else:
                emit("step_done", done_msg)

        emit("done", "Recherche abgeschlossen")
        logger.info(f"Pipeline complete: {len(context)} keys in context")
        return context

    except Exception as e:
        emit("error", f"Pipeline fehlgeschlagen: {e}")
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        context["error"] = str(e)
        return context


def format_pipeline_response(context: dict) -> str:
    """
    Formatiert Pipeline-Ergebnis für Chat-Anzeige.

    Args:
        context: Pipeline-Kontext

    Returns:
        Formatierter String
    """
    logger.debug("Formatting pipeline response")

    try:
        # Wenn Clarification vorhanden = Step 3 fertig
        # Dann NUR die Clarification zeigen (nicht den ganzen Debug-Kram)
        clarification = context.get("clarification")
        if clarification:
            return clarification

        # Fallback: Debug-Ausgabe für frühere Steps
        lines = []

        # Queries anzeigen
        queries = context.get("queries_initial", [])
        if queries:
            lines.append("**Recherche-Queries generiert:**")
            lines.append("")
            for i, q in enumerate(queries, 1):
                lines.append(f"{i}. {q}")
            lines.append("")

        # URLs anzeigen
        urls = context.get("urls_picked", [])
        if urls:
            lines.append("---")
            lines.append("")
            lines.append("**Ausgewählte URLs:**")
            lines.append("")
            for i, url in enumerate(urls, 1):
                lines.append(f"{i}. {url}")
            lines.append("")

        # Error anzeigen
        if context.get("error"):
            lines.append("---")
            lines.append("")
            lines.append(f"**Fehler:** {context['error']}")

        return "\n".join(lines) if lines else "Keine Ergebnisse."

    except Exception as e:
        logger.error(f"Format response failed: {e}")
        return f"Fehler beim Formatieren: {e}"


# === CLI TEST ===
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m lutum.researcher.pipeline \"<user message>\" [max_step]")
        sys.exit(1)

    user_msg = sys.argv[1]
    max_step = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    print(f"User Message: {user_msg}")
    print(f"Max Step: {max_step}")
    print("=" * 60)

    context = run_pipeline(user_msg, max_step)

    print("=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(format_pipeline_response(context))
