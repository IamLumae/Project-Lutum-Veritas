"""
Lutum Veritas - Configuration
=============================
Zentrale Konfiguration für alle Scraper.

ACHTUNG: Config ist immutable nach Erstellung.
         Für Änderungen neue Config erstellen.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import random


# User Agents - aktuelle Browser (2025/2026)
# ACHTUNG: Regelmäßig aktualisieren! Veraltete UAs werden erkannt.
DEFAULT_USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Firefox Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]

# Standard Accept Headers
# ACHTUNG: Müssen zu den User Agents passen (Chrome UA mit Firefox Headers = suspicious)
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


@dataclass(frozen=True)
class ScraperConfig:
    """
    Konfiguration für alle Scraper.

    Attributes:
        timeout: Request Timeout in Sekunden
        min_level: Minimale Eskalationsstufe (1-4)
        max_level: Maximale Eskalationsstufe (1-4)
        min_content_length: Minimum Zeichen für gültigen Content
        user_agents: Liste von User Agent Strings
        headers: Standard HTTP Headers
        locale: Browser Locale
        timezone: Browser Timezone
        retry_delay_min: Minimale Pause zwischen Retries (Sekunden)
        retry_delay_max: Maximale Pause zwischen Retries (Sekunden)

    ACHTUNG: frozen=True - Config kann nach Erstellung nicht geändert werden.
    """
    timeout: float = 30.0
    min_level: int = 1
    max_level: int = 4
    min_content_length: int = 100
    user_agents: tuple = field(default_factory=lambda: tuple(DEFAULT_USER_AGENTS))
    headers: dict = field(default_factory=lambda: DEFAULT_HEADERS.copy())
    locale: str = "de-DE"
    timezone: str = "Europe/Berlin"
    retry_delay_min: float = 1.0
    retry_delay_max: float = 2.0

    def get_random_user_agent(self) -> str:
        """Gibt einen zufälligen User Agent zurück."""
        return random.choice(self.user_agents)

    def get_headers(self, user_agent: Optional[str] = None) -> dict:
        """
        Gibt Headers mit zufälligem oder spezifischem User Agent zurück.

        Args:
            user_agent: Optional - spezifischer UA, sonst random

        Returns:
            Dict mit allen Headers inkl. User-Agent
        """
        headers = self.headers.copy()
        headers["User-Agent"] = user_agent or self.get_random_user_agent()
        return headers

    def get_retry_delay(self) -> float:
        """Gibt eine zufällige Retry-Pause zurück."""
        return random.uniform(self.retry_delay_min, self.retry_delay_max)


# Default Config - für schnellen Zugriff
# ACHTUNG: Nicht modifizieren! Bei Bedarf neue Config erstellen.
DEFAULT_CONFIG = ScraperConfig()
