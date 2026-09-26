"""OpenAI-compatible HTTP provider with no vendor-specific assumptions."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from python.hearttwin.intelligence.base import IntelligenceProvider
from python.hearttwin.intelligence.errors import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderUnavailable,
)
from python.hearttwin.intelligence.schemas import (
    ChatMessage,
    ProviderHealth,
    ProviderResponse,
)


def _messages(messages: Sequence[ChatMessage | Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") if isinstance(item, ChatMessage) else dict(item) for item in messages]


class GenericOpenAICompatibleProvider(IntelligenceProvider):
    name = "generic"
    protocol = "openai-compatible"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 45,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip() or not base_url.strip() or not model.strip():
            raise ProviderConfigurationError("generic provider requires API key, base URL, and model")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self._client = client

    def _endpoint(self, suffix: str) -> str:
        return f"{self.base_url}/{suffix.lstrip('/')}"

    async def complete(
        self,
        messages: Sequence[ChatMessage | Mapping[str, Any]],
        *,
        model: str | None = None,
        response_format: Mapping[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout_seconds: float | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> ProviderResponse:
        payload: dict[str, Any] = {"model": model or self.default_model, "messages": _messages(messages)}
        if response_format is not None:
            payload["response_format"] = dict(response_format)
        if max_tokens is not None:
            payload["max_completion_tokens"] = max_tokens
        if temperature is not None:
            if float(temperature) == 1.0:
                payload["temperature"] = temperature
        if extra:
            payload.update(dict(extra))
            if "max_completion_tokens" in payload and "max_tokens" in payload:
                payload.pop("max_tokens", None)
            elif "max_completion_tokens" not in payload and "max_tokens" in payload:
                payload["max_completion_tokens"] = payload.pop("max_tokens")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=timeout_seconds or self.timeout_seconds)
        try:
            last_error: Exception | None = None
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(self._endpoint("chat/completions"), headers=headers, json=payload)
                    response.raise_for_status()
                    body = response.json()
                    content = body["choices"][0]["message"]["content"]
                    if not isinstance(content, str) or not content.strip():
                        raise ProviderResponseError("provider returned empty model content")
                    return ProviderResponse(
                        content=content,
                        model=str(body.get("model", payload["model"])),
                        provider=self.name,
                        request_id=response.headers.get("x-request-id"),
                        raw=body if isinstance(body, dict) else None,
                    )
                except (httpx.HTTPError, KeyError, TypeError, ValueError, ProviderResponseError) as exc:
                    last_error = exc
                    if attempt < self.max_retries:
                        await asyncio.sleep(min(0.25 * (2**attempt), 2.0))
            raise ProviderUnavailable(f"generic model request failed: {type(last_error).__name__}") from last_error
        finally:
            if owns_client:
                await client.aclose()

    async def health(self) -> ProviderHealth:
        client = self._client or httpx.AsyncClient(timeout=min(self.timeout_seconds, 5))
        owns_client = self._client is None
        try:
            try:
                response = await client.get(self._endpoint("models"), headers={"Authorization": f"Bearer {self.api_key}"})
                reachable = response.status_code < 500
            except httpx.HTTPError:
                reachable = False
            return ProviderHealth(enabled=True, protocol=self.protocol, reachable=reachable, model_configured=True, provider=self.name)
        finally:
            if owns_client:
                await client.aclose()
