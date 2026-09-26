"""Genuine optional first-party OpenAI provider."""

from __future__ import annotations

import inspect
import os
from collections.abc import Mapping, Sequence
from typing import Any

from python.hearttwin.intelligence.base import IntelligenceProvider
from python.hearttwin.tools.model_config import chat_tuning
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


class OpenAIProvider(IntelligenceProvider):
    name = "openai"
    protocol = "openai-compatible"

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float = 45, max_retries: int = 2) -> None:
        if not api_key.strip() or not model.strip():
            raise ProviderConfigurationError("OpenAI provider requires API key and model")
        self.api_key = api_key
        self.default_model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

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
        client: Any | None = None
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ProviderUnavailable("OpenAI SDK is not installed") from exc
        effective_model = model or self.default_model
        kwargs: dict[str, Any] = {
            "model": effective_model,
            "messages": [item.model_dump(mode="json") if isinstance(item, ChatMessage) else dict(item) for item in messages],
        }
        if response_format is not None:
            kwargs["response_format"] = dict(response_format)
        if max_tokens is not None:
            kwargs.update(chat_tuning(effective_model, max_tokens, temperature))
        elif temperature is not None and float(temperature) == 1.0:
            kwargs["temperature"] = temperature
        if extra:
            kwargs.update(dict(extra))
        base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
        try:
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=base_url,
                timeout=timeout_seconds or self.timeout_seconds,
                max_retries=self.max_retries,
            )
            response = await client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            if not content.strip():
                raise ProviderResponseError("OpenAI returned empty model content")
            return ProviderResponse(
                content=content,
                # The SDK normally returns ``model``; the fallback keeps the
                # adapter compatible with lightweight test doubles and older
                # OpenAI-compatible response objects.
                model=getattr(response, "model", None) or kwargs["model"],
                provider=self.name,
            )
        except ProviderResponseError:
            raise
        except Exception as exc:
            raise ProviderUnavailable(f"OpenAI request failed: {type(exc).__name__}") from exc
        finally:
            if client is not None:
                close = getattr(client, "close", None)
                if close is not None:
                    result = close()
                    if inspect.isawaitable(result):
                        await result

    async def health(self) -> ProviderHealth:
        from python.hearttwin.intelligence.bedrock.health import bedrock_openai_reachable

        if os.environ.get("OPENAI_BASE_URL", "").find("bedrock-runtime") >= 0 or os.environ.get(
            "MODEL_BASE_URL", ""
        ).find("bedrock-runtime") >= 0:
            reachable = await bedrock_openai_reachable(timeout_seconds=min(self.timeout_seconds, 8.0))
            return ProviderHealth(
                enabled=True,
                protocol=self.protocol,
                reachable=reachable,
                model_configured=True,
                provider=self.name,
            )
        reachable = False
        try:
            from openai import AsyncOpenAI

            base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=base_url,
                timeout=min(self.timeout_seconds, 5),
                max_retries=0,
            )
            try:
                await client.models.list()
                reachable = True
            except Exception:  # noqa: BLE001 - health must never break the status route
                reachable = False
            finally:
                close = getattr(client, "close", None)
                if close is not None:
                    result = close()
                    if inspect.isawaitable(result):
                        await result
        except Exception:  # noqa: BLE001 - missing SDK/network reports unreachable
            reachable = False
        return ProviderHealth(enabled=True, protocol=self.protocol, reachable=reachable, model_configured=True, provider=self.name)


class BedrockOpenAIProvider(OpenAIProvider):
    name = "bedrock_openai"

    async def complete(
        self,
        messages,
        *,
        model: str | None = None,
        response_format: Mapping[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout_seconds: float | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> ProviderResponse:
        from python.hearttwin.intelligence.bedrock.chat_completions import complete_via_chat_completions
        from python.hearttwin.intelligence.bedrock.responses import (
            complete_via_responses,
            model_supports_responses_api,
        )

        effective_model = model or self.default_model
        protocol = os.environ.get("MODEL_API_PROTOCOL", "openai-compatible").strip().lower()
        timeout = timeout_seconds or self.timeout_seconds
        if protocol == "responses" and model_supports_responses_api(effective_model):
            content, resolved = await complete_via_responses(
                model=effective_model,
                messages=messages,
                max_tokens=max_tokens,
                extra=extra,
                timeout_seconds=timeout,
            )
            return ProviderResponse(content=content, model=resolved, provider=self.name)
        content, resolved = await complete_via_chat_completions(
            model=effective_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            extra=extra,
            timeout_seconds=timeout,
        )
        return ProviderResponse(content=content, model=resolved, provider=self.name)

    async def health(self) -> ProviderHealth:
        from python.hearttwin.intelligence.bedrock.health import bedrock_openai_reachable

        protocol = os.environ.get("MODEL_API_PROTOCOL", "openai-compatible").strip().lower()
        reachable = await bedrock_openai_reachable(timeout_seconds=min(self.timeout_seconds, 8.0))
        return ProviderHealth(
            enabled=True,
            protocol=protocol,
            reachable=reachable,
            model_configured=True,
            provider=self.name,
        )
