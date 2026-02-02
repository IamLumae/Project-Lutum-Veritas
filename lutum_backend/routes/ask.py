"""
Ask Mode - Deep Question Pipeline
==================================
6-Stage Verification System mit dual scraping phases.

Endpoints:
    GET /ask/events/{session_id} - SSE stream für live updates
    POST /ask/start - Startet Deep Question Pipeline
    GET /ask/list - Listet alle Ask Sessions

Architecture:
    C1: Intent Analysis
    C2: Knowledge Requirements
    C3: Search Queries (10)
    → SCRAPE Phase 1 (10 URLs parallel)
    C4: Answer Synthesis mit Citations [1], [2], ...
    C5: Claim Audit + Verification Queries (10)
    → SCRAPE Phase 2 (10 URLs parallel)
    C6: Final Verification Report mit [V1], [V2], ...

Model: google/gemini-2.5-flash-lite-preview-09-2025
Runtime: ~70-80s per query
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Import Deep Question Pipeline
import sys
try:
    # Try direct import first (works when installed as package)
    from deep_question_pipeline import DeepQuestionPipeline
except ImportError:
    # Fallback: add parent path for development mode
    pipeline_path = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(pipeline_path))
    from deep_question_pipeline import DeepQuestionPipeline
from lutum.core.log_config import get_logger, get_and_clear_log_buffer

logger = get_logger(__name__)
router = APIRouter(prefix="/ask", tags=["ask"])

# === i18n MESSAGES ===
ASK_MESSAGES = {
    # Connection
    "connected": {"de": "Verbunden - Ask Mode bereit", "en": "Connected - Ask Mode ready"},
    "starting": {"de": "Starte Deep Question Pipeline...", "en": "Starting Deep Question Pipeline..."},

    # Stages
    "c1_start": {"de": "C1: Analysiere deine Frage...", "en": "C1: Analyzing your question..."},
    "c1_done": {"de": "C1: Ich verstehe was du wissen möchtest", "en": "C1: I understand what you want to know"},

    "c2_start": {"de": "C2: Ermittle benötigtes Wissen...", "en": "C2: Determining required knowledge..."},
    "c2_done": {"de": "C2: Wissensanforderungen identifiziert", "en": "C2: Knowledge requirements identified"},

    "c3_start": {"de": "C3: Generiere Suchstrategien...", "en": "C3: Generating search strategies..."},
    "c3_done": {"de": "C3: {count} Suchanfragen erstellt", "en": "C3: {count} search queries created"},

    "scrape1_start": {"de": "SCRAPE 1: Durchsuche Quellen parallel...", "en": "SCRAPE 1: Searching sources in parallel..."},
    "scrape1_progress": {"de": "SCRAPE 1: {done}/{total} URLs gelesen", "en": "SCRAPE 1: {done}/{total} URLs read"},
    "scrape1_done": {"de": "SCRAPE 1: {count} Quellen erfolgreich gelesen", "en": "SCRAPE 1: {count} sources successfully read"},

    "c4_start": {"de": "C4: Synthetisiere Antwort mit Quellenbelegen...", "en": "C4: Synthesizing answer with citations..."},
    "c4_done": {"de": "C4: Antwort erstellt mit Quellenbelegen", "en": "C4: Answer created with citations"},

    "c5_start": {"de": "C5: Prüfe Behauptungen und erstelle Verifikationsqueries...", "en": "C5: Auditing claims and creating verification queries..."},
    "c5_done": {"de": "C5: {count} Verifikationsqueries generiert", "en": "C5: {count} verification queries generated"},

    "scrape2_start": {"de": "SCRAPE 2: Verifiziere mit zusätzlichen Quellen...", "en": "SCRAPE 2: Verifying with additional sources..."},
    "scrape2_progress": {"de": "SCRAPE 2: {done}/{total} URLs gelesen", "en": "SCRAPE 2: {done}/{total} URLs read"},
    "scrape2_done": {"de": "SCRAPE 2: {count} Verifikationsquellen gelesen", "en": "SCRAPE 2: {count} verification sources read"},

    "c6_start": {"de": "C6: Erstelle finale Verifikation...", "en": "C6: Creating final verification..."},
    "c6_done": {"de": "C6: Verifikationsbericht fertig", "en": "C6: Verification report complete"},

    "complete": {"de": "Deep Question abgeschlossen in {duration}s", "en": "Deep Question complete in {duration}s"},

    # Errors
    "error": {"de": "Fehler: {message}", "en": "Error: {message}"},
    "stage_failed": {"de": "Stage {stage} fehlgeschlagen: {error}", "en": "Stage {stage} failed: {error}"},
}


def t(key: str, lang: str = "de", **kwargs) -> str:
    """Translate Ask message key to specified language."""
    if key not in ASK_MESSAGES:
        logger.warning(f"Missing Ask translation key: {key}")
        return key

    msg = ASK_MESSAGES[key].get(lang, ASK_MESSAGES[key].get("de", key))
    try:
        return msg.format(**kwargs) if kwargs else msg
    except KeyError as e:
        logger.warning(f"Missing format arg for {key}: {e}")
        return msg


# === EVENT BUS ===
_ask_event_queues: dict[str, asyncio.Queue] = {}


def emit_ask_event(session_id: str, event_type: str, message: str, data: Optional[dict] = None):
    """
    Emit event to all listeners of an Ask session.

    Args:
        session_id: Session ID
        event_type: e.g. "stage_start", "stage_done", "stage_content", "error"
        message: Display text for frontend
        data: Optional additional data (e.g. stage content)
    """
    if session_id in _ask_event_queues:
        try:
            event = {
                "type": event_type,
                "message": message,
            }
            if data:
                event["data"] = data

            _ask_event_queues[session_id].put_nowait(event)
            logger.debug(f"Ask event emitted: {session_id} -> {event_type}: {message}")
        except asyncio.QueueFull:
            logger.warning(f"Ask event queue full for session {session_id}")


def emit_ask_log_buffer(session_id: str):
    """
    Emit buffered WARN/ERROR logs as ask events.

    Uses the shared lutum log buffer to surface backend warnings/errors in UI.
    """
    logs = get_and_clear_log_buffer()
    for log in logs:
        emit_ask_event(
            session_id,
            "log",
            log["short"],
            {"level": log["level"], "full": log["message"]}
        )


# === SSE ENDPOINT ===
@router.get("/events/{session_id}")
async def ask_events(session_id: str):
    """
    SSE Endpoint - Frontend connects here for live Deep Question updates.

    Args:
        session_id: Session ID to receive events for

    Returns:
        StreamingResponse with SSE events
    """
    logger.info(f"Ask SSE connection opened for session: {session_id}")

    # Create queue if doesn't exist
    if session_id not in _ask_event_queues:
        _ask_event_queues[session_id] = asyncio.Queue(maxsize=100)
        logger.debug(f"Created Ask event queue for session {session_id}")

    async def event_generator():
        try:
            # Initial connected event
            yield f"data: {json.dumps({'type': 'connected', 'message': t('connected')})}\n\n"

            while True:
                try:
                    # Wait for event with timeout (keep-alive)
                    event = await asyncio.wait_for(
                        _ask_event_queues[session_id].get(),
                        timeout=30.0
                    )
                    # Send as JSON
                    yield f"data: {json.dumps(event)}\n\n"

                    # End on "done" event
                    if event["type"] == "done":
                        break

                except asyncio.TimeoutError:
                    # Keep-alive ping
                    yield f"data: {json.dumps({'type': 'ping', 'message': ''})}\n\n"

        finally:
            # Cleanup
            if session_id in _ask_event_queues:
                del _ask_event_queues[session_id]
            logger.info(f"Ask SSE connection closed for session: {session_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# === PYDANTIC MODELS ===
class AskStartRequest(BaseModel):
    """Request body for /ask/start."""
    question: str = Field(..., description="User question to analyze", max_length=5000)
    session_id: str = Field(..., description="Session ID for SSE events", max_length=100)
    api_key: str = Field(..., description="OpenRouter API Key", max_length=200)
    language: str = Field("de", description="Response language (de/en)", max_length=5)


class AskStartResponse(BaseModel):
    """Response body for /ask/start."""
    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Status: 'started', 'error'")
    message: str = Field("", description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")


class AskSession(BaseModel):
    """Ask session metadata."""
    session_id: str
    question: str
    created_at: datetime
    completed: bool
    duration_seconds: Optional[float] = None


# === SIMPLE IN-MEMORY STORAGE ===
# NOTE: This is file-based for Lutum Desktop App (local only)
_ask_sessions: dict[str, AskSession] = {}


# === START ENDPOINT ===
@router.post("/start", response_model=AskStartResponse)
async def ask_start(request: AskStartRequest):
    """
    Start Deep Question Pipeline.

    1. Creates event queue for session
    2. Spawns background task for pipeline
    3. Returns immediately
    4. Frontend listens on /ask/events/{session_id} for updates

    Args:
        request: AskStartRequest with question, session_id, api_key

    Returns:
        AskStartResponse with session_id and status
    """
    try:
        # Create event queue
        if request.session_id not in _ask_event_queues:
            _ask_event_queues[request.session_id] = asyncio.Queue(maxsize=100)
            logger.info(f"Created Ask queue for session: {request.session_id}")

        # Validate payload early so user gets feedback in chat
        if not request.question or not request.question.strip():
            emit_ask_event(request.session_id, "error", t("error", request.language, message="Question cannot be empty"))
            return AskStartResponse(
                session_id=request.session_id,
                status="error",
                error="Question cannot be empty",
                message=t("error", request.language, message="Question cannot be empty")
            )

        if not request.api_key or not request.api_key.strip():
            emit_ask_event(request.session_id, "error", t("error", request.language, message="API key missing"))
            return AskStartResponse(
                session_id=request.session_id,
                status="error",
                error="API key missing",
                message=t("error", request.language, message="API key missing")
            )

        # Store session metadata
        _ask_sessions[request.session_id] = AskSession(
            session_id=request.session_id,
            question=request.question,
            created_at=datetime.now(),
            completed=False
        )

        # Emit starting event
        emit_ask_event(request.session_id, "starting", t("starting", request.language))
        emit_ask_log_buffer(request.session_id)

        # Spawn background task for pipeline
        asyncio.create_task(
            _run_deep_question_pipeline(
                session_id=request.session_id,
                question=request.question,
                api_key=request.api_key,
                language=request.language
            )
        )

        logger.info(f"Ask pipeline started for session: {request.session_id}")

        return AskStartResponse(
            session_id=request.session_id,
            status="started",
            message=t("starting", request.language)
        )

    except Exception as e:
        logger.error(f"Failed to start Ask pipeline: {e}", exc_info=True)
        if request.session_id not in _ask_event_queues:
            _ask_event_queues[request.session_id] = asyncio.Queue(maxsize=100)
        emit_ask_log_buffer(request.session_id)
        emit_ask_event(
            request.session_id,
            "error",
            t("error", request.language, message=str(e)),
            {"error": str(e)}
        )
        return AskStartResponse(
            session_id=request.session_id,
            status="error",
            error=str(e)
        )


# === PIPELINE RUNNER ===
async def _run_deep_question_pipeline(
    session_id: str,
    question: str,
    api_key: str,
    language: str
):
    """
    Run Deep Question Pipeline in background.
    Emits SSE events at each stage.
    """
    start_time = datetime.now()

    try:
        # Initialize pipeline
        pipeline = DeepQuestionPipeline(
            user_query=question,
            api_key=api_key
        )
        emit_ask_log_buffer(session_id)

        # === C1: Intent Analysis ===
        emit_ask_event(session_id, "stage_start", t("c1_start", language), {"stage": "C1"})

        c1_prompt = f"""USER QUERY:
{question}

