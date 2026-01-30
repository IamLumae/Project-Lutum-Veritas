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
_PROVIDER: str = "openrouter"
_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"
_WORK_MODEL: str = "google/gemini-2.5-flash-lite-preview-09-2025"
_FINAL_MODEL: str = "qwen/qwen3-vl-235b-a22b-instruct"

PROVIDER_CONFIG = {
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1/chat/completions",
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1/messages",
    },
    "google": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    },
    "huggingface": {
        "name": "HuggingFace",
        "base_url": "https://api-inference.huggingface.co/v1/chat/completions",
    },
}


def set_api_key(key: str) -> None:
    """Setzt den API Key (vom Backend aufgerufen)."""
    global _OPENROUTER_API_KEY
    _OPENROUTER_API_KEY = key or ""


def set_api_config(
    key: str,
    provider: str = "openrouter",
    work_model: str | None = None,
    final_model: str | None = None,
    base_url: str | None = None
) -> None:
    """Setzt API Konfiguration (Provider, Models, Base URL)."""
    global _OPENROUTER_API_KEY, _PROVIDER, _BASE_URL, _WORK_MODEL, _FINAL_MODEL

    _OPENROUTER_API_KEY = key or ""
    _PROVIDER = provider or "openrouter"

    config = PROVIDER_CONFIG.get(_PROVIDER)
    if base_url:
        _BASE_URL = base_url
    elif config:
        _BASE_URL = config["base_url"]

    if work_model:
        _WORK_MODEL = work_model
    if final_model:
        _FINAL_MODEL = final_model


def get_api_key() -> str:
    """Holt den API Key."""
    return _OPENROUTER_API_KEY


def get_provider() -> str:
    """Aktuellen Provider holen."""
    return _PROVIDER


def get_api_base_url() -> str:
    """Aktuelle Base URL holen."""
    return _BASE_URL


def get_work_model() -> str:
    """Aktuelles Work Model holen."""
    return _WORK_MODEL


def get_final_model() -> str:
    """Aktuelles Final Model holen."""
    return _FINAL_MODEL


def get_api_headers() -> dict:
    """Standard Headers für API-Calls basierend auf Provider."""
    headers = {
        "Content-Type": "application/json",
    }

    if _OPENROUTER_API_KEY:
        headers["Authorization"] = f"Bearer {_OPENROUTER_API_KEY}"

    if _PROVIDER == "google" and _OPENROUTER_API_KEY:
        headers["x-goog-api-key"] = _OPENROUTER_API_KEY

    if _PROVIDER == "anthropic" and _OPENROUTER_API_KEY:
        headers["x-api-key"] = _OPENROUTER_API_KEY
        headers.setdefault("anthropic-version", "2023-06-01")

    return headers
