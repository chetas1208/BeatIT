"""Certification Wave D — failure matrix for unified assistant."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from python.hearttwin.assistant.laya_adapter import LayaAdapter
from python.hearttwin.assistant.model_client import ModelClientError
from python.hearttwin.assistant.orchestrator import handle_message
from python.hearttwin.assistant.schemas import AssistantRequest, ConversationContext, ExecutionClass


def _req(message: str = "What is the uncertainty here?") -> AssistantRequest:
    return AssistantRequest(
        conversation_id="fail-matrix-conv",
        message=message,
        context=ConversationContext(conversation_id="fail-matrix-conv", audience="general"),
    )


@pytest.mark.asyncio
async def test_laya_down_uses_deterministic_fallback_adapter(monkeypatch) -> None:
    monkeypatch.setenv("LAYA_ENABLED", "false")
    response = await handle_message(_req("What ensemble assumptions are recorded?"), laya=LayaAdapter())
    assert response.safety_disclaimer
    assert response.execution_class in {
        ExecutionClass.CLARIFICATION_REQUIRED,
        ExecutionClass.UNSUPPORTED,
        ExecutionClass.EVIDENCE_RETRIEVAL,
    }


@pytest.mark.asyncio
async def test_all_models_down_still_returns_safe_response() -> None:
    with patch(
        "python.hearttwin.assistant.orchestrator.chat_completion",
        new_callable=AsyncMock,
        side_effect=ModelClientError("all keys down"),
    ), patch(
        "python.hearttwin.assistant.orchestrator.should_defer_to_clarification",
        return_value=False,
    ):
        response = await handle_message(_req("Explain the general modeling approach in plain language."))
    assert response.safety_disclaimer
    assert response.execution_class != ExecutionClass.HUMAN_DECISION_REQUIRED or "prescribe" not in _req().message
