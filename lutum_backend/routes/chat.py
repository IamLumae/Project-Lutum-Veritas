"""
Chat Endpoint
=============
Hauptendpoint für Web-Analyse Requests.

Nimmt User-Nachrichten entgegen und delegiert an LutumService.
"""

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from lutum.core.log_config import get_logger
from lutum.core.api_config import set_api_config
from lutum_backend.services.lutum_service import LutumService

logger = get_logger(__name__)
router = APIRouter(tags=["Chat"])


def _get_lutum_service() -> LutumService:
    """
    Factory für LutumService Instanz.

    Returns:
        LutumService Instanz
    """
    logger.debug("Creating LutumService instance")

    try:
        service = LutumService()
        logger.debug("LutumService created")
        return service

    except Exception as e:
        logger.error(f"Failed to create LutumService: {e}")
        raise


# Service Instanz (Singleton für Performance)
lutum_service = _get_lutum_service()


class ChatRequest(BaseModel):
    """
    Request Body für /chat Endpoint.

    Attributes:
        message: User Nachricht, kann URL + Query enthalten
        api_key: Optional OpenRouter API Key Override
        max_iterations: Max Iterationen für komplexe Anfragen (1-20)
    """
    message: str = Field(..., description="User Nachricht / URL + Query", max_length=10000)
    api_key: Optional[str] = Field(None, description="OpenRouter API Key (überschreibt Default)", max_length=200)
    max_iterations: int = Field(5, ge=1, le=20, description="Max Iterationen für komplexe Anfragen")
    provider: str = Field("openrouter", description="API Provider", max_length=50)
    work_model: str = Field("google/gemini-2.5-flash-lite-preview-09-2025", description="LLM Modell", max_length=100)
    base_url: str = Field("https://openrouter.ai/api/v1/chat/completions", description="API Base URL")


class ChatResponse(BaseModel):
    """
    Response Body für /chat Endpoint.

    Attributes:
        response: LLM Antwort Text
        url_scraped: Gescrapte URL falls vorhanden
        chars_scraped: Anzahl gescrapeter Zeichen
        error: Fehlermeldung falls aufgetreten
    """
    response: str = Field(..., description="LLM Antwort")
    url_scraped: Optional[str] = Field(None, description="Gescrapte URL falls vorhanden")
    chars_scraped: Optional[int] = Field(None, description="Anzahl gescrapeter Zeichen")
    error: Optional[str] = Field(None, description="Fehlermeldung falls aufgetreten")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat mit Lutum Veritas.

    Analysiert URLs oder beantwortet Fragen basierend auf Web-Content.
    Extrahiert automatisch URLs aus der Nachricht und scraped die Seite.

    Args:
        request: ChatRequest mit message, optional api_key und max_iterations

    Returns:
        ChatResponse mit LLM Antwort und Metadaten

    Raises:
        HTTPException 400: Bei ungültiger Anfrage
        HTTPException 500: Bei internen Fehlern
    """
    logger.debug(f"Chat request received: {request.message[:100] if request.message else 'EMPTY'}...")

    try:
        set_api_config(
            key=request.api_key or "",
            provider=request.provider,
            work_model=request.work_model,
            base_url=request.base_url
        )
        result = await lutum_service.process_message(
            message=request.message,
            api_key=request.api_key,
            max_iterations=request.max_iterations
        )

        logger.info(f"Chat response: {len(result.get('response', '')):,} chars")

        return ChatResponse(
            response=result["response"],
            url_scraped=result.get("url"),
            chars_scraped=result.get("chars_scraped")
        )

    except ValueError as e:
        # Ungültige Anfrage (leere Message etc.)
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail="Invalid request parameters")

    except RuntimeError as e:
        # Scrape/Analyze Fehler - gibt Response mit Error zurück statt Exception
        logger.error(f"Processing failed: {e}")
        return ChatResponse(
            response="",
            error="Processing failed. Please try again."
        )

    except Exception as e:
        # Unerwartete Fehler
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
