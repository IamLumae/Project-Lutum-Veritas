"""
Lutum Veritas - Base Scraper
============================
Abstrakte Basisklasse für alle Scraper-Implementierungen.

ACHTUNG: Nicht direkt instanziieren - nur als Basis für konkrete Scraper.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple

from lutum.core.config import ScraperConfig, DEFAULT_CONFIG
from lutum.core.log_config import get_logger
from lutum.extractor.content import ContentExtractor


class BaseScraper(ABC):
    """
    Abstrakte Basisklasse für Scraper.

    Jede Stufe implementiert diese Klasse mit ihrer spezifischen Logik.

    Attributes:
        level: Stufen-Nummer (1-4)
        name: Stufen-Name (SIMPLE, STEALTH, etc.)
        description: Kurze Beschreibung der Methode

    ACHTUNG: Subklassen MÜSSEN _scrape_impl() implementieren.
    """

    # Diese Attribute müssen von Subklassen überschrieben werden
    level: int = 0
    name: str = "BASE"
    description: str = "Basis-Scraper"

    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialisiert den Scraper.

        Args:
            config: Scraper-Konfiguration (oder Default)
        """
        self.config = config or DEFAULT_CONFIG
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.extractor = ContentExtractor(min_length=self.config.min_content_length)

        self.logger.debug(f"Initialisiert: {self.name} (Level {self.level})")

    @abstractmethod
    def _scrape_impl(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Implementierung des Scrapens.

        Args:
            url: Zu scrapende URL

        Returns:
            Tuple (html, error_message)
            - html: Rohes HTML bei Erfolg, None bei Fehler
            - error_message: None bei Erfolg, Fehlermeldung bei Fehler

        ACHTUNG: Diese Methode muss von Subklassen implementiert werden.
                 Sie sollte KEINE Exceptions werfen, sondern Fehler als
                 (None, error_message) zurückgeben.
        """
        pass

    def scrape(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Scraped eine URL und extrahiert Content.

        Args:
            url: Zu scrapende URL

        Returns:
            Tuple (content, html)
            - Bei Erfolg: (extrahierter_content, rohes_html)
            - Bei Fehler: (None, None)

        ACHTUNG: Gibt KEINE Exceptions weiter - alle Fehler werden geloggt
                 und als (None, None) zurückgegeben.
        """
        self.logger.debug(f"Start scrape: {url}")

        try:
            # Hole HTML
            html, error = self._scrape_impl(url)

            if error:
                self.logger.warning(f"Scrape fehlgeschlagen: {error}")
                return (None, None)

            if not html:
                self.logger.warning("Leeres HTML erhalten")
                return (None, None)

            self.logger.debug(f"HTML erhalten: {len(html)} Bytes")

            # Extrahiere Content
            content = self.extractor.extract(html, url)

            if content:
                self.logger.info(f"Scrape erfolgreich: {len(content)} Zeichen")
                return (content, html)
            else:
                self.logger.warning("Content-Extraktion ergab keinen gültigen Content")
                return (None, html)

        except Exception as e:
            # ACHTUNG: Catch-All - Scraper dürfen nicht crashen
            self.logger.error(f"Unerwarteter Fehler: {e}", exc_info=True)
            return (None, None)

    def is_available(self) -> bool:
        """
        Prüft ob alle Dependencies für diesen Scraper verfügbar sind.

        Returns:
            True wenn nutzbar, False wenn Dependencies fehlen

        ACHTUNG: Subklassen sollten dies überschreiben wenn sie
                 optionale Dependencies haben.
        """
        return True

    def __str__(self) -> str:
        return f"[Stufe {self.level}] {self.name}: {self.description}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(level={self.level}, name={self.name!r})"