Analyze the language of the user query above and respond in that same language.

---

Explain in first person what you understand they want to know.

Format your response naturally, starting with:
"Der Nutzer möchte..." (if German) or "The user wants to know..." (if English)

Explain in 3-5 sentences:
- What exactly they are asking
- What they want to know
- What kind of answer they expect

---

REMINDER: Respond in the same language as the user query above. Without exception."""

        c1_result = await asyncio.to_thread(lambda: pipeline._call_openrouter(c1_prompt, "C1_Intent"))
        emit_ask_log_buffer(session_id)
        emit_ask_event(
            session_id,
            "stage_content",
            t("c1_done", language),
            {"stage": "C1", "content": c1_result}
        )

        # === C2: Knowledge Requirements ===
        emit_ask_event(session_id, "stage_start", t("c2_start", language), {"stage": "C2"})

        c2_prompt = f"""USER QUERY:
{question}

Analyze the language of the user query above and respond in that same language.

---

Based on the user query and intent analysis below, explain in first person what information you need to answer comprehensively.

Intent Analysis:
{c1_result}

---

Format your response naturally, starting with:
"Um diese Frage zu beantworten, benötige ich..." (if German) or "To answer this question, I need..." (if English)

List in bullet points:
- What specific information you need from the internet
- What data sources would be most reliable
- What aspects need to be researched

