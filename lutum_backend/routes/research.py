"""
Research Endpoint
=================
Endpoint für die Research Pipeline.

Step 1: User Message → Overview Queries
SSE Events für Fortschrittsanzeige
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

if __package__ is None or __package__ == '':
    # Script Mode (development)
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
else:
    # Package Mode (production / installed)
    # lutum package is already installed, so we don't need to mess with sys.path for it
    pass

from lutum.core.log_config import get_logger, get_and_clear_log_buffer
from lutum.core.api_config import get_api_headers, set_api_config
from lutum.researcher.overview import get_overview_queries
from lutum.researcher.pipeline import run_pipeline, format_pipeline_response
from lutum.researcher.context_state import ContextState
from lutum.researcher.plan import create_research_plan, revise_research_plan
from lutum.researcher.prompts import (
    build_think_prompt,
    parse_think_response,
    build_pick_urls_prompt,
    parse_pick_urls_response,
    build_dossier_prompt,
    parse_dossier_response,
    build_final_synthesis_prompt,
    FINAL_SYNTHESIS_MODEL,
    FINAL_SYNTHESIS_TIMEOUT,
)

logger = get_logger(__name__)
router = APIRouter(tags=["Research"])


# === i18n STATUS MESSAGES ===
# All user-facing status messages in DE and EN
STATUS_MESSAGES = {
    # Pipeline (Step 1-3)
    "getting_overview": {"de": "Ich verschaffe mir eine Übersicht...", "en": "Getting an overview..."},
    "overview_done": {"de": "Übersicht erstellt ({count} Suchanfragen)", "en": "Overview complete ({count} search queries)"},
    "searching_google": {"de": "Ich durchsuche Google...", "en": "Searching Google..."},
    "sources_found": {"de": "Quellen gefunden ({count} URLs)", "en": "Sources found ({count} URLs)"},
    "reading_sources": {"de": "Ich lese die Quellen...", "en": "Reading sources..."},
    "sources_analyzed": {"de": "Quellen analysiert ({count} Seiten)", "en": "Sources analyzed ({count} pages)"},

    # Deep Research
    "deep_research_start": {"de": "Starte Deep Research mit {count} Punkten...", "en": "Starting Deep Research with {count} points..."},
    "developing_strategy": {"de": "[{idx}] Entwickle Suchstrategie...", "en": "[{idx}] Developing search strategy..."},
    "think_failed": {"de": "[{idx}] Think fehlgeschlagen, überspringe...", "en": "[{idx}] Think failed, skipping..."},
    "no_queries": {"de": "[{idx}] Keine Suchqueries generiert", "en": "[{idx}] No search queries generated"},
    "searches_planned": {"de": "[{idx}] {count} Suchen geplant", "en": "[{idx}] {count} searches planned"},
    "searching": {"de": "[{idx}] Durchsuche Google...", "en": "[{idx}] Searching Google..."},
    "no_results": {"de": "[{idx}] Keine Suchergebnisse", "en": "[{idx}] No search results"},
    "selecting_sources": {"de": "[{idx}] Wähle beste Quellen...", "en": "[{idx}] Selecting best sources..."},
    "few_results_retry": {"de": "[{idx}] Wenige Ergebnisse - reformuliere Suche...", "en": "[{idx}] Few results - reformulating search..."},
    "retry_with_new": {"de": "[{idx}] Retry mit {count} neuen Suchen...", "en": "[{idx}] Retry with {count} new searches..."},
    "no_urls_skip": {"de": "[{idx}] Keine URLs gefunden, überspringe Punkt", "en": "[{idx}] No URLs found, skipping point"},
    "urls_selected": {"de": "[{idx}] {count} URLs ausgewählt", "en": "[{idx}] {count} URLs selected"},
    "reading": {"de": "[{idx}] Lese Quellen...", "en": "[{idx}] Reading sources..."},
    "no_content": {"de": "[{idx}] Keine Inhalte gescraped", "en": "[{idx}] No content scraped"},
    "sources_read": {"de": "[{idx}] {count} Quellen gelesen", "en": "[{idx}] {count} sources read"},
    "creating_dossier": {"de": "[{idx}] Erstelle Dossier...", "en": "[{idx}] Creating dossier..."},
    "dossier_failed": {"de": "[{idx}] Dossier-Erstellung fehlgeschlagen", "en": "[{idx}] Dossier creation failed"},
    "dossier_done": {"de": "[{idx}] Dossier fertig!", "en": "[{idx}] Dossier complete!"},

    # Final Synthesis
    "starting_synthesis": {"de": "Starte finale Synthese...", "en": "Starting final synthesis..."},
    "combining_dossiers": {"de": "Kombiniere {count} Dossiers zu Gesamtdokument...", "en": "Combining {count} dossiers into final document..."},
    "synthesis_failed_fallback": {"de": "Final Synthesis fehlgeschlagen, nutze Fallback...", "en": "Final synthesis failed, using fallback..."},
    "research_complete": {"de": "Recherche abgeschlossen in {duration}s", "en": "Research complete in {duration}s"},

    # Academic Mode
    "academic_start": {"de": "Academic Mode: {bereiche} Bereiche mit {points} Punkten", "en": "Academic Mode: {bereiche} areas with {points} points"},
    "academic_complete": {"de": "Academic Research abgeschlossen in {duration}s", "en": "Academic Research complete in {duration}s"},

    # Session Resume
    "session_resumed": {"de": "Session fortgesetzt: {done}/{total} Dossiers fertig, {remaining} noch offen", "en": "Session resumed: {done}/{total} dossiers complete, {remaining} remaining"},

    # PICK event
    "pick_point": {"de": "PICK: Punkt {idx}/{total} → {title}", "en": "PICK: Point {idx}/{total} → {title}"},
    "remaining": {"de": "Verbleibend: {count} Punkte", "en": "Remaining: {count} points"},
}


def t(key: str, lang: str = "de", **kwargs) -> str:
    """
    Translate a status message key to the specified language.

    Args:
        key: Message key from STATUS_MESSAGES
        lang: Language code ("de" or "en"), defaults to "de"
        **kwargs: Format arguments for the message

    Returns:
        Translated and formatted message string
    """
    if key not in STATUS_MESSAGES:
        logger.warning(f"Missing translation key: {key}")
        return key

    msg = STATUS_MESSAGES[key].get(lang, STATUS_MESSAGES[key].get("de", key))
    try:
        return msg.format(**kwargs) if kwargs else msg
    except KeyError as e:
        logger.warning(f"Missing format arg for {key}: {e}")
        return msg


def flush_log_buffer():
    """
    Yields SSE events for any buffered WARN/ERROR logs.
    Call this periodically in streaming endpoints to surface backend errors to user.

    Yields:
        JSON strings with {"type": "log", "level": "WARNING|ERROR", "message": "..."}
    """
    logs = get_and_clear_log_buffer()
    for log in logs:
        yield json.dumps({
            "type": "log",
            "level": log["level"],
            "message": log["short"],
            "full": log["message"]
        }) + "\n"

# === EVENT BUS ===
# Globale Queue für SSE Events - Frontend hört zu
_event_queues: dict[str, asyncio.Queue] = {}


def emit_event(session_id: str, event_type: str, message: str):
    """
    Sendet Event an alle Listener einer Session.

    Args:
        session_id: Session ID (Frontend sendet diese)
        event_type: z.B. "step_start", "step_done", "error"
        message: Anzeigetext für Frontend
    """
    if session_id in _event_queues:
        try:
            _event_queues[session_id].put_nowait({
                "type": event_type,
                "message": message
            })
            logger.debug(f"Event emitted: {session_id} -> {event_type}: {message}")
        except asyncio.QueueFull:
            logger.warning(f"Event queue full for session {session_id}")


@router.get("/research/events/{session_id}")
async def research_events(session_id: str):
    """
    SSE Endpoint - Frontend verbindet sich hier für Live-Updates.

    Args:
        session_id: Session ID für die Events empfangen werden

    Returns:
        StreamingResponse mit SSE Events
    """
    logger.info(f"SSE connection opened for session: {session_id}")

    # Queue für diese Session erstellen (falls nicht schon vom POST-Handler erstellt)
    if session_id not in _event_queues:
        _event_queues[session_id] = asyncio.Queue(maxsize=100)
        logger.debug(f"Created event queue for session {session_id} in SSE handler")

    async def event_generator():
        import json
        try:
            # Initial "connected" Event (JSON format!)
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Verbunden'})}\n\n"

            while True:
                try:
                    # Warte auf Event mit Timeout (keep-alive)
                    event = await asyncio.wait_for(
                        _event_queues[session_id].get(),
                        timeout=30.0
                    )
                    # JSON statt Python dict!
                    yield f"data: {json.dumps({'type': event['type'], 'message': event['message']})}\n\n"

                    # Bei "done" Event beenden
                    if event["type"] == "done":
                        break

                except asyncio.TimeoutError:
                    # Keep-alive ping
                    yield f"data: {json.dumps({'type': 'ping', 'message': ''})}\n\n"

        finally:
            # Cleanup
            if session_id in _event_queues:
                del _event_queues[session_id]
            logger.info(f"SSE connection closed for session: {session_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


class OverviewRequest(BaseModel):
    """
    Request Body für /research/overview.

    Attributes:
        message: User Nachricht / Auftrag
        session_id: Session ID für Events (optional)
        api_key: OpenRouter API Key
    """
    message: str = Field(..., description="User Nachricht / Research-Auftrag", max_length=10000)
    session_id: Optional[str] = Field(None, description="Session ID für SSE Events", max_length=100)
    api_key: str = Field(..., description="OpenRouter API Key", max_length=200)
    provider: str = Field("openrouter", description="API Provider", max_length=50)
    work_model: str = Field("google/gemini-2.5-flash-lite-preview-09-2025", description="LLM Modell", max_length=100)
    base_url: str = Field("https://openrouter.ai/api/v1/chat/completions", description="API Base URL")


class OverviewResponse(BaseModel):
    """
    Response Body für /research/overview.

    Attributes:
        session_title: LLM-generierter Session-Titel (2-5 Wörter)
        queries_initial: Liste der generierten Google Queries
        raw_response: Rohe LLM Antwort
        error: Fehlermeldung falls aufgetreten
    """
    session_title: str = Field("", description="LLM-generierter Session-Titel")
    queries_initial: list[str] = Field(default_factory=list, description="Generierte Search Queries")
    raw_response: Optional[str] = Field(None, description="Rohe LLM Antwort")
    error: Optional[str] = Field(None, description="Fehlermeldung")


@router.post("/research/overview", response_model=OverviewResponse)
async def research_overview(request: OverviewRequest):
    """
    Step 1: Generiert Overview Queries.

    Nimmt User-Nachricht, LLM analysiert und erstellt
    bis zu 10 Google Queries für Übersicht.

    Args:
        request: OverviewRequest mit message

    Returns:
        OverviewResponse mit queries_initial Liste
    """
    logger.debug(f"Research overview request: {request.message[:100] if request.message else 'EMPTY'}...")

    # API Config setzen für alle LLM Calls
    set_api_config(
        key=request.api_key,
        provider=request.provider,
        work_model=request.work_model,
        base_url=request.base_url
    )

    try:
        if not request.message or not request.message.strip():
            logger.warning("Empty message received")
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        sid = request.session_id

        # Event: Start
        if sid:
            emit_event(sid, "step_start", "Nachricht empfangen...")

        # Event: LLM analysiert
        if sid:
            emit_event(sid, "step_progress", "LLM analysiert deine Anfrage...")

        # Overview Queries generieren
        result = get_overview_queries(request.message)

        # Event: Done
        if sid:
            query_count = len(result.get('queries_initial', []))
            emit_event(sid, "step_done", f"Step 1 fertig: {query_count} Suchanfragen generiert")

        logger.info(f"Overview response: {len(result.get('queries_initial', []))} queries")

        return OverviewResponse(
            session_title=result.get("session_title", ""),
            queries_initial=result.get("queries_initial", []),
            raw_response=result.get("raw_response"),
            error=result.get("error")
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Research overview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# === FULL PIPELINE ENDPOINT ===

class PipelineRequest(BaseModel):
    """Request für vollständige Pipeline."""
    message: str = Field(..., description="User Nachricht / Research-Auftrag", max_length=10000)
    session_id: Optional[str] = Field(None, description="Session ID für SSE Events", max_length=100)
    max_step: int = Field(3, ge=1, le=5, description="Bis zu welchem Step ausführen (default 3)")
    api_key: str = Field(..., description="OpenRouter API Key", max_length=200)
    language: str = Field("de", description="Language for status messages (de/en)")
    provider: str = Field("openrouter", description="API Provider", max_length=50)
    work_model: str = Field("google/gemini-2.5-flash-lite-preview-09-2025", description="LLM Modell", max_length=100)
    base_url: str = Field("https://openrouter.ai/api/v1/chat/completions", description="API Base URL")


class PipelineResponse(BaseModel):
    """Response der vollständigen Pipeline."""
    session_title: str = Field("", description="LLM-generierter Session-Titel")
    response: str = Field("", description="Formatierte Antwort (Clarification oder Debug)")
    queries_count: int = Field(0, description="Anzahl generierter Queries")
    urls_count: int = Field(0, description="Anzahl gepickter URLs")
    scraped_count: int = Field(0, description="Anzahl erfolgreich gescrapeter Seiten")
    error: Optional[str] = Field(None, description="Fehlermeldung")


@router.post("/research/run")
async def research_run(request: PipelineRequest):
    """
    Vollständige Research Pipeline ausführen - STREAMING.

    Sendet JSON-Lines für Status-Updates zwischen Steps.
    Frontend liest Stream und zeigt Status-Messages im Chat.

    Format:
    {"type": "status", "message": "Ich verschaffe mir eine Übersicht..."}
    {"type": "done", "data": {...}}
    """
    import json
    from lutum.researcher.overview import get_overview_queries
    from lutum.researcher.search import get_initial_data, _close_google_session
    from lutum.researcher.clarify import get_clarification

    logger.info(f"Pipeline request (streaming): {request.message[:100] if request.message else 'EMPTY'}...")

    async def generate():
        # API Config setzen für alle LLM Calls
        set_api_config(
            key=request.api_key,
            provider=request.provider,
            work_model=request.work_model,
            base_url=request.base_url
        )
        lang = request.language

        try:
            if not request.message or not request.message.strip():
                yield json.dumps({"type": "error", "message": "Message cannot be empty"}) + "\n"
                return

            user_message = request.message
            context = {"user_message": user_message, "error": None}

            # === STEP 1: Overview ===
            yield json.dumps({"type": "status", "message": t("getting_overview", lang)}) + "\n"

            result1 = get_overview_queries(user_message)
            context.update(result1)

            if context.get("error"):
                for log_event in flush_log_buffer():
                    yield log_event
                yield json.dumps({"type": "error", "message": context["error"]}) + "\n"
                return

            queries = context.get("queries_initial", [])
            yield json.dumps({"type": "status", "message": t("overview_done", lang, count=len(queries))}) + "\n"

            # === STEP 2: Search ===
            if request.max_step >= 2:
                yield json.dumps({"type": "status", "message": t("searching_google", lang)}) + "\n"

                result2 = await get_initial_data(user_message, queries)
                context.update(result2)

                # RAM-Cleanup: Browser killen nach Search
                await _close_google_session()
                logger.info("Browser session closed (RAM cleanup)")

                if context.get("error"):
                    for log_event in flush_log_buffer():
                        yield log_event
                    yield json.dumps({"type": "error", "message": context["error"]}) + "\n"
                    return

                urls = context.get("urls_picked", [])
                yield json.dumps({"type": "status", "message": t("sources_found", lang, count=len(urls))}) + "\n"

                # Sources Event mit URL-Liste für Frontend
                if urls:
                    yield json.dumps({"type": "sources", "urls": urls, "message": t("sources_found", lang, count=len(urls))}) + "\n"

            # === STEP 3: Clarify ===
            if request.max_step >= 3:
                urls = context.get("urls_picked", [])
                if urls:
                    yield json.dumps({"type": "status", "message": t("reading_sources", lang)}) + "\n"

                    result3 = await get_clarification(user_message, urls)
                    context.update(result3)

                    scraped = context.get("success_count", 0)
                    yield json.dumps({"type": "status", "message": t("sources_analyzed", lang, count=scraped)}) + "\n"

            # Response formatieren
            response_text = format_pipeline_response(context)

            # Flush any buffered logs before done
            for log_event in flush_log_buffer():
                yield log_event

            # Finale Response
            yield json.dumps({
                "type": "done",
                "data": {
                    "session_title": context.get("session_title", ""),
                    "response": response_text,
                    "queries_count": len(context.get("queries_initial", [])),
                    "urls_count": len(context.get("urls_picked", [])),
                    "scraped_count": context.get("success_count", 0),
                    "error": context.get("error")
                }
            }) + "\n"

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            # Security: Don't expose internal error details to client
            for log_event in flush_log_buffer():
                yield log_event
            yield json.dumps({"type": "error", "message": "Research pipeline failed. Please try again."}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )


# === STEP 4: RESEARCH PLAN ===

class PlanRequest(BaseModel):
    """Request für Plan-Erstellung (Step 4)."""
    user_query: str = Field(..., description="Ursprüngliche User-Anfrage", max_length=10000)
    clarification_questions: list[str] = Field(default_factory=list, description="Rückfragen aus Step 3")
    clarification_answers: list[str] = Field(..., description="User-Antworten auf Rückfragen")
    session_id: Optional[str] = Field(None, description="Session ID für SSE Events", max_length=100)
    api_key: str = Field(..., description="OpenRouter API Key", max_length=200)
    academic_mode: bool = Field(False, description="Academic Mode: Hierarchische Bereiche statt flacher Liste")
    provider: str = Field("openrouter", description="API Provider", max_length=50)
    work_model: str = Field("google/gemini-2.5-flash-lite-preview-09-2025", description="LLM Modell", max_length=100)
    base_url: str = Field("https://openrouter.ai/api/v1/chat/completions", description="API Base URL")


class PlanResponse(BaseModel):
    """Response mit Recherche-Plan."""
    plan_points: list[str] = Field(default_factory=list, description="Plan-Punkte (Normal Mode)")
    plan_text: str = Field("", description="Formatierter Plan-Text")
    context_state: dict = Field(default_factory=dict, description="Aktueller Context State")
    academic_bereiche: Optional[dict] = Field(None, description="Hierarchische Bereiche (Academic Mode)")
    error: Optional[str] = Field(None, description="Fehlermeldung")


@router.post("/research/plan", response_model=PlanResponse)
async def research_plan(request: PlanRequest):
    """
    Step 4: Recherche-Plan erstellen.

    Normal Mode: Flache Liste von Punkten
    Academic Mode: Hierarchische Bereiche mit Unterpunkten

    Args:
        request: PlanRequest mit Query, Rückfragen, Antworten, academic_mode

    Returns:
        PlanResponse mit Plan-Punkten oder academic_bereiche
    """
    mode_str = "ACADEMIC" if request.academic_mode else "NORMAL"
    logger.info(f"Plan request ({mode_str}): {request.user_query[:100]}...")

    # API Config setzen
    set_api_config(
        key=request.api_key,
        provider=request.provider,
        work_model=request.work_model,
        base_url=request.base_url
    )

    try:
        sid = request.session_id

        # Status Event
        if sid:
            emit_event(sid, "step_start", f"Erstelle {'Academic' if request.academic_mode else ''} Recherche-Plan...")

        # Context State aufbauen
        context = ContextState()
        context.user_query = request.user_query
        context.clarification_questions = request.clarification_questions
        context.clarification_answers = request.clarification_answers

        if sid:
            emit_event(sid, "step_progress", "Analysiere deine Antworten...")

        # === ACADEMIC MODE: Hierarchische Bereiche ===
        if request.academic_mode:
            from lutum.researcher.prompts import create_academic_plan, format_academic_plan

            result = create_academic_plan(context)

            if result.get("error"):
                if sid:
                    emit_event(sid, "error", f"Academic Plan fehlgeschlagen: {result['error']}")
                return PlanResponse(error=result["error"])

            bereiche = result.get("bereiche", {})
            total_points = sum(len(points) for points in bereiche.values())

            # Context State mit academic_bereiche setzen
            context_dict = context.to_dict()
            context_dict["academic_bereiche"] = bereiche

            if sid:
                emit_event(sid, "step_done", f"Academic Plan: {len(bereiche)} Bereiche, {total_points} Punkte")
                emit_event(sid, "done", "Warte auf deine Entscheidung...")

            return PlanResponse(
                plan_points=[],  # Leer bei Academic Mode
                plan_text=result.get("plan_text", ""),
                context_state=context_dict,
                academic_bereiche=bereiche,
                error=None
            )

        # === NORMAL MODE: Flache Liste ===
        else:
            result = create_research_plan(context)

            if result.get("error"):
                if sid:
                    emit_event(sid, "error", f"Plan-Erstellung fehlgeschlagen: {result['error']}")
                return PlanResponse(error=result["error"])

            # Plan in Context State setzen
            context.set_plan(result["plan_points"])

            if sid:
                emit_event(sid, "step_done", f"Plan erstellt ({len(result['plan_points'])} Punkte)")
                emit_event(sid, "done", "Warte auf deine Entscheidung...")

            return PlanResponse(
                plan_points=result["plan_points"],
                plan_text=result["plan_text"],
                context_state=context.to_dict(),
                academic_bereiche=None,
                error=None
            )

    except Exception as e:
        logger.error(f"Plan creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


class PlanReviseRequest(BaseModel):
    """Request für Plan-Überarbeitung."""
    context_state: dict = Field(..., description="Aktueller Context State")
    feedback: str = Field(..., description="User-Feedback zum Plan", max_length=5000)
    session_id: Optional[str] = Field(None, description="Session ID für SSE Events", max_length=100)
    api_key: str = Field(..., description="OpenRouter API Key", max_length=200)
    provider: str = Field("openrouter", description="API Provider", max_length=50)
    work_model: str = Field("google/gemini-2.5-flash-lite-preview-09-2025", description="LLM Modell", max_length=100)
    base_url: str = Field("https://openrouter.ai/api/v1/chat/completions", description="API Base URL")


@router.post("/research/plan/revise", response_model=PlanResponse)
async def research_plan_revise(request: PlanReviseRequest):
    """
    Plan überarbeiten basierend auf User-Feedback.

    Args:
        request: PlanReviseRequest mit Context State und Feedback

    Returns:
        PlanResponse mit überarbeitetem Plan
    """
    logger.info(f"Plan revision request: {request.feedback[:100]}...")

    # API Config setzen
    set_api_config(
        key=request.api_key,
        provider=request.provider,
        work_model=request.work_model,
        base_url=request.base_url
    )

    try:
        sid = request.session_id

        if sid:
            emit_event(sid, "step_start", "Überarbeite Plan...")

        # Context State laden
        context = ContextState.from_dict(request.context_state)

        if sid:
            emit_event(sid, "step_progress", "Verarbeite dein Feedback...")

        # Plan überarbeiten
        result = revise_research_plan(context, request.feedback)

        if result.get("error"):
            if sid:
                emit_event(sid, "error", f"Plan-Überarbeitung fehlgeschlagen: {result['error']}")
            return PlanResponse(error=result["error"])

        # Neuen Plan in Context State setzen
        context.set_plan(result["plan_points"])

        if sid:
            emit_event(sid, "step_done", f"Plan überarbeitet (v{context.plan_version})")
            emit_event(sid, "done", "Warte auf deine Entscheidung...")

        return PlanResponse(
            plan_points=result["plan_points"],
            plan_text=result["plan_text"],
            context_state=context.to_dict(),
            error=None
        )

    except Exception as e:
        logger.error(f"Plan revision failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# === STEP 5: DEEP RESEARCH ORCHESTRATOR ===

class DeepResearchRequest(BaseModel):
    """Request für Deep Research Pipeline."""
    context_state: dict = Field(..., description="Context State mit Plan")
    session_id: Optional[str] = Field(None, description="Session ID für SSE Events", max_length=100)
    api_key: str = Field(..., description="API Key", max_length=200)
    provider: str = Field("openrouter", description="API Provider", max_length=50)
    work_model: str = Field("google/gemini-2.5-flash-lite-preview-09-2025", description="Modell für Vorarbeit (Think, Pick URLs, Dossier)", max_length=100)
    final_model: str = Field("qwen/qwen3-vl-235b-a22b-instruct", description="Modell für Final Synthesis", max_length=100)
    language: str = Field("de", description="Language for status messages (de/en)")
    base_url: str = Field("https://openrouter.ai/api/v1/chat/completions", description="API Base URL")


class DeepResearchResponse(BaseModel):
    """Response der Deep Research Pipeline."""
    final_document: str = Field("", description="Finales Dokument")
    total_points: int = Field(0, description="Anzahl abgearbeiteter Punkte")
    total_sources: int = Field(0, description="Anzahl genutzter Quellen")
    duration_seconds: float = Field(0.0, description="Gesamtdauer in Sekunden")
    error: Optional[str] = Field(None, description="Fehlermeldung")


@router.post("/research/deep")
async def research_deep(request: DeepResearchRequest):
    """
    Step 5: Deep Research Pipeline - STREAMING.

    Orchestriert die vollständige Recherche:
    1. Für jeden Punkt im Plan:
       - Think (Suchstrategie)
       - Google Search (parallel)
       - Pick URLs
       - Scrape URLs (parallel)
       - Dossier erstellen
       - Key Learnings extrahieren → an nächste Punkte
    2. Final Synthesis (alle Dossiers → Gesamtdokument)

    Events:
    - {"type": "status", "message": "..."}
    - {"type": "sources", "urls": [...], "message": "..."}
    - {"type": "point_complete", "point_title": "...", "point_number": N, "total_points": M, "key_learnings": "..."}
    - {"type": "done", "data": {...}}
    """
    import json
    import time
    import requests
    from lutum.researcher.search import _execute_all_searches_async, _close_google_session
    from lutum.scrapers.camoufox_scraper import scrape_urls_batch

    # LLM Config - aus Request übernehmen
    MODEL_FAST = request.work_model
    MODEL_FINAL = request.final_model
    BASE_URL = request.base_url

    def call_llm(system_prompt: str, user_prompt: str, model: str = MODEL_FAST, timeout: int = 60, max_tokens: int = 8000) -> Optional[str]:
        """Ruft LLM auf (OpenRouter, OpenAI, Anthropic, Google, HuggingFace)."""
        try:
            response = requests.post(
                BASE_URL,
                headers=get_api_headers(),
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": max_tokens
                },
                timeout=timeout
            )
            result = response.json()
            if "choices" in result:
                choice = result["choices"][0]
                message = choice.get("message", {})
                content = message.get("content")
                finish_reason = choice.get("finish_reason", "unknown")

                # Debug: Log wenn content fehlt oder leer ist
                if content is None:
                    logger.warning(f"LLM returned null content (finish_reason={finish_reason}, refusal={message.get('refusal', 'none')}, model={model})")
                elif not content.strip():
                    logger.warning(f"LLM returned empty string (finish_reason={finish_reason}, model={model})")
                return content
            logger.error(f"LLM error (no choices): {result}")
            return None
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    async def scrape_urls_parallel(urls: list[str], timeout: int = 15) -> dict[str, str]:
        """Scraped URLs sequenziell aber schnell (15s timeout statt 45s)."""
        return await scrape_urls_batch(urls, timeout=timeout)

    logger.info("Deep Research Pipeline started")
    start_time = time.time()

    # API Config setzen für alle LLM Calls
    set_api_config(
        key=request.api_key,
        provider=request.provider,
        work_model=request.work_model,
        final_model=request.final_model,
        base_url=request.base_url
    )

    # === CHECKPOINT SYSTEM ===
    import hashlib

    def get_session_id(plan: list[str], user_query: str) -> str:
        """Generiert eindeutige Session-ID aus Plan + Query."""
        content = user_query + "|||" + "|||".join(plan)
        return hashlib.sha1(content.encode()).hexdigest()[:12]

    def get_checkpoint_dir(session_id: str) -> Path:
        """Gibt Checkpoint-Verzeichnis für Session zurück."""
        base_dir = Path(__file__).parent.parent.parent / "research_checkpoints"
        return base_dir / session_id

    def save_checkpoint(session_id: str, data: dict):
        """Speichert Checkpoint für Session."""
        checkpoint_dir = get_checkpoint_dir(session_id)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_file = checkpoint_dir / "checkpoint.json"
        checkpoint_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"[CHECKPOINT] Saved for session {session_id}: {len(data.get('completed_dossiers', []))} dossiers")

    def load_checkpoint(session_id: str) -> Optional[dict]:
        """Lädt Checkpoint für Session."""
        checkpoint_file = get_checkpoint_dir(session_id) / "checkpoint.json"
        if checkpoint_file.exists():
            return json.loads(checkpoint_file.read_text(encoding="utf-8"))
        return None

    async def generate():
        lang = request.language
        try:
            # Context State laden
            context = ContextState.from_dict(request.context_state)
            research_plan = context.research_plan

            if not research_plan or len(research_plan) == 0:
                yield json.dumps({"type": "error", "message": "No research plan" if lang == "en" else "Kein Recherche-Plan vorhanden"}) + "\n"
                return

            user_query = context.user_query

            # Check ob Resume
            is_resume = "_resumed_from" in request.context_state
            completed_dossiers = request.context_state.get("_completed_dossiers", []) if is_resume else []
            accumulated_learnings = request.context_state.get("_accumulated_learnings", []) if is_resume else []
            all_sources = []

            # === GLOBALE SOURCE REGISTRY ===
            # Trackt alle gepickten URLs mit globaler Nummerierung für Citations
            # Problem: Jedes Dossier nummeriert [1], [2], [3] lokal
            # Lösung: Nach jedem Dossier die lokalen Nummern durch globale ersetzen
            source_registry: dict[int, str] = {}  # {1: "url1", 2: "url2", ...}
            source_counter = 1  # Globaler Zähler

            def renumber_citations(text: str, local_urls: list[str], start_num: int) -> tuple[str, int]:
                """
                Ersetzt lokale [1], [2], [3] durch globale Nummern [start_num], [start_num+1], ...

                Returns:
                    (renumbered_text, next_available_number)
                """
                import re
                result = text
                current_num = start_num

                # Finde alle lokalen Citation-Nummern im Text
                local_nums = set(int(m) for m in re.findall(r'\[(\d+)\]', text))

                # Mapping: lokal → global
                local_to_global = {}
                for local_num in sorted(local_nums):
                    local_to_global[local_num] = current_num
                    current_num += 1

                # Ersetze von hinten nach vorne (damit Nummern nicht kollidieren)
                for local_num in sorted(local_nums, reverse=True):
                    global_num = local_to_global[local_num]
                    result = re.sub(rf'\[{local_num}\]', f'[{global_num}]', result)

                    # URL zur Registry hinzufügen (wenn vorhanden)
                    if local_num - 1 < len(local_urls):
                        source_registry[global_num] = local_urls[local_num - 1]

                return result, current_num

            # Total Points = bereits fertig + noch offen
            total_points = len(completed_dossiers) + len(research_plan)

            # Session-ID generieren (bei Resume aus dem Original-Plan)
            if is_resume:
                session_id = request.context_state.get("_resumed_from", get_session_id(research_plan, user_query))
            else:
                session_id = get_session_id(research_plan, user_query)
            logger.info(f"[SESSION] ID: {session_id}")

            if is_resume:
                logger.info(f"[RESUME] Continuing session with {len(completed_dossiers)} existing dossiers, {len(research_plan)} remaining")
                yield json.dumps({
                    "type": "status",
                    "message": t("session_resumed", lang, done=len(completed_dossiers), total=total_points, remaining=len(research_plan))
                }) + "\n"
            else:
                yield json.dumps({"type": "status", "message": t("deep_research_start", lang, count=total_points)}) + "\n"
                # Initial Checkpoint: Plan gespeichert
                save_checkpoint(session_id, {
                    "user_query": user_query,
                    "research_plan": research_plan,
                    "completed_dossiers": [],
                    "status": "started"
                })

            yield json.dumps({"type": "session_id", "session_id": session_id}) + "\n"

            # === HAUPTSCHLEIFE: Jeden Punkt abarbeiten ===
            # Kopie der Plan-Liste zum Abarbeiten (Original bleibt für Final Synthesis)
            remaining_points = list(research_plan)
            # Bei Resume: point_index bei len(completed_dossiers) starten
            point_index = len(completed_dossiers) if is_resume else 0

            while remaining_points:
                point_index += 1

                # --- PICK: Ersten Punkt aus verbleibender Liste nehmen ---
                current_point = remaining_points.pop(0)  # Nimmt ersten, entfernt ihn
                point_title = current_point[:60] + "..." if len(current_point) > 60 else current_point

                # Status: Was wurde gepickt, was bleibt übrig
                remaining_titles = [p[:30] + "..." if len(p) > 30 else p for p in remaining_points]
                yield json.dumps({
                    "type": "status",
                    "message": t("pick_point", lang, idx=point_index, total=total_points, title=point_title)
                }) + "\n"

                if remaining_points:
                    yield json.dumps({
                        "type": "status",
                        "message": t("remaining", lang, count=len(remaining_points))
                    }) + "\n"

                # --- STEP A: Think (Suchstrategie) ---
                yield json.dumps({"type": "status", "message": t("developing_strategy", lang, idx=point_index)}) + "\n"
                step_start = time.time()

                system_prompt, user_prompt = build_think_prompt(
                    user_query=user_query,
                    current_point=current_point,
                    previous_learnings=accumulated_learnings if accumulated_learnings else None
                )

                think_response = call_llm(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=MODEL_FAST,
                    timeout=60
                )
                # Flush logs after LLM call
                for log_event in flush_log_buffer():
                    yield log_event
                logger.info(f"[{point_index}] TIMING: Think LLM took {time.time() - step_start:.1f}s")
                logger.info(f"[{point_index}] [THINK] RAW LLM RESPONSE:\n{think_response[:2000] if think_response else 'NONE'}")

                if not think_response:
                    yield json.dumps({"type": "status", "message": t("think_failed", lang, idx=point_index)}) + "\n"
                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": point_index,
                        "total_points": total_points,
                        "skipped": True,
                        "skip_reason": "Think LLM failed" if lang == "en" else "Think LLM fehlgeschlagen",
                        "key_learnings": "Skipped - no search strategy generated" if lang == "en" else "Übersprungen - keine Suchstrategie generiert"
                    }) + "\n"
                    continue

                thinking_block, search_queries = parse_think_response(think_response)
                logger.info(f"[{point_index}] [THINK] PARSED QUERIES: {search_queries}")

                if not search_queries:
                    yield json.dumps({"type": "status", "message": t("no_queries", lang, idx=point_index)}) + "\n"
                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": point_index,
                        "total_points": total_points,
                        "skipped": True,
                        "skip_reason": "No search queries generated" if lang == "en" else "Keine Suchqueries generiert",
                        "key_learnings": "Skipped - LLM could not derive search terms" if lang == "en" else "Übersprungen - LLM konnte keine Suchbegriffe ableiten"
                    }) + "\n"
                    continue

                yield json.dumps({"type": "status", "message": t("searches_planned", lang, idx=point_index, count=len(search_queries))}) + "\n"

                # --- STEP B: Google Search (parallel) ---
                yield json.dumps({"type": "status", "message": t("searching", lang, idx=point_index)}) + "\n"
                step_start = time.time()

                # Dict {query: [results]}
                search_results_dict = await _execute_all_searches_async(search_queries, results_per_query=20)

                # RAM-Cleanup: Browser killen nach Search-Runde
                await _close_google_session()
                logger.info(f"[{point_index}] TIMING: Search took {time.time() - step_start:.1f}s")

                if not search_results_dict or all(len(r) == 0 for r in search_results_dict.values()):
                    yield json.dumps({"type": "status", "message": t("no_results", lang, idx=point_index)}) + "\n"
                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": point_index,
                        "total_points": total_points,
                        "skipped": True,
                        "skip_reason": "No search results found" if lang == "en" else "Keine Suchergebnisse gefunden",
                        "key_learnings": "Skipped - search returned no results" if lang == "en" else "Übersprungen - Suche lieferte keine Treffer"
                    }) + "\n"
                    continue

                # Alle Results flatten und formatieren für Pick URLs Prompt
                formatted_results = []
                result_counter = 1
                for query, results in search_results_dict.items():
                    for result in results:
                        formatted_results.append(f"[{result_counter}] {result.get('title', 'Kein Titel')}")
                        formatted_results.append(f"    URL: {result.get('url', '')}")
                        formatted_results.append(f"    Snippet: {result.get('snippet', '')[:200]}")
                        formatted_results.append("")
                        result_counter += 1
                search_results_text = "\n".join(formatted_results)

                # --- STEP C: Pick URLs ---
                logger.info(f"[{point_index}] === STEP C: Pick URLs START ===")
                yield json.dumps({"type": "status", "message": t("selecting_sources", lang, idx=point_index)}) + "\n"
                step_start = time.time()

                logger.info(f"[{point_index}] Building pick_urls prompt...")
                system_prompt, user_prompt = build_pick_urls_prompt(
                    user_query=user_query,
                    current_point=current_point,
                    thinking_block=thinking_block,
                    search_results=search_results_text,
                    previous_learnings=accumulated_learnings if accumulated_learnings else None
                )

                logger.info(f"[{point_index}] Calling LLM for pick_urls...")
                pick_response = call_llm(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=MODEL_FAST,
                    timeout=60
                )
                # Flush logs after LLM call
                for log_event in flush_log_buffer():
                    yield log_event
                logger.info(f"[{point_index}] LLM returned, parsing response...")
                logger.info(f"[{point_index}] RAW LLM RESPONSE:\n{pick_response[:2000] if pick_response else 'NONE'}")

                selected_urls = parse_pick_urls_response(pick_response) if pick_response else []
                logger.info(f"[{point_index}] PARSED URLs: {selected_urls}")
                logger.info(f"[{point_index}] === STEP C DONE: Pick URLs took {time.time() - step_start:.1f}s, got {len(selected_urls)} URLs ===")

                # === RETRY-LOOP bei Sackgassen (<2 URLs) ===
                if len(selected_urls) < 2:
                    yield json.dumps({"type": "status", "message": t("few_results_retry", lang, idx=point_index)}) + "\n"

                    # Reformulierungs-Prompt
                    retry_system = "Du bist ein Research-Experte. Die erste Suche hat keine guten Ergebnisse geliefert."
                    retry_user = f"""Die Suchanfragen für "{current_point}" haben nur {len(selected_urls)} brauchbare URLs ergeben.

