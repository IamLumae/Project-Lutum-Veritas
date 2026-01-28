"""
API Config - Runtime Key Storage
================================
Backend setzt den API Key, Module lesen ihn.

Usage:
    # Backend (beim Request)
    from lutum.core.api_config import set_api_key
    set_api_key(request.api_key)

    # Module
    from lutum.core.api_config import get_api_key
    key = get_api_key()
"""

_OPENROUTER_API_KEY: str = ""


def set_api_key(key: str) -> None:
    """Setzt den API Key (vom Backend aufgerufen)."""
    global _OPENROUTER_API_KEY
    _OPENROUTER_API_KEY = key or ""


def get_api_key() -> str:
    """Holt den API Key."""
    return _OPENROUTER_API_KEY
