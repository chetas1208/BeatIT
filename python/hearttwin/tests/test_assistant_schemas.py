"""Schema validation tests for python/hearttwin/assistant/schemas.py.

Scoped to the new assistant package only per Wave 2 instructions — does not
exercise anything under shadow_trial_* or the live app.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from python.hearttwin.assistant.schemas import (
    AssistantArtifact,
    AssistantArtifactType,
    AssistantMessage,
    AssistantRequest,
    AssistantResponse,
    CanonicalProvenanceKind,
    ConversationContext,
    ExecutionClass,
    ProvenanceRef,
    ToolResult,
)
from python.hearttwin.safety import DISCLAIMER


def test_conversation_context_minimal() -> None:
    ctx = ConversationContext(conversation_id="c1", audience="general")
    assert ctx.patient_id is None
    assert ctx.audience == "general"


def test_conversation_context_rejects_bad_audience() -> None:
    with pytest.raises(ValidationError):
        ConversationContext(conversation_id="c1", audience="nurse")


def test_conversation_context_full() -> None:
    ctx = ConversationContext(
        conversation_id="c1",
        audience="physician",
        patient_id="p1",
        snapshot_id="s1",
        component_id="LV",
        product_space="twin",
        scenario_id="sc1",
        ensemble_id="e1",
        shadow_trial_id="st1",
        pair_id="pair1",
        target_metric="delta_sv",
        synthetic_status="synthetic",
    )
    assert ctx.component_id == "LV"


def test_assistant_message_defaults() -> None:
    msg = AssistantMessage(role="user", content="What is the current EF?")
    assert msg.tool_result_refs == []
    assert msg.created_at is not None


def test_assistant_message_rejects_bad_role() -> None:
    with pytest.raises(ValidationError):
        AssistantMessage(role="narrator", content="x")


def test_tool_result_valid() -> None:
    tr = ToolResult(
        tool_name="get_current_twin",
        execution_class=ExecutionClass.DIRECT_STATE_READ,
        canonical_payload={"ef_pct": 43.0},
        provenance=[ProvenanceRef(kind=CanonicalProvenanceKind.OBSERVED, source_id="obs-1")],
        safety_level="T0",
    )
    assert tr.safety_level == "T0"
    assert tr.provenance[0].kind == CanonicalProvenanceKind.OBSERVED


def test_tool_result_rejects_bad_safety_level() -> None:
    with pytest.raises(ValidationError):
        ToolResult(
            tool_name="run_shadow_trial",
            execution_class=ExecutionClass.SIMULATION,
            canonical_payload={},
            provenance=[],
            safety_level="T9",
        )


def test_provenance_ref_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        ProvenanceRef(kind=CanonicalProvenanceKind.DERIVED, confidence=1.5)


def test_assistant_artifact_defaults() -> None:
    artifact = AssistantArtifact(
        type=AssistantArtifactType.CARDIAC_COMPONENT_REPORT,
        title="LV Component Report",
        conversation_id="c1",
    )
    assert artifact.version == 1
    assert artifact.id
    assert artifact.source_tool_ids == []


def test_assistant_artifact_rejects_bad_type() -> None:
    with pytest.raises(ValidationError):
        AssistantArtifact(
            type="not_a_real_type",
            title="x",
            conversation_id="c1",
        )


def test_execution_class_has_all_required_members() -> None:
    expected = {
        "DIRECT_STATE_READ",
        "EVIDENCE_RETRIEVAL",
        "DETERMINISTIC_COMPUTATION",
        "SIMULATION",
        "ARTIFACT_GENERATION",
        "GENERATIVE_EXPLANATION",
        "COMPLEX_SYNTHESIS",
        "CLARIFICATION_REQUIRED",
        "INSUFFICIENT_EVIDENCE",
        "HUMAN_DECISION_REQUIRED",
        "UNSUPPORTED",
    }
    assert expected == {member.name for member in ExecutionClass}


def test_assistant_request_requires_matching_context_conversation_id() -> None:
    with pytest.raises(ValidationError):
        AssistantRequest(
            conversation_id="c1",
            message="hello",
            context=ConversationContext(conversation_id="c2", audience="general"),
        )


def test_assistant_request_valid() -> None:
    req = AssistantRequest(
        conversation_id="c1",
        message="What is the current EF?",
        context=ConversationContext(conversation_id="c1", audience="general"),
    )
    assert req.context.conversation_id == req.conversation_id


def test_assistant_response_always_carries_safety_disclaimer() -> None:
    resp = AssistantResponse(
        message="stub",
        execution_class=ExecutionClass.UNSUPPORTED,
    )
    assert resp.safety_disclaimer == DISCLAIMER
    assert resp.artifacts == []
    assert resp.trace.request_id