Originale Suchanfragen:
{chr(10).join(search_queries)}

Generiere 5 ALTERNATIVE Suchanfragen mit:
- Anderen Keywords
- Anderen Perspektiven (z.B. "tutorial" statt "documentation")
- Spezifischeren oder allgemeineren Begriffen

FORMAT:
search 1: [Query]
search 2: [Query]
search 3: [Query]
search 4: [Query]
search 5: [Query]"""

                    retry_response = call_llm(retry_system, retry_user, timeout=30)
                    if retry_response:
                        _, retry_queries = parse_think_response("=== SEARCHES ===\n" + retry_response)

                        if retry_queries:
                            yield json.dumps({"type": "status", "message": t("retry_with_new", lang, idx=point_index, count=len(retry_queries))}) + "\n"

                            # Nochmal suchen
                            retry_results = await _execute_all_searches_async(retry_queries, results_per_query=20)

                            # RAM-Cleanup: Browser killen nach Retry-Search
                            await _close_google_session()
                            logger.info(f"[{point_index}] Browser closed (RAM cleanup after retry)")

                            if retry_results:
                                # Neue Results zu den alten hinzufügen
                                for query, results in retry_results.items():
                                    for result in results:
                                        formatted_results.append(f"[{result_counter}] {result.get('title', 'Kein Titel')}")
                                        formatted_results.append(f"    URL: {result.get('url', '')}")
                                        formatted_results.append(f"    Snippet: {result.get('snippet', '')[:200]}")
                                        formatted_results.append("")
                                        result_counter += 1

                                search_results_text = "\n".join(formatted_results)

                                # Pick URLs nochmal
                                system_prompt, user_prompt = build_pick_urls_prompt(
                                    user_query=user_query,
                                    current_point=current_point,
                                    thinking_block=thinking_block,
                                    search_results=search_results_text,
                                    previous_learnings=accumulated_learnings if accumulated_learnings else None
                                )
                                pick_response = call_llm(system_prompt, user_prompt, timeout=60)
                                selected_urls = parse_pick_urls_response(pick_response) if pick_response else selected_urls

                if not selected_urls:
                    yield json.dumps({"type": "status", "message": t("no_urls_skip", lang, idx=point_index)}) + "\n"
                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": point_index,
                        "total_points": total_points,
                        "skipped": True,
                        "skip_reason": "No URLs after retry" if lang == "en" else "Keine URLs nach Retry",
                        "key_learnings": "Skipped - LLM could not identify relevant URLs" if lang == "en" else "Übersprungen - LLM konnte keine relevanten URLs identifizieren"
                    }) + "\n"
                    continue

                yield json.dumps({"type": "status", "message": t("urls_selected", lang, idx=point_index, count=len(selected_urls))}) + "\n"

                # Sources Event für Frontend
                yield json.dumps({
                    "type": "sources",
                    "urls": selected_urls,
                    "message": f"Point {point_index}: {len(selected_urls)} sources" if lang == "en" else f"Punkt {point_index}: {len(selected_urls)} Quellen"
                }) + "\n"

                all_sources.extend(selected_urls)

                # --- STEP D: Scrape URLs (parallel) ---
                logger.info(f"[{point_index}] === STEP D: Scrape URLs START === URLs: {selected_urls}")
                yield json.dumps({"type": "status", "message": t("reading", lang, idx=point_index)}) + "\n"
                step_start = time.time()

                scraped_contents = await scrape_urls_parallel(selected_urls, timeout=45)
                logger.info(f"[{point_index}] === STEP D DONE: Scrape took {time.time() - step_start:.1f}s for {len(selected_urls)} URLs, got {len(scraped_contents)} contents ===")
                logger.info(f"[{point_index}] [SCRAPE] RESULTS: {[(url[:40], len(content) if content else 0) for url, content in scraped_contents.items()]}")

                # Gescrapte Inhalte formatieren
                scraped_text_parts = []
                for url, content in scraped_contents.items():
                    if content and len(content.strip()) > 100:
                        # Auf 10.000 Zeichen pro Quelle begrenzen
                        truncated = content[:10000] + "..." if len(content) > 10000 else content
                        scraped_text_parts.append(f"=== QUELLE: {url} ===\n{truncated}\n")

                scraped_content = "\n".join(scraped_text_parts)

                if not scraped_content:
                    yield json.dumps({"type": "status", "message": t("no_content", lang, idx=point_index)}) + "\n"
                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": point_index,
                        "total_points": total_points,
                        "skipped": True,
                        "skip_reason": "Scraping failed" if lang == "en" else "Scraping fehlgeschlagen",
                        "key_learnings": "Skipped - all URLs were empty or blocked" if lang == "en" else "Übersprungen - alle URLs waren leer oder blockiert"
                    }) + "\n"
                    continue

                yield json.dumps({"type": "status", "message": t("sources_read", lang, idx=point_index, count=len(scraped_text_parts))}) + "\n"

                # --- STEP E: Dossier erstellen ---
                logger.info(f"[{point_index}] === STEP E: Dossier START ===")
                yield json.dumps({"type": "status", "message": t("creating_dossier", lang, idx=point_index)}) + "\n"
                step_start = time.time()

                logger.info(f"[{point_index}] Building dossier prompt with {len(scraped_text_parts)} sources...")
                system_prompt, user_prompt = build_dossier_prompt(
                    user_query=user_query,
                    current_point=current_point,
                    thinking_block=thinking_block,
                    scraped_content=scraped_content
                )

                logger.info(f"[{point_index}] Calling LLM for dossier...")
                dossier_response = call_llm(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=MODEL_FAST,
                    timeout=120
                )
                # Flush logs after LLM call
                for log_event in flush_log_buffer():
                    yield log_event
                logger.info(f"[{point_index}] === STEP E DONE: Dossier LLM took {time.time() - step_start:.1f}s ===")
                logger.info(f"[{point_index}] [DOSSIER] RAW LLM RESPONSE ({len(dossier_response) if dossier_response else 0} chars):\n{dossier_response[:2000] if dossier_response else 'NONE'}...")

                if not dossier_response:
                    yield json.dumps({"type": "status", "message": t("dossier_failed", lang, idx=point_index)}) + "\n"
                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": point_index,
                        "total_points": total_points,
                        "skipped": True,
                        "skip_reason": "Dossier LLM failed" if lang == "en" else "Dossier LLM fehlgeschlagen",
                        "key_learnings": "Skipped - LLM could not create dossier" if lang == "en" else "Übersprungen - LLM konnte kein Dossier erstellen"
                    }) + "\n"
                    continue

                # Dossier + Key Learnings + Citations extrahieren
                dossier_text, key_learnings, citations = parse_dossier_response(dossier_response)
                logger.info(f"[{point_index}] [DOSSIER] PARSED: dossier={len(dossier_text)} chars, learnings={len(key_learnings)} chars, citations={len(citations)}")
                logger.info(f"[{point_index}] [DOSSIER] KEY LEARNINGS:\n{key_learnings[:500] if key_learnings else 'NONE'}...")

                # === GLOBALE CITATION-RENUMMERIERUNG ===
                # Lokale [1], [2], [3] → Globale [source_counter], [source_counter+1], ...
                dossier_urls = list(scraped_contents.keys())
                dossier_text, source_counter = renumber_citations(dossier_text, dossier_urls, source_counter)
                if key_learnings:
                    key_learnings, _ = renumber_citations(key_learnings, dossier_urls, source_counter - len(dossier_urls))
                logger.info(f"[{point_index}] [RENUMBER] Citations renumbered, next global num: {source_counter}")

                # Speichern
                completed_dossiers.append({
                    "point": current_point,
                    "dossier": dossier_text,
                    "sources": dossier_urls
                })

                # Key Learnings akkumulieren für nächste Punkte
                if key_learnings:
                    accumulated_learnings.append(key_learnings)

                # CHECKPOINT nach jedem Dossier
                save_checkpoint(session_id, {
                    "user_query": user_query,
                    "research_plan": research_plan,
                    "completed_dossiers": completed_dossiers,
                    "accumulated_learnings": accumulated_learnings,
                    "remaining_points": remaining_points,
                    "status": f"dossier_{point_index}_complete"
                })

                yield json.dumps({"type": "status", "message": t("dossier_done", lang, idx=point_index)}) + "\n"

                # Point Complete Event für Frontend (mit Key Learnings + vollem Dossier für Ausklappen)
                yield json.dumps({
                    "type": "point_complete",
                    "point_title": current_point,
                    "point_number": point_index,
                    "total_points": total_points,
                    "remaining_count": len(remaining_points),
                    "key_learnings": key_learnings or ("No key learnings extracted" if lang == "en" else "Keine Key Learnings extrahiert"),
                    "dossier_full": dossier_text,  # Volles Dossier für "Mehr anzeigen" Button
                    "sources": list(scraped_contents.keys())
                }) + "\n"

                # Kurze Pause nach point_complete damit Frontend Zeit hat zu rendern
                # WICHTIG: Verhindert dass letztes Dossier mit Final Synthesis verschluckt wird
                await asyncio.sleep(0.3)

            # === FINAL SYNTHESIS ===
            if completed_dossiers:
                yield json.dumps({"type": "status", "message": t("starting_synthesis", lang)}) + "\n"
                yield json.dumps({"type": "status", "message": t("combining_dossiers", lang, count=len(completed_dossiers))}) + "\n"

                system_prompt, user_prompt = build_final_synthesis_prompt(
                    user_query=user_query,
                    research_plan=research_plan,
                    all_dossiers=completed_dossiers
                )

                # Spezielles Event für lange Wartezeit - Frontend zeigt besondere Animation
                total_content_chars = sum(len(d.get("dossier", "")) for d in completed_dossiers)
                estimated_minutes = max(2, min(10, total_content_chars // 10000 + 2))  # 2-10 Minuten geschätzt

                yield json.dumps({
                    "type": "synthesis_start",
                    "message": "Final Synthesis running - this may take a few minutes..." if lang == "en" else "Final Synthesis läuft - das dauert einige Minuten...",
                    "estimated_minutes": estimated_minutes,
                    "dossier_count": len(completed_dossiers),
                    "total_sources": len(source_registry)
                }) + "\n"

                # WICHTIG: Stream MUSS geflusht werden BEVOR der blocking LLM-Call startet
                # asyncio.sleep allein reicht NICHT weil call_llm synchron ist und den Event Loop blockiert
                # Lösung: call_llm in separatem Thread ausführen
                await asyncio.sleep(0.1)

                step_start = time.time()

                # LLM-Call in Thread ausführen damit Event Loop nicht blockiert wird
                # So kommt synthesis_start WIRKLICH vor dem Result an
                final_document = await asyncio.to_thread(
                    call_llm,
                    system_prompt,
                    user_prompt,
                    MODEL_FINAL,  # Aus Request: request.final_model
                    FINAL_SYNTHESIS_TIMEOUT,
                    32000  # Final Synthesis braucht VIEL mehr als 8000!
                )
                # Flush logs after Final Synthesis
                for log_event in flush_log_buffer():
                    yield log_event
                logger.info(f"TIMING: Final Synthesis took {time.time() - step_start:.1f}s")
                logger.info(f"[FINAL] RAW LLM RESPONSE ({len(final_document) if final_document else 0} chars)")

                # SAFETY: Final Document als Backup speichern
                if final_document:
                    from pathlib import Path
                    from datetime import datetime
                    backup_dir = Path(__file__).parent.parent.parent / "final_synthesis_backups"
                    backup_dir.mkdir(exist_ok=True)
                    backup_file = backup_dir / f"synthesis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                    backup_file.write_text(final_document, encoding="utf-8")
                    logger.info(f"[FINAL] Backup saved to {backup_file}")

                if not final_document:
                    # Fallback: Einfach alle Dossiers zusammenfügen
                    yield json.dumps({"type": "status", "message": t("synthesis_failed_fallback", lang)}) + "\n"
                    final_document = "# Research Result\n\n" if lang == "en" else "# Recherche-Ergebnis\n\n"
                    for d in completed_dossiers:
                        final_document += f"## {d['point']}\n\n{d['dossier']}\n\n---\n\n"

            else:
                final_document = "No dossiers created - research failed." if lang == "en" else "Keine Dossiers erstellt - Recherche fehlgeschlagen."

            # === DONE ===
            duration = time.time() - start_time

            yield json.dumps({"type": "status", "message": t("research_complete", lang, duration=f"{duration:.1f}")}) + "\n"

            # Flush any remaining logs before done
            for log_event in flush_log_buffer():
                yield log_event

            # Source Registry für Frontend: {1: "url1", 2: "url2", ...}
            logger.info(f"[DONE] Source Registry has {len(source_registry)} entries")

            yield json.dumps({
                "type": "done",
                "data": {
                    "final_document": final_document,
                    "total_points": len(completed_dossiers),
                    "total_sources": len(source_registry),
                    "duration_seconds": duration,
                    "source_registry": source_registry,  # NEU: Alle Quellen mit globaler Nummerierung
                    "error": None
                }
            }) + "\n"

        except Exception as e:
            logger.error(f"Deep Research failed: {e}", exc_info=True)
            # Flush logs to capture error details
            for log_event in flush_log_buffer():
                yield log_event
            # Security: Don't expose internal error details to client
            yield json.dumps({"type": "error", "message": "Deep research failed. Please try again."}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )


# === SESSION RECOVERY ENDPOINTS ===

class SessionInfo(BaseModel):
    """Info über eine Research-Session."""
    session_id: str
    user_query: str
    status: str
    completed_dossiers: int
    total_points: int
    last_modified: str


class SessionListResponse(BaseModel):
    """Liste aller Sessions."""
    sessions: list[SessionInfo]


class SessionCheckpointResponse(BaseModel):
    """Checkpoint einer Session."""
    success: bool
    session_id: Optional[str] = None
    user_query: Optional[str] = None
    research_plan: Optional[list[str]] = None
    completed_dossiers: Optional[list[dict]] = None
    remaining_points: Optional[list[str]] = None
    status: Optional[str] = None
    error: Optional[str] = None


@router.get("/research/sessions", response_model=SessionListResponse)
async def list_sessions():
    """Listet alle Research-Sessions mit Checkpoints."""
    try:
        checkpoint_base = Path(__file__).parent.parent.parent / "research_checkpoints"

        if not checkpoint_base.exists():
            return SessionListResponse(sessions=[])

        sessions = []
        for session_dir in checkpoint_base.iterdir():
            if session_dir.is_dir():
                checkpoint_file = session_dir / "checkpoint.json"
                if checkpoint_file.exists():
                    try:
                        data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
                        sessions.append(SessionInfo(
                            session_id=session_dir.name,
                            user_query=data.get("user_query", "")[:100] + "..." if len(data.get("user_query", "")) > 100 else data.get("user_query", ""),
                            status=data.get("status", "unknown"),
                            completed_dossiers=len(data.get("completed_dossiers", [])),
                            total_points=len(data.get("research_plan", [])),
                            last_modified=datetime.fromtimestamp(checkpoint_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to parse checkpoint {session_dir.name}: {e}")

        # Nach Änderungsdatum sortieren (neueste zuerst)
        sessions.sort(key=lambda s: s.last_modified, reverse=True)

        return SessionListResponse(sessions=sessions)

    except Exception as e:
        logger.error(f"[SESSIONS] Failed to list sessions: {e}")
        return SessionListResponse(sessions=[])


@router.get("/research/session/{session_id}", response_model=SessionCheckpointResponse)
async def get_session_checkpoint(session_id: str):
    """Lädt den Checkpoint einer spezifischen Session."""
    try:
        checkpoint_file = Path(__file__).parent.parent.parent / "research_checkpoints" / session_id / "checkpoint.json"

        if not checkpoint_file.exists():
            return SessionCheckpointResponse(
                success=False,
                error=f"Session {session_id} nicht gefunden"
            )

        data = json.loads(checkpoint_file.read_text(encoding="utf-8"))

        logger.info(f"[RECOVERY] Loaded session {session_id}: {len(data.get('completed_dossiers', []))} dossiers")

        return SessionCheckpointResponse(
            success=True,
            session_id=session_id,
            user_query=data.get("user_query"),
            research_plan=data.get("research_plan"),
            completed_dossiers=data.get("completed_dossiers"),
            remaining_points=data.get("remaining_points"),
            status=data.get("status")
        )

    except Exception as e:
        logger.error(f"[RECOVERY] Failed to load session {session_id}: {e}")
        return SessionCheckpointResponse(
            success=False,
            error="Session konnte nicht geladen werden"
        )


# Legacy endpoint für alte Frontend-Versionen
@router.get("/research/latest-synthesis")
async def get_latest_synthesis():
    """Legacy: Holt die neueste Session."""
    sessions_response = await list_sessions()
    if sessions_response.sessions:
        latest = sessions_response.sessions[0]
        return await get_session_checkpoint(latest.session_id)
    return SessionCheckpointResponse(success=False, error="Keine Sessions gefunden")


# === RESUME SESSION ENDPOINT ===

class ResumeRequest(BaseModel):
    """Request für Session Resume."""
    session_id: str = Field(..., description="Session ID zum Fortsetzen", max_length=50)
    api_key: str = Field(..., description="API Key", max_length=200)
    provider: str = Field("openrouter", description="API Provider", max_length=50)
    work_model: str = Field("google/gemini-2.5-flash-lite-preview-09-2025", max_length=100)
    final_model: str = Field("qwen/qwen3-vl-235b-a22b-instruct", max_length=100)
    language: str = Field("de", description="Language for status messages (de/en)")
    base_url: str = Field("https://openrouter.ai/api/v1/chat/completions", description="API Base URL")


@router.post("/research/resume")
async def resume_session(request: ResumeRequest):
    """
    Setzt eine unterbrochene Session fort.

    Lädt den Checkpoint und führt die Pipeline ab remaining_points fort.
    """
    # Checkpoint laden
    checkpoint_file = Path(__file__).parent.parent.parent / "research_checkpoints" / request.session_id / "checkpoint.json"

    if not checkpoint_file.exists():
        return {"error": f"Session {request.session_id} nicht gefunden"}

    checkpoint = json.loads(checkpoint_file.read_text(encoding="utf-8"))

    remaining_points = checkpoint.get("remaining_points", [])
    if not remaining_points:
        return {"error": "Keine ausstehenden Punkte - Session ist bereits fertig"}

    # Context State für Deep Research bauen
    context_state = {
        "user_query": checkpoint.get("user_query", ""),
        "clarification_questions": [],
        "clarification_answers": [],
        "overview_queries": [],
        "overview_results": {},
        "research_plan": remaining_points,  # NUR die verbleibenden Punkte!
        "_resumed_from": request.session_id,
        "_completed_dossiers": checkpoint.get("completed_dossiers", []),
        "_accumulated_learnings": checkpoint.get("accumulated_learnings", [])
    }

    # Deep Research Request bauen
    deep_request = DeepResearchRequest(
        context_state=context_state,
        session_id=request.session_id,
        api_key=request.api_key,
        provider=request.provider,
        work_model=request.work_model,
        final_model=request.final_model,
        base_url=request.base_url
    )

    # Deep Research starten (gibt StreamingResponse zurück)
    return await run_deep_research(deep_request)


# === ACADEMIC MODE ENDPOINT ===

class AcademicResearchRequest(BaseModel):
    """Request für Academic Deep Research Pipeline."""
    context_state: dict = Field(..., description="Context State mit academic_bereiche")
    session_id: Optional[str] = Field(None, description="Session ID für SSE Events", max_length=100)
    api_key: str = Field(..., description="API Key", max_length=200)
    provider: str = Field("openrouter", description="API Provider", max_length=50)
    work_model: str = Field("google/gemini-2.5-flash-lite-preview-09-2025", description="Modell für Vorarbeit", max_length=100)
    final_model: str = Field("anthropic/claude-sonnet-4.5", description="Modell für Meta-Synthesis", max_length=100)
    language: str = Field("de", description="Language for status messages (de/en)")
    base_url: str = Field("https://openrouter.ai/api/v1/chat/completions", description="API Base URL")


@router.post("/research/academic")
async def research_academic(request: AcademicResearchRequest):
    """
    Academic Deep Research Pipeline - STREAMING.

    UNTERSCHIED ZU NORMAL MODE:
    - Plan hat BEREICHE statt flacher Liste
    - Bereiche werden SEQUENZIELL abgearbeitet (Key Learnings fließen nur INNERHALB)
    - Nach allen Bereichen: META-SYNTHESE (Querverbindungen, Toulmin, Evidenz-Grading)

    Events:
    - {"type": "bereich_start", "bereich_title": "...", "bereich_number": N, "total_bereiche": M}
    - {"type": "point_complete", ...} (wie Normal Mode)
    - {"type": "bereich_complete", "bereich_title": "...", "synthese": "..."}
    - {"type": "meta_synthesis_start", ...}
    - {"type": "done", "data": {...}}
    """
    import json
    import time
    import re
    import requests as http_requests
    from lutum.researcher.search import _execute_all_searches_async, _close_google_session
    from lutum.scrapers.camoufox_scraper import scrape_urls_batch
    from lutum.researcher.prompts import (
        build_think_prompt,
        parse_think_response,
        build_pick_urls_prompt,
        parse_pick_urls_response,
        build_dossier_prompt,
        parse_dossier_response,
    )
    from lutum.researcher.prompts.bereichs_synthesis import (
        build_bereichs_synthesis_prompt,
        BEREICHS_SYNTHESIS_MODEL,
        BEREICHS_SYNTHESIS_TIMEOUT,
    )
    from lutum.researcher.prompts.academic_conclusion import (
        build_academic_conclusion_prompt,
        ACADEMIC_CONCLUSION_MODEL,
        ACADEMIC_CONCLUSION_TIMEOUT,
    )

    logger.info("Academic Research Pipeline started")
    start_time = time.time()

    # API Config setzen
    set_api_config(
        key=request.api_key,
        provider=request.provider,
        work_model=request.work_model,
        final_model=request.final_model,
        base_url=request.base_url
    )

    MODEL_FAST = request.work_model
    MODEL_META = request.final_model
    BASE_URL = request.base_url

    def call_llm(system_prompt: str, user_prompt: str, model: str = MODEL_FAST, timeout: int = 60, max_tokens: int = 8000) -> Optional[str]:
        """Ruft LLM auf (OpenRouter, OpenAI, Anthropic, Google, HuggingFace)."""
        try:
            response = http_requests.post(
                BASE_URL,
                headers=get_api_headers(),
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": max_tokens
                },
                timeout=timeout
            )
            result = response.json()
            if "choices" in result:
                choice = result["choices"][0]
                message = choice.get("message", {})
                content = message.get("content")
                finish_reason = choice.get("finish_reason", "unknown")

                # Debug: Log wenn content fehlt oder leer ist
                if content is None:
                    logger.warning(f"LLM returned null content (finish_reason={finish_reason}, refusal={message.get('refusal', 'none')}, model={model})")
                elif not content.strip():
                    logger.warning(f"LLM returned empty string (finish_reason={finish_reason}, model={model})")
                return content
            logger.error(f"LLM error (no choices): {result}")
            return None
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    async def scrape_urls_parallel(urls: list[str], timeout: int = 45) -> dict[str, str]:
        """Scraped URLs."""
        return await scrape_urls_batch(urls, timeout=timeout)

    async def generate():
        lang = request.language
        try:
            # Context laden
            context_state = request.context_state
            user_query = context_state.get("user_query", "")
            academic_bereiche = context_state.get("academic_bereiche", {})

            if not academic_bereiche:
                yield json.dumps({"type": "error", "message": "No academic areas in context" if lang == "en" else "Keine Academic Bereiche im Context"}) + "\n"
                return

            total_bereiche = len(academic_bereiche)
            total_points = sum(len(points) for points in academic_bereiche.values())

            yield json.dumps({
                "type": "status",
                "message": t("academic_start", lang, bereiche=total_bereiche, points=total_points)
            }) + "\n"

            # === GLOBALE TRACKING ===
            source_registry: dict[int, str] = {}
            source_counter = 1
            all_bereichs_synthesen = []
            global_point_index = 0

            def renumber_citations(text: str, local_urls: list[str], start_num: int) -> tuple[str, int]:
                """Ersetzt lokale [N] durch globale Nummern."""
                result = text
                current_num = start_num
                local_nums = set(int(m) for m in re.findall(r'\[(\d+)\]', text))
                local_to_global = {}
                for local_num in sorted(local_nums):
                    local_to_global[local_num] = current_num
                    current_num += 1
                for local_num in sorted(local_nums, reverse=True):
                    global_num = local_to_global[local_num]
                    result = re.sub(rf'\[{local_num}\]', f'[{global_num}]', result)
                    if local_num - 1 < len(local_urls):
                        source_registry[global_num] = local_urls[local_num - 1]
                return result, current_num

            # === HAUPTSCHLEIFE: Jeden BEREICH abarbeiten ===
            for bereich_index, (bereich_titel, bereich_punkte) in enumerate(academic_bereiche.items(), 1):

                yield json.dumps({
                    "type": "bereich_start",
                    "bereich_title": bereich_titel,
                    "bereich_number": bereich_index,
                    "total_bereiche": total_bereiche,
                    "points_in_bereich": len(bereich_punkte)
                }) + "\n"

                # Key Learnings NUR für diesen Bereich (nicht bereichsübergreifend!)
                bereich_learnings = []
                bereich_dossiers = []
                bereich_sources = []

                # === Jeden Punkt im Bereich abarbeiten ===
                for punkt_index, current_point in enumerate(bereich_punkte, 1):
                    global_point_index += 1
                    punkt_label = f"[{bereich_index}.{punkt_index}]"

                    yield json.dumps({
                        "type": "status",
                        "message": f"{punkt_label} {current_point[:50]}..."
                    }) + "\n"

                    # --- STEP A: Think ---
                    yield json.dumps({"type": "status", "message": f"{punkt_label} {'Developing search strategy...' if lang == 'en' else 'Entwickle Suchstrategie...'}"}) + "\n"

                    system_prompt, user_prompt = build_think_prompt(
                        user_query=user_query,
                        current_point=current_point,
                        previous_learnings=bereich_learnings if bereich_learnings else None
                    )

                    think_response = call_llm(system_prompt, user_prompt, timeout=60)
                    # Flush logs after LLM call
                    for log_event in flush_log_buffer():
                        yield log_event

                    if not think_response:
                        yield json.dumps({
                            "type": "point_complete",
                            "point_title": current_point,
                            "point_number": global_point_index,
                            "total_points": total_points,
                            "skipped": True,
                            "skip_reason": "Think failed" if lang == "en" else "Think fehlgeschlagen",
                            "key_learnings": "Skipped" if lang == "en" else "Übersprungen"
                        }) + "\n"
                        continue

                    thinking_block, search_queries = parse_think_response(think_response)

                    if not search_queries:
                        yield json.dumps({
                            "type": "point_complete",
                            "point_title": current_point,
                            "point_number": global_point_index,
                            "total_points": total_points,
                            "skipped": True,
                            "skip_reason": "No search queries" if lang == "en" else "Keine Suchqueries",
                            "key_learnings": "Skipped" if lang == "en" else "Übersprungen"
                        }) + "\n"
                        continue

                    # --- STEP B: Search ---
                    yield json.dumps({"type": "status", "message": f"{punkt_label} {'Searching Google...' if lang == 'en' else 'Durchsuche Google...'}"}) + "\n"

                    search_results_dict = await _execute_all_searches_async(search_queries, results_per_query=20)
                    await _close_google_session()

                    if not search_results_dict:
                        continue

                    # Formatieren
                    formatted_results = []
                    result_counter = 1
                    for query, results in search_results_dict.items():
                        for result in results:
                            formatted_results.append(f"[{result_counter}] {result.get('title', '')}")
                            formatted_results.append(f"    URL: {result.get('url', '')}")
                            formatted_results.append(f"    Snippet: {result.get('snippet', '')[:200]}")
                            formatted_results.append("")
                            result_counter += 1
                    search_results_text = "\n".join(formatted_results)

                    # --- STEP C: Pick URLs ---
                    yield json.dumps({"type": "status", "message": f"{punkt_label} {'Selecting sources...' if lang == 'en' else 'Wähle Quellen...'}"}) + "\n"

                    system_prompt, user_prompt = build_pick_urls_prompt(
                        user_query=user_query,
                        current_point=current_point,
                        thinking_block=thinking_block,
                        search_results=search_results_text,
                        previous_learnings=bereich_learnings if bereich_learnings else None
                    )

                    pick_response = call_llm(system_prompt, user_prompt, timeout=60)
                    # Flush logs after LLM call
                    for log_event in flush_log_buffer():
                        yield log_event
                    selected_urls = parse_pick_urls_response(pick_response) if pick_response else []

                    if not selected_urls:
                        continue

                    yield json.dumps({
                        "type": "sources",
                        "urls": selected_urls,
                        "message": f"{punkt_label} {len(selected_urls)} {'sources' if lang == 'en' else 'Quellen'}"
                    }) + "\n"

                    bereich_sources.extend(selected_urls)

                    # --- STEP D: Scrape ---
                    yield json.dumps({"type": "status", "message": f"{punkt_label} {'Reading sources...' if lang == 'en' else 'Lese Quellen...'}"}) + "\n"

                    scraped_contents = await scrape_urls_parallel(selected_urls)

                    scraped_text_parts = []
                    for url, content in scraped_contents.items():
                        if content and len(content.strip()) > 100:
                            truncated = content[:10000] + "..." if len(content) > 10000 else content
                            scraped_text_parts.append(f"=== QUELLE: {url} ===\n{truncated}\n")

                    scraped_content = "\n".join(scraped_text_parts)

                    if not scraped_content:
                        continue

                    # --- STEP E: Dossier ---
                    yield json.dumps({"type": "status", "message": f"{punkt_label} {'Creating dossier...' if lang == 'en' else 'Erstelle Dossier...'}"}) + "\n"

                    system_prompt, user_prompt = build_dossier_prompt(
                        user_query=user_query,
                        current_point=current_point,
                        thinking_block=thinking_block,
                        scraped_content=scraped_content
                    )

                    dossier_response = call_llm(system_prompt, user_prompt, timeout=120)
                    # Flush logs after LLM call
                    for log_event in flush_log_buffer():
                        yield log_event

                    if not dossier_response:
                        continue

                    dossier_text, key_learnings, citations = parse_dossier_response(dossier_response)

                    # Globale Renummerierung
                    dossier_urls = list(scraped_contents.keys())
                    dossier_text, source_counter = renumber_citations(dossier_text, dossier_urls, source_counter)
                    if key_learnings:
                        key_learnings, _ = renumber_citations(key_learnings, dossier_urls, source_counter - len(dossier_urls))

                    bereich_dossiers.append({
                        "point": current_point,
                        "dossier": dossier_text,
                        "sources": dossier_urls
                    })

                    if key_learnings:
                        bereich_learnings.append(key_learnings)

                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": global_point_index,
                        "total_points": total_points,
                        "key_learnings": key_learnings or ("No key learnings" if lang == "en" else "Keine Key Learnings"),
                        "dossier_full": dossier_text,
                        "sources": dossier_urls
                    }) + "\n"

                    await asyncio.sleep(0.2)

                # === BEREICHS-SYNTHESE (ECHTER LLM CALL!) ===
                if bereich_dossiers:
                    yield json.dumps({
                        "type": "status",
                        "message": f"🧠 {'Synthesis for area:' if lang == 'en' else 'Synthese für Bereich:'} {bereich_titel}..."
                    }) + "\n"

                    # Echter LLM Call für Bereichs-Synthese
                    system_prompt, user_prompt = build_bereichs_synthesis_prompt(
                        user_query=user_query,
                        bereich_titel=bereich_titel,
                        bereich_dossiers=bereich_dossiers
                    )

                    bereich_synthese = await asyncio.to_thread(
                        call_llm,
                        system_prompt,
                        user_prompt,
                        BEREICHS_SYNTHESIS_MODEL,
                        BEREICHS_SYNTHESIS_TIMEOUT,
                        48000  # Increased from 16k for comprehensive area analysis
                    )
                    # Flush logs after Bereichs-Synthese
                    for log_event in flush_log_buffer():
                        yield log_event

                    if not bereich_synthese:
                        # Fallback: Dossiers zusammenkleben
                        bereich_synthese = f"## {bereich_titel}\n\n"
                        for d in bereich_dossiers:
                            bereich_synthese += f"### {d['point']}\n\n{d['dossier']}\n\n"

                    # KEINE Renummerierung hier - die Dossiers haben bereits globale Nummern!
                    # Die Bereichs-Synthese soll die globalen Citations aus den Dossiers beibehalten.

                    all_bereichs_synthesen.append({
                        "bereich_titel": bereich_titel,
                        "synthese": bereich_synthese,
                        "sources": bereich_sources,
                        "sources_count": len(bereich_sources),
                        "dossiers": bereich_dossiers
                    })

                    yield json.dumps({
                        "type": "bereich_complete",
                        "bereich_title": bereich_titel,
                        "bereich_number": bereich_index,
                        "total_bereiche": total_bereiche,
                        "dossiers_count": len(bereich_dossiers),
                        "sources_count": len(bereich_sources),
                        "synthese_preview": bereich_synthese[:500] + "..." if len(bereich_synthese) > 500 else bereich_synthese
                    }) + "\n"

                await asyncio.sleep(0.3)

            # === ACADEMIC CONCLUSION (DER MAGISCHE FINALE CALL!) ===
            if all_bereichs_synthesen:
                yield json.dumps({
                    "type": "meta_synthesis_start",
                    "message": "🔮 Academic Conclusion: Finding cross-connections, patterns, the solution..." if lang == "en" else "🔮 Academic Conclusion: Finde Querverbindungen, Muster, die Lösung...",
                    "bereiche_count": len(all_bereichs_synthesen),
                    "total_sources": len(source_registry)
                }) + "\n"

                await asyncio.sleep(0.2)

                # Count total dossiers across all areas
                total_dossiers = sum(len(s.get('dossiers', [])) for s in all_bereichs_synthesen)

                # DER MAGISCHE CALL - bekommt User-Frage + alle Bereichs-Synthesen
                system_prompt, user_prompt, conclusion_metrics = build_academic_conclusion_prompt(
                    user_query=user_query,
                    bereichs_synthesen=all_bereichs_synthesen,
                    total_dossiers=total_dossiers,
                )

                # Academic Conclusion in Thread für non-blocking
                academic_conclusion = await asyncio.to_thread(
                    call_llm,
                    system_prompt,
                    user_prompt,
                    ACADEMIC_CONCLUSION_MODEL,
                    ACADEMIC_CONCLUSION_TIMEOUT,
                    96000  # Increased from 32k for comprehensive synthesis (200k+ chars output)
                )
                # Flush logs after Academic Conclusion
                for log_event in flush_log_buffer():
                    yield log_event

                if not academic_conclusion:
                    academic_conclusion = "# Conclusion\n\nConclusion synthesis failed." if lang == "en" else "# Conclusion\n\nConclusion-Synthese fehlgeschlagen."

                # === BUILD IMPACT STATEMENT ===
                if lang == "en":
                    impact_statement = f"""> **🔮 I have analyzed {conclusion_metrics['total_sources']} sources** and read **{conclusion_metrics['total_synthese_chars']:,} characters** of synthesized knowledge.
