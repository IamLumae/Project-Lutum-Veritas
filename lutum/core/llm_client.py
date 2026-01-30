"""
LLM Client Helpers
==================
Zentrale Helpers für API-Calls + Error Parsing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import requests

from lutum.core.api_config import get_api_base_url, get_api_headers, get_provider
from lutum.core.log_config import get_logger

logger = get_logger(__name__)


@dataclass
class LLMCallResult:
    content: Optional[str]
    error: Optional[str]
    raw: Optional[dict[str, Any]]


def _extract_error_message(payload: Any, status_code: Optional[int] = None) -> str:
    if isinstance(payload, dict):
        if "error" in payload:
            error = payload["error"]
            if isinstance(error, dict):
                message = error.get("message") or error.get("error") or str(error)
            else:
                message = str(error)
        else:
            message = payload.get("message") or payload.get("detail") or str(payload)
    else:
        message = str(payload)

    if status_code:
        return f"HTTP {status_code}: {message}"
    return message


def call_chat_completion(
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int,
    timeout: int,
    base_url: Optional[str] = None
) -> LLMCallResult:
    """
    Führt einen Chat-Completion Call durch (OpenAI-kompatibles Format).
    """
    url = base_url or get_api_base_url()

    try:
        response = requests.post(
            url,
            headers=get_api_headers(),
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens
            },
            timeout=timeout
        )

        if not response.ok:
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            error_message = _extract_error_message(payload, response.status_code)
            logger.error(f"LLM API error ({get_provider()}): {error_message}")
            return LLMCallResult(content=None, error=error_message, raw=None)

        result = response.json()
        if "choices" not in result:
            error_message = _extract_error_message(result, response.status_code)
            logger.error(f"LLM response missing choices: {error_message}")
            return LLMCallResult(content=None, error=error_message, raw=result)

        choice = result["choices"][0]
        message = choice.get("message", {})
        content = message.get("content")
        if content is None or not str(content).strip():
            finish_reason = choice.get("finish_reason", "unknown")
            refusal = message.get("refusal", "none")
            logger.warning(f"LLM returned empty content (finish_reason={finish_reason}, refusal={refusal}, model={model})")

        return LLMCallResult(content=content, error=None, raw=result)

    except requests.Timeout:
        error_message = "LLM timeout"
        logger.error(error_message)
        return LLMCallResult(content=None, error=error_message, raw=None)
    except Exception as e:
        error_message = f"LLM call failed: {e}"
        logger.error(error_message)
        return LLMCallResult(content=None, error=error_message, raw=None)
