"""Bedrock OpenAI-compatible Chat Completions HTTP adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from python.hearttwin.intelligence.bedrock.auth import authorization_headers, bedrock_openai_base_url
from python.hearttwin.intelligence.errors import ProviderResponseError, ProviderUnavailable
from python.hearttwin.intelligence.schemas import ChatMessage


def _messages(messages: Sequence[ChatMessage | Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") if isinstance(item, ChatMessage) else dict(item) for item in messages]


def build_chat_payload(
    *,
    model: str,
    messages: Sequence[ChatMessage | Mapping[str, Any]],
    max_tokens: int | None = None,
    temperature: float | None = None,
    response_format: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model, "messages": _messages(messages)}
    if response_format is not None:
        payload["response_format"] = dict(response_format)
    if max_tokens is not None:
        payload["max_completion_tokens"] = max_tokens
    if temperature is not None and float(temperature) == 1.0:
        payload["temperature"] = temperature
    if extra:
        payload.update(dict(extra))
    return payload


def parse_chat_content(body: Mapping[str, Any]) -> str:
    choices = body.get("choices") or []
    if not choices:
        raise ProviderResponseError("chat completion returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if not str(content).strip():
        raise ProviderResponseError("chat completion returned empty content")
    return str(content)


async def complete_via_chat_completions(
    *,
    model: str,
    messages: Sequence[ChatMessage | Mapping[str, Any]],
    max_tokens: int | None = None,
    temperature: float | None = None,
    response_format: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
    timeout_seconds: float = 45.0,
    client: httpx.AsyncClient | None = None,
) -> tuple[str, str]:
    """Return (content, resolved_model_id)."""
    base = bedrock_openai_base_url()
    if not base:
        raise ProviderUnavailable("Bedrock base URL is not configured")
    url = f"{base}/chat/completions"
    payload = build_chat_payload(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format=response_format,
        extra=extra,
    )
    owns = client is None
    http = client or httpx.AsyncClient(timeout=timeout_seconds)
    try:
        response = await http.post(url, headers=authorization_headers(), json=payload)
        if response.status_code >= 400:
            raise ProviderUnavailable(f"Bedrock chat HTTP {response.status_code}")
        body = response.json()
        content = parse_chat_content(body)
        resolved = str(body.get("model") or model)
        return content, resolved
    except httpx.HTTPError as exc:
        raise ProviderUnavailable(f"Bedrock chat request failed: {type(exc).__name__}") from exc
    finally:
        if owns:
            await http.aclose()
