"""Assistant System-2 chat client — delegates to the canonical intelligence provider.

All Bedrock/OpenAI inference flows through ``complete_text``; this module keeps
the Wave 6 ``ChatCompletionResult`` contract for the orchestrator.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from python.hearttwin.intelligence.errors import ProviderUnavailable
from python.hearttwin.intelligence.factory import complete_text, provider_available


class ModelClientError(Exception):
    """Base class for every failure this module raises."""


class NoHealthyKeyError(ModelClientError):
    """Intelligence provider disabled or unreachable."""


class ModelAPIError(ModelClientError):
    """Remote model call failed."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


@dataclass(frozen=True)
class ChatCompletionResult:
    text: str
    model: str
    latency_ms: float
    key_used: str  # role label for traces, e.g. "bedrock-fast"
    raw_usage: Optional[dict] = None


async def chat_completion(
    messages: list[dict],
    model: str,
    *,
    max_tokens: int = 300,
    temperature: float = 0.2,
    pool: object | None = None,  # noqa: ARG001 — legacy signature; ignored
    timeout_seconds: float = 45.0,
) -> ChatCompletionResult:
    if not provider_available():
        raise NoHealthyKeyError("Intelligence provider is disabled or not configured.")

    start = time.monotonic()
    try:
        text = await complete_text(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )
    except ProviderUnavailable as exc:
        raise ModelAPIError(str(exc)) from exc

    latency_ms = (time.monotonic() - start) * 1000
    return ChatCompletionResult(
        text=text,
        model=model,
        latency_ms=latency_ms,
        key_used="bedrock",
        raw_usage=None,
    )
