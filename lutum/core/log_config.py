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

Live Log Buffer:
    from lutum.core.log_config import get_and_clear_log_buffer
    logs = get_and_clear_log_buffer()  # Returns list of {"level", "message", "short"} dicts
"""

import logging
import os
import sys
from collections import deque
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Optional


# ACHTUNG: Globaler State - wird einmal beim Import konfiguriert
_configured = False

# === LIVE LOG BUFFER ===
# Captures WARN/ERROR logs for streaming to frontend
_log_buffer: deque = deque(maxlen=100)  # Max 100 entries
_log_buffer_lock = Lock()

# Format für Log-Nachrichten
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FORMAT_DEBUG = "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# === LIVE LOG BUFFER HANDLER ===
# Must be defined BEFORE setup_logging

class LiveLogHandler(logging.Handler):
    """
    Custom handler that captures WARN/ERROR logs to a buffer
    for streaming to the frontend.
    """

    def __init__(self):
        super().__init__(level=logging.WARNING)  # Only WARN and above

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            level = record.levelname
            with _log_buffer_lock:
                _log_buffer.append({
                    "level": level,
                    "message": msg,
                    "module": record.name,
                    "short": record.getMessage()[:200]  # Truncated version for UI
                })
        except Exception:
            pass  # Never crash on logging


def get_and_clear_log_buffer() -> list:
    """
    Get all buffered WARN/ERROR logs and clear the buffer.

    Returns:
        List of log entries: [{"level": "WARNING", "message": "...", "short": "..."}, ...]
    """
    with _log_buffer_lock:
        logs = list(_log_buffer)
        _log_buffer.clear()
    return logs


def peek_log_buffer() -> list:
    """
    Peek at the log buffer without clearing it.

    Returns:
        List of log entries
    """
    with _log_buffer_lock:
        return list(_log_buffer)


def _install_live_handler():
    """Install the live log handler on the lutum logger."""
    root_logger = logging.getLogger("lutum")

    # Check if already installed
    for handler in root_logger.handlers:
        if isinstance(handler, LiveLogHandler):
            return

    live_handler = LiveLogHandler()
    live_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    root_logger.addHandler(live_handler)


def _resolve_log_path(log_file: Optional[str]) -> Optional[Path]:
    """
    Resolve log file path (creates parent dir if needed).

    Uses LUTUM_LOG_FILE or LUTUM_LOG_DIR when no explicit log_file is provided.
    """
    if log_file:
        return Path(log_file).expanduser()

    if os.getenv("LUTUM_DISABLE_LOG_FILE") == "1":
        return None

    log_dir = os.getenv("LUTUM_LOG_DIR")
    if log_dir:
        base_dir = Path(log_dir).expanduser()
    else:
        base_dir = Path.home() / ".lutum-veritas" / "logs"

    return base_dir / "lutum.log"


# === MAIN LOGGING SETUP ===

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

    # File Handler - optional (daily rotation)
    resolved_path = _resolve_log_path(log_file)
    if resolved_path:
        try:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = TimedRotatingFileHandler(
                resolved_path,
                when="midnight",
                interval=1,
                backupCount=14,
                encoding="utf-8",
                delay=True
            )
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

    # Install live log handler for frontend streaming
    _install_live_handler()

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
