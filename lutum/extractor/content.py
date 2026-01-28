"""
Lutum Veritas - Content Extractor
=================================
Extrahiert Hauptcontent aus HTML mit trafilatura.

ACHTUNG: Trafilatura muss installiert sein: pip install trafilatura
         Filtert: Ads, Navigation, Footer, Sidebars, etc.
"""

from typing import Optional

from lutum.core.log_config import get_logger
from lutum.core.exceptions import ExtractionError, DependencyError


class ContentExtractor:
    """
    Extrahiert sauberen Text-Content aus HTML.

    Nutzt trafilatura für intelligente Content-Extraktion.
    Filtert automatisch Werbung, Navigation, Footer, etc.

    Usage:
        extractor = ContentExtractor(min_length=100)
        content = extractor.extract(html, url="https://example.com")
    """

    def __init__(self, min_length: int = 100):
        """
        Initialisiert den Extractor.

        Args:
            min_length: Minimum Zeichen für gültigen Content

        Raises:
            DependencyError: Wenn trafilatura nicht installiert
        """
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.min_length = min_length

        # Prüfe ob trafilatura verfügbar
        # ACHTUNG: Import erst hier um bessere Fehlermeldung zu geben
        try:
            import trafilatura
            self._trafilatura = trafilatura
            self.logger.debug("trafilatura geladen")
        except ImportError as e:
            self.logger.error("trafilatura nicht installiert")
            raise DependencyError(
                dependency="trafilatura",
                install_hint="pip install trafilatura"
            ) from e

    def extract(self, html: str, url: str = "") -> Optional[str]:
        """
        Extrahiert Hauptcontent aus HTML.

        Args:
            html: Rohes HTML
            url: Original-URL (für bessere Extraktion)

        Returns:
            Extrahierter Text oder None wenn zu kurz/leer

        ACHTUNG: Gibt None zurück wenn Content < min_length.
                 Wirft KEINE Exceptions - loggt stattdessen.
        """
        if not html:
            self.logger.warning("Leeres HTML übergeben")
            return None

        if not isinstance(html, str):
            self.logger.warning(f"HTML ist kein String: {type(html)}")
            return None

        try:
            self.logger.debug(f"Extrahiere Content aus {len(html)} Bytes HTML")

            content = self._trafilatura.extract(
                html,
                url=url,
                include_links=True,
                include_tables=True,
                include_images=False,
                include_comments=False,
                favor_recall=True,  # Lieber mehr als weniger Content
                deduplicate=True,
            )

            # Validierung
            if not content:
                self.logger.debug("trafilatura gab keinen Content zurück")
                return None

            content = content.strip()

            if len(content) < self.min_length:
                self.logger.debug(
                    f"Content zu kurz: {len(content)} < {self.min_length} Zeichen"
                )
                return None

            self.logger.debug(f"Content extrahiert: {len(content)} Zeichen")
            return content

        except Exception as e:
            # ACHTUNG: Alle Errors abfangen - Extraction darf nicht crashen
            self.logger.error(f"Extraction fehlgeschlagen: {e}", exc_info=True)
            return None

    def extract_with_fallback(self, html: str, url: str = "") -> Optional[str]:
        """
        Extrahiert Content mit Fallback auf Raw-Text.

        Args:
            html: Rohes HTML
            url: Original-URL

        Returns:
            Content oder einfacher Text-Fallback

        ACHTUNG: Fallback entfernt nur HTML-Tags, keine intelligente Filterung.
        """
        # Versuche normale Extraktion
        content = self.extract(html, url)
        if content:
            return content

        # Fallback: Einfache Tag-Entfernung
        # ACHTUNG: Schlechte Qualität, nur als letzter Ausweg
        self.logger.warning("Fallback auf einfache Tag-Entfernung")

        try:
            import re

            # Entferne Script und Style Blöcke
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

            # Entferne alle Tags
            text = re.sub(r'<[^>]+>', ' ', text)

            # Bereinige Whitespace
            text = re.sub(r'\s+', ' ', text).strip()

            if len(text) >= self.min_length:
                self.logger.debug(f"Fallback-Content: {len(text)} Zeichen")
                return text

            return None

        except Exception as e:
            self.logger.error(f"Fallback fehlgeschlagen: {e}", exc_info=True)
            return None


# Singleton für schnellen Zugriff
# ACHTUNG: Wird beim ersten Import erstellt
_default_extractor: Optional[ContentExtractor] = None


def get_extractor(min_length: int = 100) -> ContentExtractor:
    """
    Gibt den Default-Extractor zurück (Singleton).

    Args:
        min_length: Minimum Content-Länge

    Returns:
        ContentExtractor Instanz
    """
    global _default_extractor

    if _default_extractor is None:
        _default_extractor = ContentExtractor(min_length=min_length)

    return _default_extractor


def extract_content(html: str, url: str = "", min_length: int = 100) -> Optional[str]:
    """
    Convenience-Funktion für schnelle Extraktion.

    Args:
        html: Rohes HTML
        url: Original-URL
        min_length: Minimum Content-Länge

    Returns:
        Extrahierter Content oder None
    """
    extractor = get_extractor(min_length)
    return extractor.extract(html, url)