Remember: Your training data is irrelevant. Only assess what information is NEEDED, not what you think you already know.

---

REMINDER: Respond in the same language as the user query above. Without exception."""

        c2_result = await asyncio.to_thread(lambda: pipeline._call_openrouter(c2_prompt, "C2_Knowledge"))
        emit_ask_log_buffer(session_id)
        emit_ask_event(
            session_id,
            "stage_content",
            t("c2_done", language),
            {"stage": "C2", "content": c2_result}
        )

        # === C3: Search Queries ===
        emit_ask_event(session_id, "stage_start", t("c3_start", language), {"stage": "C3"})

        c3_prompt = f"""USER QUERY:
{question}

Analyze the language of the user query above and respond in that same language.

---

Based on all previous analysis, explain in first person which search queries you will use to gather information.

Intent Analysis:
{c1_result}

Knowledge Requirements:
{c2_result}

---

Format your response naturally, starting with:
"Ich sollte nun Quellen suchen um die Frage zu beantworten. Ich entscheide mich für folgende 10 Suchbegriffe:" (if German)
or
"I should now search for sources to answer the question. I will use these 10 search terms:" (if English)

Then list exactly 10 search queries as a numbered list:
1. [first search query]
2. [second search query]
...
10. [tenth search query]

The first 5 queries should target direct information.
The last 5 queries should diversify or verify the information.

