"""
Lutum Service
=============
Minimaler Service Layer - ruft nur die Pipeline auf.

Die Pipeline lädt Steps dynamisch.
Dieser Service wird NIE wieder geändert (außer für neue API-Parameter).
"""

from typing import Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lutum.core.log_config import get_logger
from lutum.researcher.pipeline import run_pipeline, format_pipeline_response

logger = get_logger(__name__)


class LutumService:
    """
    Service Layer für Lutum Veritas.

    Minimal by design - delegiert alles an pipeline.py
    """

    def __init__(self):
        """Initialisiert den Service mit Logger."""
        self.logger = get_logger(f"{__name__}.LutumService")
        self.logger.debug("LutumService initialized")

    async def process_message(
        self,
        message: str,
        api_key: Optional[str] = None,
        max_iterations: int = 5
    ) -> dict:
        """
        Verarbeitet User-Nachricht durch die Pipeline.

        Args:
            message: User Nachricht / Research-Auftrag
            api_key: Optional API Key Override (zukünftig)
            max_iterations: Max Iterationen / Steps

        Returns:
            Dict mit keys: response, url, chars_scraped

        Raises:
            ValueError: Bei leerer Nachricht
            RuntimeError: Bei Verarbeitungsfehlern
        """
        self.logger.debug(f"Processing message: {message[:100] if message else 'EMPTY'}...")

        try:
            # Validierung
            if not message or not message.strip():
                self.logger.warning("Empty message received")
                raise ValueError("Message cannot be empty")

            # Pipeline ausführen (async)
            self.logger.info(f"Starting pipeline with max_step={max_iterations}")

            context = await run_pipeline(message, max_step=max_iterations)

            # Response formatieren
            response_text = format_pipeline_response(context)

            return {
                "response": response_text,
                "url": None,
                "chars_scraped": len(response_text)
            }

        except ValueError:
            raise

        except Exception as e:
            self.logger.error(f"Unexpected error processing message: {e}", exc_info=True)
            raise RuntimeError(f"Processing failed: {e}")
