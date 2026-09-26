"""Wave 7 — required multi-turn conversation scenarios (backend orchestrator).

These exercise the unified pipeline without the Next.js panel. They map to
the campaign's Conversations A–D at the orchestration layer; full UI E2E
remains a separate frontend check.
"""

from __future__ import annotations

import pytest

from python.hearttwin.assistant.orchestrator import handle_message
from python.hearttwin.assistant.schemas import AssistantRequest, ConversationContext, ExecutionClass


def _ctx(**kwargs: object) -> ConversationContext:
    base = {"conversation_id": "wave7-conv", "audience": "general"}
    base.update(kwargs)
    return ConversationContext(**base)  # type: ignore[arg-type]


def _turn(message: str, context: ConversationContext) -> AssistantRequest:
    return AssistantRequest(
        conversation_id=context.conversation_id,
        message=message,
        context=context,
    )


@pytest.mark.asyncio
async def test_conversation_a_component_context_without_restatement() -> None:
    """LV highlight → patient-specific → provenance, one conversation id."""
    context = _ctx(component_id="LV")
    r1 = await handle_message(_turn("What does the highlighted part do?", context))
    assert r1.safety_disclaimer
    r2 = await handle_message(_turn("What does it look like in this patient?", context))
    assert r2.safety_disclaimer
    r3 = await handle_message(_turn("Where did that value come from?", context))
    assert r3.safety_disclaimer
    assert context.component_id == "LV"


@pytest.mark.asyncio
async def test_conversation_c_refuses_autonomous_treatment_plan() -> None:
    context = _ctx(audience="physician")
    response = await handle_message(
        _turn("Which treatment should I give?", context),
    )
    assert response.execution_class == ExecutionClass.HUMAN_DECISION_REQUIRED
    assert response.trace.tools_invoked == []


@pytest.mark.asyncio
async def test_conversation_d_observed_vs_simulated_is_not_fabricated() -> None:
    context = _ctx()
    response = await handle_message(
        _turn("What is directly observed and what is simulated?", context),
    )
    assert response.trace.tools_invoked == []
    assert response.execution_class in {
        ExecutionClass.CLARIFICATION_REQUIRED,
        ExecutionClass.EVIDENCE_RETRIEVAL,
        ExecutionClass.INSUFFICIENT_EVIDENCE,
    }