> I have processed **{conclusion_metrics['total_dossiers']} dossiers** from worker AIs across **{conclusion_metrics['total_areas']} independent research areas**.
> This is what I found:

"""
                else:
                    impact_statement = f"""> **🔮 Ich habe {conclusion_metrics['total_sources']} Quellen analysiert** und **{conclusion_metrics['total_synthese_chars']:,} Zeichen** an synthetisiertem Wissen gelesen.
> Ich habe **{conclusion_metrics['total_dossiers']} Dossiers** von Arbeits-KIs aus **{conclusion_metrics['total_areas']} unabhängigen Forschungsbereichen** verarbeitet.
> Das ist was ich gefunden habe:

"""

                # === STRUCTURED DATA (not glued together anymore!) ===
                # Each synthesis = separate collapsible block
                # Conclusion = separate open block with orange background

                syntheses_data = []
                for i, s in enumerate(all_bereichs_synthesen, 1):
                    syntheses_data.append({
                        "index": i,
                        "title": s['bereich_titel'],
                        "content": s['synthese'],
                        "sources_count": s.get('sources_count', 0),
                        "dossiers_count": len(s.get('dossiers', []))
                    })

                conclusion_data = {
                    "impact_statement": impact_statement,
                    "content": academic_conclusion,
                    "title": "🔮 CROSS-CONNECTIONS & CONCLUSION" if lang == "en" else "🔮 QUERVERBINDUNGEN & CONCLUSION"
                }

                # Legacy: Still build final_document for backwards compatibility
                final_document = f"# {user_query[:100]}{'...' if len(user_query) > 100 else ''}\n\n"
                final_document += "---\n\n"
                for i, s in enumerate(all_bereichs_synthesen, 1):
                    final_document += f"\n{'═' * 60}\n"
                    final_document += f"# 📚 BEREICH {i}/{len(all_bereichs_synthesen)}: {s['bereich_titel']}\n"
                    final_document += f"{'═' * 60}\n\n"
                    final_document += s['synthese']
                    final_document += "\n\n"
                final_document += f"\n{'█' * 60}\n"
                final_document += "# 🔮 CROSS-CONNECTIONS & CONCLUSION\n" if lang == "en" else "# 🔮 QUERVERBINDUNGEN & CONCLUSION\n"
                final_document += f"{'█' * 60}\n\n"
                final_document += impact_statement
                final_document += academic_conclusion

                # SAFETY: Academic Final Document als Backup speichern
                if final_document:
                    from pathlib import Path
                    from datetime import datetime
                    backup_dir = Path(__file__).parent.parent.parent / "academic_synthesis_backups"
                    backup_dir.mkdir(exist_ok=True)
                    backup_file = backup_dir / f"academic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                    backup_file.write_text(final_document, encoding="utf-8")
                    logger.info(f"[ACADEMIC] Backup saved to {backup_file}")

            else:
                final_document = "No areas successfully researched." if lang == "en" else "Keine Bereiche erfolgreich recherchiert."

            # === DONE ===
            duration = time.time() - start_time

            yield json.dumps({"type": "status", "message": t("academic_complete", lang, duration=f"{duration:.1f}")}) + "\n"

            # Flush any remaining logs before done
            for log_event in flush_log_buffer():
                yield log_event

            yield json.dumps({
                "type": "done",
                "data": {
                    # NEW: Structured data for collapsible UI
                    "syntheses": syntheses_data if all_bereichs_synthesen else [],
                    "conclusion": conclusion_data if all_bereichs_synthesen else None,
                    # LEGACY: Still include for backwards compatibility
                    "final_document": final_document,
                    # Metadata
                    "total_points": global_point_index,
                    "total_sources": len(source_registry),
                    "total_bereiche": total_bereiche,
                    "duration_seconds": duration,
                    "source_registry": source_registry,
                    "conclusion_metrics": conclusion_metrics if all_bereichs_synthesen else None,
                    "error": None
                }
            }) + "\n"

        except Exception as e:
            logger.error(f"Academic Research failed: {e}", exc_info=True)
            # Flush logs to capture error details
            for log_event in flush_log_buffer():
                yield log_event
            yield json.dumps({"type": "error", "message": "Academic research failed. Please try again."}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )
