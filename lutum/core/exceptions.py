"""
Lutum Veritas - Custom Exceptions
=================================
Alle Fehlertypen für das Projekt.

ACHTUNG: Alle Scraper-Methoden fangen diese und loggen sie.
         Sie werden NICHT an den Caller durchgereicht außer explizit dokumentiert.
"""


class LutumError(Exception):
    """Basis-Exception für alle Lutum-Fehler."""
    pass


class ScrapeError(LutumError):
    """Fehler beim Scrapen einer URL."""

    def __init__(self, url: str, message: str, level: int = 0):
        self.url = url
        self.level = level
        super().__init__(f"[Stufe {level}] {url}: {message}")


class ExtractionError(LutumError):
    """Fehler bei der Content-Extraktion."""

    def __init__(self, url: str, message: str):
        self.url = url
        super().__init__(f"Extraction failed for {url}: {message}")


class ConfigError(LutumError):
    """Fehler in der Konfiguration."""
    pass


class TimeoutError(ScrapeError):
    """Timeout beim Scrapen."""

    def __init__(self, url: str, timeout_seconds: float, level: int = 0):
        self.timeout_seconds = timeout_seconds
        super().__init__(url, f"Timeout nach {timeout_seconds}s", level)


class BlockedError(ScrapeError):
    """Website hat den Scraper blockiert."""

    def __init__(self, url: str, status_code: int = 0, level: int = 0):
        self.status_code = status_code
        super().__init__(url, f"Blocked (HTTP {status_code})", level)


class DependencyError(LutumError):
    """Fehlende Dependency für eine Stufe."""

    def __init__(self, dependency: str, install_hint: str):
        self.dependency = dependency
        self.install_hint = install_hint
        super().__init__(f"Missing: {dependency}. Install: {install_hint}")
