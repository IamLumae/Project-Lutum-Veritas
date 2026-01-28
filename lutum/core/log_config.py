"""
Lutum Veritas - Logging Setup
=============================
Zentrales Logging für alle Module.

Log Levels:
- DEBUG: Alles (Entwicklung)
- INFO:  Normale Operationen
- WARNING: Recoverable Fehler
- ERROR: Kritische Fehler

Usage:
    from lutum.core.log_config import get_logger
    logger = get_logger(__name__)
"""

import logging
import sys
from typing import Optional


# ACHTUNG: Globaler State - wird einmal beim Import konfiguriert
_configured = False

# Format für Log-Nachrichten
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FORMAT_DEBUG = "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: int = logging.INFO,
    debug: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    Konfiguriert das Logging für das gesamte Projekt.

    Args:
        level: Log Level (DEBUG, INFO, WARNING, ERROR)
        debug: Wenn True, wird DEBUG Level und erweitertes Format verwendet
        log_file: Optional - Pfad zu Log-Datei

    ACHTUNG: Sollte nur einmal am Programmstart aufgerufen werden.
             Mehrfache Aufrufe überschreiben vorherige Konfiguration.
    """
    global _configured

    # Level Override wenn debug=True
    if debug:
        level = logging.DEBUG

    # Format basierend auf Level
    log_format = LOG_FORMAT_DEBUG if level == logging.DEBUG else LOG_FORMAT

    # Handlers
    handlers = []

    # Console Handler - immer
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format, DATE_FORMAT))
    handlers.append(console_handler)

    # File Handler - optional
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(log_format, DATE_FORMAT))
            handlers.append(file_handler)
        except Exception as e:
            # Log-File kann nicht erstellt werden - nicht kritisch
            print(f"[WARNING] Log-File konnte nicht erstellt werden: {e}", file=sys.stderr)

    # Root Logger konfigurieren
    root_logger = logging.getLogger("lutum")
    root_logger.setLevel(level)

    # Alte Handler entfernen
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Neue Handler hinzufügen
    for handler in handlers:
        root_logger.addHandler(handler)

    _configured = True
    root_logger.debug("Logging konfiguriert (Level: %s)", logging.getLevelName(level))


def get_logger(name: str) -> logging.Logger:
    """
    Gibt einen Logger für das angegebene Modul zurück.

    Args:
        name: Modulname (üblicherweise __name__)

    Returns:
        Konfigurierter Logger

    Usage:
        logger = get_logger(__name__)
        logger.info("Das ist eine Info")
        logger.error("Das ist ein Fehler", exc_info=True)
    """
    # Auto-Setup wenn noch nicht konfiguriert
    if not _configured:
        setup_logging()

    # Stelle sicher dass der Name mit "lutum" prefixed ist
    if not name.startswith("lutum"):
        name = f"lutum.{name}"

    return logging.getLogger(name)


# Convenience-Funktionen für schnellen Zugriff
def set_debug() -> None:
    """Schaltet auf DEBUG Level um."""
    setup_logging(debug=True)


def set_quiet() -> None:
    """Schaltet auf ERROR-only um."""
    setup_logging(level=logging.ERROR)


def set_info() -> None:
    """Schaltet auf INFO Level um (Default)."""
    setup_logging(level=logging.INFO)
