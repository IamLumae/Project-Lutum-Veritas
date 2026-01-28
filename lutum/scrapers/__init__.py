"""
Lutum Veritas - Scrapers Module
===============================
Camoufox Scraper (John Wick) - 0% Detection, Maximum Stealth.

Usage:
    from lutum.scrapers import CamoufoxScraper
    from lutum.scrapers.camoufox_scraper import camoufox_scrape_raw
"""

from lutum.scrapers.base import BaseScraper
from lutum.scrapers.camoufox_scraper import CamoufoxScraper, camoufox_scrape, camoufox_scrape_raw

__all__ = [
    "BaseScraper",
    "CamoufoxScraper",
    "camoufox_scrape",
    "camoufox_scrape_raw",
]
