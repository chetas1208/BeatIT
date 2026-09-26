"""Model client degrades cleanly when Bedrock inference is unavailable."""

from __future__ import annotations

import pytest

from python.hearttwin.assistant.model_client import ModelClientError, chat_completion


@pytest.mark.asyncio
async def test_all_keys_down_caller_degrades_to_deterministic_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_ENABLED", "false")

    async def try_model() -> dict:
        try:
            await chat_completion([{"role": "user", "content": "hi"}], "global.openai.gpt-5.6-luna")
        except ModelClientError:
            return {"source": "deterministic_fallback"}
        return {"source": "unexpected_success"}

    assert (await try_model())["source"] == "deterministic_fallback"
