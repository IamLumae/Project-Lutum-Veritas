"""
Lutum Veritas - Core Module
===========================
Config, Logging, Exceptions.
"""

from lutum.core.config import ScraperConfig, DEFAULT_CONFIG
from lutum.core.log_config import get_logger
from lutum.core.exceptions import ExtractionError, DependencyError

__all__ = [
    "ScraperConfig",
    "DEFAULT_CONFIG",
    "get_logger",
    "ExtractionError",
    "DependencyError",
]
