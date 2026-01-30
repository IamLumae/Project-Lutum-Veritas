"""
LLM Client Helpers
==================
Zentrale Helpers für API-Calls + Error Parsing.
Provider-aware: Handles OpenAI, Anthropic, Google, HuggingFace formats.
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


def _build_request_body(
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int,
    provider: str
) -> dict:
    """
    Builds provider-specific request body.

    Anthropic: System prompt as top-level param, not in messages.
    Google: Lower temperature for consistent output.
    OpenAI/OpenRouter/HuggingFace: Standard format.
    """

    if provider == "anthropic":
        # Anthropic: Extract system prompt from messages, put it top-level
        system_prompt = None
        filtered_messages = []

        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content", "")
            else:
                filtered_messages.append(msg)

        body = {
            "model": model,
            "messages": filtered_messages,
            "max_tokens": max_tokens,
        }

        if system_prompt:
            body["system"] = system_prompt

        return body

    elif provider == "google":
        # Google Gemini: Use lower temperature for consistent output
        return {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,  # Lower temp for consistent structured output
        }

    else:
        # OpenAI / OpenRouter / HuggingFace: Standard format
        return {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,  # Consistent output
        }


def _parse_response(result: dict, provider: str) -> Optional[str]:
    """
    Parses provider-specific response format.

    Anthropic: content[0].text
    Others: choices[0].message.content
    """

    if provider == "anthropic":
        # Anthropic format: {"content": [{"type": "text", "text": "..."}]}
        content_blocks = result.get("content", [])
        if content_blocks and len(content_blocks) > 0:
            first_block = content_blocks[0]
            if isinstance(first_block, dict):
                return first_block.get("text")
            return str(first_block)
        return None

    else:
        # OpenAI format: {"choices": [{"message": {"content": "..."}}]}
        if "choices" not in result:
            return None
        choice = result["choices"][0]
        message = choice.get("message", {})
        return message.get("content")


def _get_finish_reason(result: dict, provider: str) -> str:
    """Gets finish reason from provider-specific response."""

    if provider == "anthropic":
        return result.get("stop_reason", "unknown")
    else:
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0].get("finish_reason", "unknown")
        return "unknown"


def call_chat_completion(
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int,
    timeout: int,
    base_url: Optional[str] = None
) -> LLMCallResult:
    """
    Führt einen Chat-Completion Call durch.
    Provider-aware: Handles different API formats automatically.
    """
    url = base_url or get_api_base_url()
    provider = get_provider()

    # Build provider-specific request body
    request_body = _build_request_body(messages, model, max_tokens, provider)

    logger.debug(f"[LLM] Provider: {provider}, Model: {model}, max_tokens: {max_tokens}")

    try:
        response = requests.post(
            url,
            headers=get_api_headers(),
            json=request_body,
            timeout=timeout
        )

        if not response.ok:
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            error_message = _extract_error_message(payload, response.status_code)
            logger.error(f"LLM API error ({provider}): {error_message}")
            return LLMCallResult(content=None, error=error_message, raw=None)

        result = response.json()

        # Parse response using provider-specific logic
        content = _parse_response(result, provider)
        finish_reason = _get_finish_reason(result, provider)

        # ALWAYS log finish_reason to debug early stops
        logger.info(f"[LLM] provider={provider}, finish_reason={finish_reason}, content_len={len(content) if content else 0}, model={model}")

        if content is None or not str(content).strip():
            logger.warning(f"LLM returned empty content (provider={provider}, finish_reason={finish_reason}, model={model})")

        return LLMCallResult(content=content, error=None, raw=result)

    except requests.Timeout:
        error_message = "LLM timeout"
        logger.error(error_message)
        return LLMCallResult(content=None, error=error_message, raw=None)
    except Exception as e:
        error_message = f"LLM call failed: {e}"
        logger.error(error_message)
        return LLMCallResult(content=None, error=error_message, raw=None)
