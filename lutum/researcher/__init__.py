"""
Lutum Veritas - Researcher Module
=================================
Research Pipeline: Overview → Search → Scrape → Analyze → Plan

Architektur:
- Jeder Step = EINE Datei
- Fertige Steps werden NIE wieder angefasst
- pipeline.py orchestriert alles dynamisch
"""

from lutum.researcher.pipeline import run_pipeline, format_pipeline_response

# Einzelne Steps für direkten Zugriff (optional)
from lutum.researcher.overview import get_overview_queries
from lutum.researcher.search import get_initial_data
from lutum.researcher.scraper import scrape_urls, format_scraped_for_llm

__all__ = [
    # Pipeline (Hauptinterface)
    "run_pipeline",
    "format_pipeline_response",
    # Einzelne Steps
    "get_overview_queries",
    "get_initial_data",
    "scrape_urls",
    "format_scraped_for_llm",
]
