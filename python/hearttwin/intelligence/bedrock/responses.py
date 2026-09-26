"""Bedrock OpenAI-compatible Responses API adapter (when supported for the model)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from python.hearttwin.intelligence.bedrock.auth import authorization_headers, bedrock_openai_base_url
from python.hearttwin.intelligence.errors import ProviderResponseError, ProviderUnavailable
from python.hearttwin.intelligence.schemas import ChatMessage


def model_supports_responses_api(model_id: str) -> bool:
    """GPT-OSS and safeguard models stay on chat completions per AWS compatibility notes."""
    lower = model_id.lower()
    if "gpt-oss" in lower or "safeguard" in lower:
        return False
    return True


def _input_from_messages(messages: Sequence[ChatMessage | Mapping[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in messages:
        data = item.model_dump(mode="json") if isinstance(item, ChatMessage) else dict(item)
        role = str(data.get("role", "user"))
        content = data.get("content", "")
        items.append({"role": role, "content": content})
    return items


def build_responses_payload(
    *,
    model: str,
    messages: Sequence[ChatMessage | Mapping[str, Any]],
    max_tokens: int | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model, "input": _input_from_messages(messages)}
    if max_tokens is not None:
        payload["max_output_tokens"] = max_tokens
    if extra:
        payload.update(dict(extra))
    return payload


def parse_responses_content(body: Mapping[str, Any]) -> str:
    if body.get("output_text"):
        text = str(body["output_text"]).strip()
        if text:
            return text
    output = body.get("output") or []
    for block in output:
        if not isinstance(block, Mapping):
            continue
        if block.get("type") == "message":
            for part in block.get("content") or []:
                if isinstance(part, Mapping) and part.get("type") in {"output_text", "text"}:
                    text = str(part.get("text") or "").strip()
                    if text:
                        return text
    raise ProviderResponseError("responses API returned no textual output")


async def complete_via_responses(
    *,
    model: str,
    messages: Sequence[ChatMessage | Mapping[str, Any]],
    max_tokens: int | None = None,
    extra: Mapping[str, Any] | None = None,
    timeout_seconds: float = 45.0,
    client: httpx.AsyncClient | None = None,
) -> tuple[str, str]:
    base = bedrock_openai_base_url()
    if not base:
        raise ProviderUnavailable("Bedrock base URL is not configured")
    url = f"{base}/responses"
    payload = build_responses_payload(model=model, messages=messages, max_tokens=max_tokens, extra=extra)
    owns = client is None
    http = client or httpx.AsyncClient(timeout=timeout_seconds)
    try:
        response = await http.post(url, headers=authorization_headers(), json=payload)
        if response.status_code >= 400:
            raise ProviderUnavailable(f"Bedrock responses HTTP {response.status_code}")
        body = response.json()
        content = parse_responses_content(body)
        resolved = str(body.get("model") or model)
        return content, resolved
    except httpx.HTTPError as exc:
        raise ProviderUnavailable(f"Bedrock responses request failed: {type(exc).__name__}") from exc
    finally:
        if owns:
            await http.aclose()