---

REMINDER: Respond in the same language as the user query above. Without exception."""

        c3_result = await asyncio.to_thread(lambda: pipeline._call_openrouter(c3_prompt, "C3_Queries"))
        emit_ask_log_buffer(session_id)
        queries_initial = pipeline._parse_numbered_list(c3_result)
        emit_ask_event(
            session_id,
            "stage_content",
            t("c3_done", language, count=len(queries_initial)),
            {"stage": "C3", "content": c3_result, "queries": queries_initial}
        )

        # === SCRAPE Phase 1 ===
        emit_ask_event(session_id, "scrape_start", t("scrape1_start", language), {"phase": 1})

        # Use pipeline's async scraping method with progress callback
        async def scrape1_progress(done: int, total: int):
            emit_ask_event(
                session_id,
                "scrape_progress",
                t("scrape1_progress", language, done=done, total=total),
                {"phase": 1, "done": done, "total": total}
            )

        scraped_results_1 = await pipeline._search_and_scrape_async(
            queries_initial,
            stage="Scraping_Phase_1",
            progress_callback=scrape1_progress
        )
        emit_ask_log_buffer(session_id)

        successful_scrapes_1 = sum(1 for r in scraped_results_1 if r.get("success"))
        emit_ask_event(
            session_id,
            "scrape_done",
            t("scrape1_done", language, count=successful_scrapes_1),
            {"phase": 1, "count": successful_scrapes_1, "total": len(scraped_results_1)}
        )

        # === C4: Answer Synthesis ===
        emit_ask_event(session_id, "stage_start", t("c4_start", language), {"stage": "C4"})

        formatted_sources = pipeline._format_scraped_results(scraped_results_1)
        c4_prompt = f"""USER QUERY:
{question}

Analyze the language of the user query above and respond in that same language.

---

Based on all information gathered, compose a comprehensive answer.

Intent Analysis:
{c1_result}

Knowledge Requirements:
{c2_result}

Scraped Sources:
{formatted_sources}

---

Format your response naturally, starting with:
"Ich habe nun die Quellen analysiert. Basierend auf den gefundenen Daten kann ich folgendes beantworten:" (if German)
or
"I have analyzed the sources. Based on the data found, I can answer as follows:" (if English)

Then provide your answer:
- Start with a brief introduction (1-2 sentences)
- Answer thoroughly but concisely
- No filler sentences - only substantial information
- Use citations [1], [2], [3] etc. for every factual claim from the sources
- Data from internet sources ALWAYS takes precedence over your training data

---

REMINDER: Respond in the same language as the user query above. Without exception."""

        c4_result = await asyncio.to_thread(lambda: pipeline._call_openrouter(c4_prompt, "C4_Answer"))
        emit_ask_log_buffer(session_id)
        emit_ask_event(
            session_id,
            "stage_content",
            t("c4_done", language),
            {"stage": "C4", "content": c4_result, "sources": scraped_results_1}
        )

        # === C5: Claim Audit ===
        emit_ask_event(session_id, "stage_start", t("c5_start", language), {"stage": "C5"})

        c5_prompt = f"""USER QUERY:
{question}

Analyze the language of the user query above and respond in that same language.

---

Analyze the AI answer below and explain in first person which claims need fact-checking.

AI Answer to Verify:
{c4_result}

---

Format your response naturally, starting with:
"Ich überprüfe nun die Aussagen auf Richtigkeit. Folgende Claims müssen verifiziert werden:" (if German)
or
"I am now checking the statements for correctness. The following claims need verification:" (if English)

