"""Tests for assistant model_client → canonical intelligence provider."""

from __future__ import annotations

import pytest

from python.hearttwin.assistant.model_client import (
    ChatCompletionResult,
    ModelAPIError,
    NoHealthyKeyError,
    chat_completion,
)
from python.hearttwin.intelligence.errors import ProviderUnavailable


@pytest.mark.asyncio
async def test_raises_when_provider_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_ENABLED", "false")
    monkeypatch.setenv("INTELLIGENCE_PROVIDER", "disabled")
    with pytest.raises(NoHealthyKeyError):
        await chat_completion([{"role": "user", "content": "hi"}], "global.openai.gpt-5.6-luna")


@pytest.mark.asyncio
async def test_delegates_to_complete_text(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_complete_text(messages, **kwargs):  # type: ignore[no-untyped-def]
        assert messages[0]["content"] == "hi"
        assert kwargs.get("model") == "global.openai.gpt-5.6-luna"
        return "hello"

    monkeypatch.setattr("python.hearttwin.assistant.model_client.provider_available", lambda: True)
    monkeypatch.setattr("python.hearttwin.assistant.model_client.complete_text", fake_complete_text)
    result = await chat_completion([{"role": "user", "content": "hi"}], "global.openai.gpt-5.6-luna")
    assert isinstance(result, ChatCompletionResult)
    assert result.text == "hello"
    assert result.key_used == "bedrock"


@pytest.mark.asyncio
async def test_maps_provider_unavailable_to_model_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise ProviderUnavailable("HTTPStatusError")

    monkeypatch.setattr("python.hearttwin.assistant.model_client.provider_available", lambda: True)
    monkeypatch.setattr("python.hearttwin.assistant.model_client.complete_text", boom)
    with pytest.raises(ModelAPIError):
        await chat_completion([{"role": "user", "content": "hi"}], "global.openai.gpt-5.6-luna")
