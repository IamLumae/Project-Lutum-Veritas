"""
Research Endpoint
=================
Endpoint für die Research Pipeline.

Step 1: User Message → Overview Queries
SSE Events für Fortschrittsanzeige
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lutum.core.log_config import get_logger
from lutum.core.api_config import get_api_key, set_api_key
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
    message: str = Field(..., description="User Nachricht / Research-Auftrag")
    session_id: Optional[str] = Field(None, description="Session ID für SSE Events")
    api_key: str = Field(..., description="OpenRouter API Key")


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

    # API Key setzen für alle LLM Calls
    set_api_key(request.api_key)

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
    message: str = Field(..., description="User Nachricht / Research-Auftrag")
    session_id: Optional[str] = Field(None, description="Session ID für SSE Events")
    max_step: int = Field(3, description="Bis zu welchem Step ausführen (default 3)")
    api_key: str = Field(..., description="OpenRouter API Key")


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
        # API Key setzen für alle LLM Calls
        set_api_key(request.api_key)

        try:
            if not request.message or not request.message.strip():
                yield json.dumps({"type": "error", "message": "Message cannot be empty"}) + "\n"
                return

            user_message = request.message
            context = {"user_message": user_message, "error": None}

            # === STEP 1: Overview ===
            yield json.dumps({"type": "status", "message": "Ich verschaffe mir eine Übersicht..."}) + "\n"

            result1 = get_overview_queries(user_message)
            context.update(result1)

            if context.get("error"):
                yield json.dumps({"type": "error", "message": context["error"]}) + "\n"
                return

            queries = context.get("queries_initial", [])
            yield json.dumps({"type": "status", "message": f"Übersicht erstellt ({len(queries)} Suchanfragen)"}) + "\n"

            # === STEP 2: Search ===
            if request.max_step >= 2:
                yield json.dumps({"type": "status", "message": "Ich durchsuche Google..."}) + "\n"

                result2 = await get_initial_data(user_message, queries)
                context.update(result2)

                # RAM-Cleanup: Browser killen nach Search
                await _close_google_session()
                logger.info("Browser session closed (RAM cleanup)")

                if context.get("error"):
                    yield json.dumps({"type": "error", "message": context["error"]}) + "\n"
                    return

                urls = context.get("urls_picked", [])
                yield json.dumps({"type": "status", "message": f"Quellen gefunden ({len(urls)} URLs)"}) + "\n"

                # Sources Event mit URL-Liste für Frontend
                if urls:
                    yield json.dumps({"type": "sources", "urls": urls, "message": f"{len(urls)} Quellen werden analysiert"}) + "\n"

            # === STEP 3: Clarify ===
            if request.max_step >= 3:
                urls = context.get("urls_picked", [])
                if urls:
                    yield json.dumps({"type": "status", "message": "Ich lese die Quellen..."}) + "\n"

                    result3 = await get_clarification(user_message, urls)
                    context.update(result3)

                    scraped = context.get("success_count", 0)
                    yield json.dumps({"type": "status", "message": f"Quellen analysiert ({scraped} Seiten)"}) + "\n"

            # Response formatieren
            response_text = format_pipeline_response(context)

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
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )


# === STEP 4: RESEARCH PLAN ===

class PlanRequest(BaseModel):
    """Request für Plan-Erstellung (Step 4)."""
    user_query: str = Field(..., description="Ursprüngliche User-Anfrage")
    clarification_questions: list[str] = Field(default_factory=list, description="Rückfragen aus Step 3")
    clarification_answers: list[str] = Field(..., description="User-Antworten auf Rückfragen")
    session_id: Optional[str] = Field(None, description="Session ID für SSE Events")
    api_key: str = Field(..., description="OpenRouter API Key")


class PlanResponse(BaseModel):
    """Response mit Recherche-Plan."""
    plan_points: list[str] = Field(default_factory=list, description="Plan-Punkte")
    plan_text: str = Field("", description="Formatierter Plan-Text")
    context_state: dict = Field(default_factory=dict, description="Aktueller Context State")
    error: Optional[str] = Field(None, description="Fehlermeldung")


@router.post("/research/plan", response_model=PlanResponse)
async def research_plan(request: PlanRequest):
    """
    Step 4: Recherche-Plan erstellen.

    Nimmt Context State mit User-Antworten und generiert
    einen tiefgehenden Recherche-Plan (min. 5 Punkte).

    Args:
        request: PlanRequest mit Query, Rückfragen, Antworten

    Returns:
        PlanResponse mit Plan-Punkten
    """
    logger.info(f"Plan request for: {request.user_query[:100]}...")

    # API Key setzen
    set_api_key(request.api_key)

    try:
        sid = request.session_id

        # Status Event
        if sid:
            emit_event(sid, "step_start", "Erstelle Recherche-Plan...")

        # Context State aufbauen
        context = ContextState()
        context.user_query = request.user_query
        context.clarification_questions = request.clarification_questions
        context.clarification_answers = request.clarification_answers

        if sid:
            emit_event(sid, "step_progress", "Analysiere deine Antworten...")

        # Plan generieren
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
            error=None
        )

    except Exception as e:
        logger.error(f"Plan creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


class PlanReviseRequest(BaseModel):
    """Request für Plan-Überarbeitung."""
    context_state: dict = Field(..., description="Aktueller Context State")
    feedback: str = Field(..., description="User-Feedback zum Plan")
    session_id: Optional[str] = Field(None, description="Session ID für SSE Events")
    api_key: str = Field(..., description="OpenRouter API Key")


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

    # API Key setzen
    set_api_key(request.api_key)

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
    session_id: Optional[str] = Field(None, description="Session ID für SSE Events")
    api_key: str = Field(..., description="OpenRouter API Key")


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

    # OpenRouter Config
    MODEL_FAST = "google/gemini-3-flash-preview"

    def call_llm(system_prompt: str, user_prompt: str, model: str = MODEL_FAST, timeout: int = 60, max_tokens: int = 8000) -> Optional[str]:
        """Ruft OpenRouter LLM auf."""
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {get_api_key()}",
                    "Content-Type": "application/json",
                },
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
                return result["choices"][0]["message"]["content"]
            logger.error(f"LLM error: {result}")
            return None
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    async def scrape_urls_parallel(urls: list[str], timeout: int = 15) -> dict[str, str]:
        """Scraped URLs sequenziell aber schnell (15s timeout statt 45s)."""
        return await scrape_urls_batch(urls, timeout=timeout)

    logger.info("Deep Research Pipeline started")
    start_time = time.time()

    # API Key setzen für alle LLM Calls
    set_api_key(request.api_key)

    async def generate():
        try:
            # Context State laden
            context = ContextState.from_dict(request.context_state)
            research_plan = context.research_plan

            if not research_plan or len(research_plan) == 0:
                yield json.dumps({"type": "error", "message": "Kein Recherche-Plan vorhanden"}) + "\n"
                return

            total_points = len(research_plan)
            user_query = context.user_query

            yield json.dumps({"type": "status", "message": f"Starte Deep Research mit {total_points} Punkten..."}) + "\n"

            # Akkumulatoren
            completed_dossiers = []  # Liste von {point, dossier, sources}
            accumulated_learnings = []  # Key Learnings für Context-Pass
            all_sources = []

            # === HAUPTSCHLEIFE: Jeden Punkt abarbeiten ===
            # Kopie der Plan-Liste zum Abarbeiten (Original bleibt für Final Synthesis)
            remaining_points = list(research_plan)
            point_index = 0

            while remaining_points:
                point_index += 1

                # --- PICK: Ersten Punkt aus verbleibender Liste nehmen ---
                current_point = remaining_points.pop(0)  # Nimmt ersten, entfernt ihn
                point_title = current_point[:60] + "..." if len(current_point) > 60 else current_point

                # Status: Was wurde gepickt, was bleibt übrig
                remaining_titles = [p[:30] + "..." if len(p) > 30 else p for p in remaining_points]
                yield json.dumps({
                    "type": "status",
                    "message": f"PICK: Punkt {point_index}/{total_points} → {point_title}"
                }) + "\n"

                if remaining_points:
                    yield json.dumps({
                        "type": "status",
                        "message": f"Verbleibend: {len(remaining_points)} Punkte"
                    }) + "\n"

                # --- STEP A: Think (Suchstrategie) ---
                yield json.dumps({"type": "status", "message": f"[{point_index}] Entwickle Suchstrategie..."}) + "\n"
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
                logger.info(f"[{point_index}] TIMING: Think LLM took {time.time() - step_start:.1f}s")
                logger.info(f"[{point_index}] [THINK] RAW LLM RESPONSE:\n{think_response[:2000] if think_response else 'NONE'}")

                if not think_response:
                    yield json.dumps({"type": "status", "message": f"[{point_index}] Think fehlgeschlagen, überspringe..."}) + "\n"
                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": point_index,
                        "total_points": total_points,
                        "skipped": True,
                        "skip_reason": "Think LLM fehlgeschlagen",
                        "key_learnings": "Übersprungen - keine Suchstrategie generiert"
                    }) + "\n"
                    continue

                thinking_block, search_queries = parse_think_response(think_response)
                logger.info(f"[{point_index}] [THINK] PARSED QUERIES: {search_queries}")

                if not search_queries:
                    yield json.dumps({"type": "status", "message": f"[{point_index}] Keine Suchqueries generiert"}) + "\n"
                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": point_index,
                        "total_points": total_points,
                        "skipped": True,
                        "skip_reason": "Keine Suchqueries generiert",
                        "key_learnings": "Übersprungen - LLM konnte keine Suchbegriffe ableiten"
                    }) + "\n"
                    continue

                yield json.dumps({"type": "status", "message": f"[{point_index}] {len(search_queries)} Suchen geplant"}) + "\n"

                # --- STEP B: Google Search (parallel) ---
                yield json.dumps({"type": "status", "message": f"[{point_index}] Durchsuche Google..."}) + "\n"
                step_start = time.time()

                # Dict {query: [results]}
                search_results_dict = await _execute_all_searches_async(search_queries, results_per_query=20)

                # RAM-Cleanup: Browser killen nach Search-Runde
                await _close_google_session()
                logger.info(f"[{point_index}] TIMING: Search took {time.time() - step_start:.1f}s")

                if not search_results_dict or all(len(r) == 0 for r in search_results_dict.values()):
                    yield json.dumps({"type": "status", "message": f"[{point_index}] Keine Suchergebnisse"}) + "\n"
                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": point_index,
                        "total_points": total_points,
                        "skipped": True,
                        "skip_reason": "Keine Suchergebnisse gefunden",
                        "key_learnings": "Übersprungen - DuckDuckGo lieferte keine Treffer"
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
                yield json.dumps({"type": "status", "message": f"[{point_index}] Wähle beste Quellen..."}) + "\n"
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
                logger.info(f"[{point_index}] LLM returned, parsing response...")
                logger.info(f"[{point_index}] RAW LLM RESPONSE:\n{pick_response[:2000] if pick_response else 'NONE'}")

                selected_urls = parse_pick_urls_response(pick_response) if pick_response else []
                logger.info(f"[{point_index}] PARSED URLs: {selected_urls}")
                logger.info(f"[{point_index}] === STEP C DONE: Pick URLs took {time.time() - step_start:.1f}s, got {len(selected_urls)} URLs ===")

                # === RETRY-LOOP bei Sackgassen (<2 URLs) ===
                if len(selected_urls) < 2:
                    yield json.dumps({"type": "status", "message": f"[{point_index}] Wenige Ergebnisse - reformuliere Suche..."}) + "\n"

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
                            yield json.dumps({"type": "status", "message": f"[{point_index}] Retry mit {len(retry_queries)} neuen Suchen..."}) + "\n"

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
                    yield json.dumps({"type": "status", "message": f"[{point_index}] Keine URLs gefunden, überspringe Punkt"}) + "\n"
                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": point_index,
                        "total_points": total_points,
                        "skipped": True,
                        "skip_reason": "Keine URLs nach Retry",
                        "key_learnings": "Übersprungen - LLM konnte keine relevanten URLs identifizieren"
                    }) + "\n"
                    continue

                yield json.dumps({"type": "status", "message": f"[{point_index}] {len(selected_urls)} URLs ausgewählt"}) + "\n"

                # Sources Event für Frontend
                yield json.dumps({
                    "type": "sources",
                    "urls": selected_urls,
                    "message": f"Punkt {point_index}: {len(selected_urls)} Quellen"
                }) + "\n"

                all_sources.extend(selected_urls)

                # --- STEP D: Scrape URLs (parallel) ---
                logger.info(f"[{point_index}] === STEP D: Scrape URLs START === URLs: {selected_urls}")
                yield json.dumps({"type": "status", "message": f"[{point_index}] Lese Quellen..."}) + "\n"
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
                    yield json.dumps({"type": "status", "message": f"[{point_index}] Keine Inhalte gescraped"}) + "\n"
                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": point_index,
                        "total_points": total_points,
                        "skipped": True,
                        "skip_reason": "Scraping fehlgeschlagen",
                        "key_learnings": "Übersprungen - alle URLs waren leer oder blockiert"
                    }) + "\n"
                    continue

                yield json.dumps({"type": "status", "message": f"[{point_index}] {len(scraped_text_parts)} Quellen gelesen"}) + "\n"

                # --- STEP E: Dossier erstellen ---
                logger.info(f"[{point_index}] === STEP E: Dossier START ===")
                yield json.dumps({"type": "status", "message": f"[{point_index}] Erstelle Dossier..."}) + "\n"
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
                logger.info(f"[{point_index}] === STEP E DONE: Dossier LLM took {time.time() - step_start:.1f}s ===")
                logger.info(f"[{point_index}] [DOSSIER] RAW LLM RESPONSE ({len(dossier_response) if dossier_response else 0} chars):\n{dossier_response[:2000] if dossier_response else 'NONE'}...")

                if not dossier_response:
                    yield json.dumps({"type": "status", "message": f"[{point_index}] Dossier-Erstellung fehlgeschlagen"}) + "\n"
                    yield json.dumps({
                        "type": "point_complete",
                        "point_title": current_point,
                        "point_number": point_index,
                        "total_points": total_points,
                        "skipped": True,
                        "skip_reason": "Dossier LLM fehlgeschlagen",
                        "key_learnings": "Übersprungen - LLM konnte kein Dossier erstellen"
                    }) + "\n"
                    continue

                # Dossier + Key Learnings extrahieren
                dossier_text, key_learnings = parse_dossier_response(dossier_response)
                logger.info(f"[{point_index}] [DOSSIER] PARSED: dossier={len(dossier_text)} chars, learnings={len(key_learnings)} chars")
                logger.info(f"[{point_index}] [DOSSIER] KEY LEARNINGS:\n{key_learnings[:500] if key_learnings else 'NONE'}...")

                # Speichern
                completed_dossiers.append({
                    "point": current_point,
                    "dossier": dossier_text,
                    "sources": list(scraped_contents.keys())
                })

                # Key Learnings akkumulieren für nächste Punkte
                if key_learnings:
                    accumulated_learnings.append(key_learnings)

                yield json.dumps({"type": "status", "message": f"[{point_index}] Dossier fertig!"}) + "\n"

                # Point Complete Event für Frontend (mit Key Learnings + vollem Dossier für Ausklappen)
                yield json.dumps({
                    "type": "point_complete",
                    "point_title": current_point,
                    "point_number": point_index,
                    "total_points": total_points,
                    "remaining_count": len(remaining_points),
                    "key_learnings": key_learnings or "Keine Key Learnings extrahiert",
                    "dossier_full": dossier_text,  # Volles Dossier für "Mehr anzeigen" Button
                    "sources": list(scraped_contents.keys())
                }) + "\n"

                # Kurze Pause nach point_complete damit Frontend Zeit hat zu rendern
                # WICHTIG: Verhindert dass letztes Dossier mit Final Synthesis verschluckt wird
                await asyncio.sleep(0.3)

            # === FINAL SYNTHESIS ===
            if completed_dossiers:
                yield json.dumps({"type": "status", "message": "Starte finale Synthese..."}) + "\n"
                yield json.dumps({"type": "status", "message": f"Kombiniere {len(completed_dossiers)} Dossiers zu Gesamtdokument..."}) + "\n"

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
                    "message": "Final Synthesis läuft - das dauert einige Minuten...",
                    "estimated_minutes": estimated_minutes,
                    "dossier_count": len(completed_dossiers),
                    "total_sources": len(set(all_sources))
                }) + "\n"

                step_start = time.time()

                final_document = call_llm(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=FINAL_SYNTHESIS_MODEL,
                    timeout=FINAL_SYNTHESIS_TIMEOUT,
                    max_tokens=32000  # Final Synthesis braucht VIEL mehr als 8000!
                )
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
                    yield json.dumps({"type": "status", "message": "Final Synthesis fehlgeschlagen, nutze Fallback..."}) + "\n"
                    final_document = "# Recherche-Ergebnis\n\n"
                    for d in completed_dossiers:
                        final_document += f"## {d['point']}\n\n{d['dossier']}\n\n---\n\n"

            else:
                final_document = "Keine Dossiers erstellt - Recherche fehlgeschlagen."

            # === DONE ===
            duration = time.time() - start_time

            yield json.dumps({"type": "status", "message": f"Recherche abgeschlossen in {duration:.1f}s"}) + "\n"

            yield json.dumps({
                "type": "done",
                "data": {
                    "final_document": final_document,
                    "total_points": len(completed_dossiers),
                    "total_sources": len(set(all_sources)),
                    "duration_seconds": duration,
                    "error": None
                }
            }) + "\n"

        except Exception as e:
            logger.error(f"Deep Research failed: {e}", exc_info=True)
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )


# === SYNTHESIS RECOVERY ENDPOINT ===

class SynthesisRecoveryResponse(BaseModel):
    """Response für Synthesis Recovery."""
    success: bool
    final_document: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None


@router.get("/latest-synthesis", response_model=SynthesisRecoveryResponse)
async def get_latest_synthesis():
    """
    Holt die neueste gespeicherte Final Synthesis aus dem Backup-Ordner.

    Wird verwendet wenn die SSE-Verbindung unterbrochen wurde und das
    Frontend die Synthesis nicht empfangen hat.
    """
    try:
        backup_dir = Path(__file__).parent.parent.parent / "final_synthesis_backups"

        if not backup_dir.exists():
            return SynthesisRecoveryResponse(
                success=False,
                error="Kein Backup-Ordner gefunden"
            )

        # Neueste .md Datei finden
        md_files = list(backup_dir.glob("synthesis_*.md"))

        if not md_files:
            return SynthesisRecoveryResponse(
                success=False,
                error="Keine Synthesis-Backups gefunden"
            )

        # Nach Änderungsdatum sortieren (neueste zuerst)
        latest_file = max(md_files, key=lambda f: f.stat().st_mtime)

        content = latest_file.read_text(encoding="utf-8")

        logger.info(f"[RECOVERY] Loaded synthesis from {latest_file.name} ({len(content)} chars)")

        return SynthesisRecoveryResponse(
            success=True,
            final_document=content,
            filename=latest_file.name
        )

    except Exception as e:
        logger.error(f"[RECOVERY] Failed to load synthesis: {e}")
        return SynthesisRecoveryResponse(
            success=False,
            error=str(e)
        )