Then list EXACTLY 10 main claims from the answer as a numbered list, each with a verification search query:
1. [claim] → [verification search query]
2. [claim] → [verification search query]
...
10. [claim] → [verification search query]

IMPORTANT: Always create exactly 10 verification queries, no more, no less.
Focus on the most important verifiable factual claims.

---

REMINDER: Respond in the same language as the user query above. Without exception."""

        c5_result = await asyncio.to_thread(lambda: pipeline._call_openrouter(c5_prompt, "C5_Audit"))
        emit_ask_log_buffer(session_id)

        # Parse verification queries (extract after →)
        queries_verification = []
        for line in c5_result.split('\n'):
            if '→' in line:
                query = line.split('→', 1)[1].strip()
                if query:
                    queries_verification.append(query)

        if not queries_verification:
            # Fallback: parse as numbered list
            queries_verification = pipeline._parse_numbered_list(c5_result)

        emit_ask_event(
            session_id,
            "stage_content",
            t("c5_done", language, count=len(queries_verification)),
            {"stage": "C5", "content": c5_result, "queries": queries_verification}
        )

        # === SCRAPE Phase 2 ===
        emit_ask_event(session_id, "scrape_start", t("scrape2_start", language), {"phase": 2})

        async def scrape2_progress(done: int, total: int):
            emit_ask_event(
                session_id,
                "scrape_progress",
                t("scrape2_progress", language, done=done, total=total),
                {"phase": 2, "done": done, "total": total}
            )

        scraped_results_2 = await pipeline._search_and_scrape_async(
            queries_verification,
            stage="Scraping_Phase_2",
            progress_callback=scrape2_progress
        )
        emit_ask_log_buffer(session_id)

        successful_scrapes_2 = sum(1 for r in scraped_results_2 if r.get("success"))
        emit_ask_event(
            session_id,
            "scrape_done",
            t("scrape2_done", language, count=successful_scrapes_2),
            {"phase": 2, "count": successful_scrapes_2, "total": len(scraped_results_2)}
        )

        # === C6: Final Verification ===
        emit_ask_event(session_id, "stage_start", t("c6_start", language), {"stage": "C6"})

        formatted_verification = pipeline._format_scraped_results(scraped_results_2)
        c6_prompt = f"""USER QUERY:
{question}

Analyze the language of the user query above and respond in that same language.

---

Based on the verification sources below, explain in first person the fact-check results.

AI Answer:
{c4_result}

Verification Sources:
{formatted_verification}

---

Format your response naturally, starting with:
"Ich habe die Verifikationsquellen analysiert. Ergebnis:" (if German)
or
"I have analyzed the verification sources. Result:" (if English)

Then list each claim with its verification status:
[OK] [Claim]: Verified - [evidence with [V1], [V2] citations]
[NO] [Claim]: Contradicted - [evidence with [V1], [V2] citations]
[??] [Claim]: Uncertain - [explanation]

Use [V1], [V2], [V3] etc. to cite verification sources.

---

REMINDER: Respond in the same language as the user query above. Without exception."""

        c6_result = await asyncio.to_thread(lambda: pipeline._call_openrouter(c6_prompt, "C6_Verification"))
        emit_ask_log_buffer(session_id)
        emit_ask_event(
            session_id,
            "stage_content",
            t("c6_done", language),
            {"stage": "C6", "content": c6_result, "sources": scraped_results_2}
        )

        # === COMPLETE ===
        duration = (datetime.now() - start_time).total_seconds()

        # Update session
        if session_id in _ask_sessions:
            _ask_sessions[session_id].completed = True
            _ask_sessions[session_id].duration_seconds = duration

        emit_ask_event(
            session_id,
            "done",
            t("complete", language, duration=f"{duration:.1f}"),
            {
                "duration": duration,
                "total_sources": len(scraped_results_1) + len(scraped_results_2)
            }
        )
        emit_ask_log_buffer(session_id)

        logger.info(f"Ask pipeline completed for {session_id} in {duration:.1f}s")

    except Exception as e:
        logger.error(f"Ask pipeline failed for {session_id}: {e}", exc_info=True)
        emit_ask_log_buffer(session_id)
        emit_ask_event(
            session_id,
            "error",
            t("error", language, message=str(e)),
            {"error": str(e)}
        )
        # Still emit done to close connection
        emit_ask_event(session_id, "done", "Pipeline terminated with error")


# === LIST ENDPOINT ===
@router.get("/list")
async def ask_list():
    """
    List all Ask sessions (in-memory).

    Returns:
        List of AskSession metadata
    """
    return list(_ask_sessions.values())
