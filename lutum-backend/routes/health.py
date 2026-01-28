"""
Health Check Endpoint
=====================
Simple health check für Frontend und Monitoring.
"""

import sys
from pathlib import Path

from fastapi import APIRouter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from lutum.core.log_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Health Check Endpoint.

    Gibt Status zurück wenn Server läuft.
    Wird vom Frontend genutzt um Backend-Verfügbarkeit zu prüfen.

    Returns:
        Dict mit status und service name
    """
    logger.debug("Health check requested")

    try:
        response = {
            "status": "ok",
            "service": "lutum-veritas"
        }
        logger.debug("Health check OK")
        return response

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "service": "lutum-veritas",
            "error": str(e)
        }
