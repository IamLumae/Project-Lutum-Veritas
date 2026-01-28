"""
LUTUM VERITAS - Wahrheit aus dem Schlamm
========================================
Camoufox Web Scraper (John Wick - 0% Detection) + LLM Analyzer.

Usage:
    from lutum.scrapers import camoufox_scrape_raw
    text = camoufox_scrape_raw("https://example.com")

    from lutum.analyzer import analyze_url
    result = analyze_url("https://example.com", user_query="keypoints")
"""

__version__ = "1.0.0"

from lutum.scrapers import CamoufoxScraper, camoufox_scrape_raw
from lutum.analyzer import analyze_url

__all__ = [
    "__version__",
    "CamoufoxScraper",
    "camoufox_scrape_raw",
    "analyze_url",
]
