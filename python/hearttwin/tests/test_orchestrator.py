"""Tests for python/hearttwin/assistant/orchestrator.py (Wave 3).

Covers the wiring contract, not Wave 2's internals (those have their own
test suites): safety-first ordering, the clarification short-circuit, real
tool execution against a persisted ensemble, and honest "no answer"
responses when no tool matches. Reuses the same real-ensemble fixture
pattern as test_tool_registry.py (run the real deterministic ensemble
engine, persist it through the real store) rather than mocking canonical
data.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from python.hearttwin.assistant.orchestrator import handle_message
from python.hearttwin.assistant.schemas import AssistantRequest, ConversationContext, ExecutionClass
from python.hearttwin.assistant.tool_registry import get_tool_registry
from python.hearttwin.ensemble import (
    PARAMETER_BOUNDS,
    EnsembleDistributionRequest,
    EnsembleRequest,
    run_ensemble,
)
from python.hearttwin.schemas import CardiacTwinState, Hemodynamics, MeasuredValue, Measurements, ValueSource
from python.hearttwin.storage.ensemble_store import create_ensemble_store

_BASE_CONTEXT_KWARGS = dict(conversation_id="conv-1", audience="general")


def _context(**overrides) -> ConversationContext:
    return ConversationContext(**{**_BASE_CONTEXT_KWARGS, **overrides})


def _request(message: str, context: ConversationContext) -> AssistantRequest:
    return AssistantRequest(conversation_id=context.conversation_id, message=message, context=context)


def _measured(value: float, unit: str) -> MeasuredValue:
    return MeasuredValue(value=value, unit=unit, source=ValueSource.FILE_EXTRACTION, confidence=1.0)


def _state(baseline_vitals: dict) -> CardiacTwinState:
    return CardiacTwinState(
        case_id="orchestrator-fixture-case",
        created_at=datetime(2026, 1, 2, 3, 4, 5),  # noqa: DTZ001 - canonical naive fixture timestamp
        measurements=Measurements(
            heart_rate_bpm=_measured(baseline_vitals["heart_rate_bpm"], "bpm"),
            systolic_bp_mmhg=_measured(baseline_vitals["systolic_bp_mmhg"], "mmHg"),
            diastolic_bp_mmhg=_measured(baseline_vitals["diastolic_bp_mmhg"], "mmHg"),
            edv_ml=_measured(baseline_vitals["edv_ml"], "mL"),
            esv_ml=_measured(baseline_vitals["esv_ml"], "mL"),
        ),
        hemodynamics=Hemodynamics(
            preload_index=_measured(1.0, "index"),
            afterload_index=_measured(1.0, "index"),
            contractility_index=_measured(1.0, "index"),
            systemic_vascular_resistance_index=_measured(1.0, "index"),
        ),
    )


def _distribution(parameter_id: str) -> EnsembleDistributionRequest:
    defaults: dict[str, tuple[dict, dict]] = {
        "heart_rate_bpm": ({"mean": 72.0, "sd": 2.0}, {"min": 30.0, "max": 200.0}),
        "preload_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 1.5}),
        "afterload_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 2.0}),
        "contractility_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 1.5}),
        "systemic_vascular_resistance_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 2.0}),
    }
    parameters, bounds = defaults[parameter_id]
    return EnsembleDistributionRequest(
        parameter_id=parameter_id,
        family="normal",
        parameters=parameters,
        bounds=bounds,
        source="measurement",
        evidence_ids=["manual_baseline.json"],
        rationale="Orchestrator test fixture",
        version="test-v1",
    )


@pytest.fixture
def persisted_ensemble(baseline_vitals: dict, tmp_path, monkeypatch) -> dict:
    monkeypatch.setenv("BEATIT_ENSEMBLE_DB_PATH", str(tmp_path / "ensembles.sqlite3"))
    request = EnsembleRequest(
        origin_snapshot_id="snapshot-orchestrator",
        state=_state(baseline_vitals),
        seed=11,
        sample_count=6,
        distributions=[_distribution(parameter_id) for parameter_id in PARAMETER_BOUNDS],
        origin_quality="observed",
    )
    result = run_ensemble(request)
    create_ensemble_store().save(result["id"], result)
    return result


# ---------------------------------------------------------------------------
# (d) safety-first ordering: blocked before any tool runs
# ---------------------------------------------------------------------------


async def test_emergency_message_is_blocked_before_any_tool_runs() -> None:
    context = _context(ensemble_id="ens-should-never-be-used")
    request = _request(
        "I'm having crushing chest pain right now and I can't breathe, am I having a heart attack?",
        context,
    )

    response = await handle_message(request)

    assert response.execution_class == ExecutionClass.HUMAN_DECISION_REQUIRED
    assert response.trace.tools_invoked == []
    assert response.safety_disclaimer


async def test_treatment_seeking_message_is_blocked_before_any_tool_runs() -> None:
    context = _context()
    request = _request("Please prescribe medication and set a treatment plan for this patient.", context)

    response = await handle_message(request)

    assert response.execution_class == ExecutionClass.HUMAN_DECISION_REQUIRED
    assert response.trace.tools_invoked == []


# ---------------------------------------------------------------------------
# (a)/(b) clarification short-circuit
# ---------------------------------------------------------------------------


async def test_bare_referent_with_no_context_triggers_clarification() -> None:
    context = _context()
    request = _request("what about here?", context)

    response = await handle_message(request)

    assert response.execution_class == ExecutionClass.CLARIFICATION_REQUIRED
    assert response.trace.tools_invoked == []


async def test_bare_referent_with_component_id_does_not_trigger_clarification() -> None:
    context = _context(component_id="LV")
    request = _request("what about here?", context)

    response = await handle_message(request)

    assert response.execution_class != ExecutionClass.CLARIFICATION_REQUIRED


# ---------------------------------------------------------------------------
# (e) real tool execution with real data
# ---------------------------------------------------------------------------


async def test_ensemble_family_message_with_ensemble_id_executes_real_tool(persisted_ensemble: dict) -> None:
    # Deliberately avoids the word "ensemble" itself — Laya's fallback
    # tool-family router matches "ensemble" as an EXPERIMENT-bucket keyword
    # (checked before the UNCERTAINTY bucket), which would misroute this to a
    # category with no registered tools. "uncertainty" + a resolving
    # ensemble_id in context is what actually reaches the UNCERTAINTY family
    # and its real ensemble tools.
    get_tool_registry()  # ensure singleton initialized before the request
    context = _context(ensemble_id=persisted_ensemble["id"])
    request = _request("What is the uncertainty here?", context)

    response = await handle_message(request)

    assert response.trace.tools_invoked == ["get_ensemble"]
    assert response.execution_class == ExecutionClass.EVIDENCE_RETRIEVAL
    assert persisted_ensemble["id"] in response.message
    assert str(len(persisted_ensemble["samples"])) in response.message


async def test_ensemble_assumptions_keyword_selects_assumptions_tool(persisted_ensemble: dict) -> None:
    context = _context(ensemble_id=persisted_ensemble["id"])
    request = _request("What are the uncertain assumptions here?", context)

    response = await handle_message(request)

    assert response.trace.tools_invoked == ["get_ensemble_assumptions"]


# ---------------------------------------------------------------------------
# (f) honest "no answer" — never fabricated
# ---------------------------------------------------------------------------


async def test_no_matching_tool_family_returns_unsupported_not_fabricated() -> None:
    context = _context()
    # Fallback tool-family routing sends "current EF" style asks to TWIN,
    # a category with zero registered tools this wave.
    request = _request("What is the current EF?", context)

    response = await handle_message(request)

    assert response.execution_class == ExecutionClass.UNSUPPORTED
    assert response.trace.tools_invoked == []


async def test_missing_required_context_returns_insufficient_evidence_not_fabricated() -> None:
    # Routes to the UNCERTAINTY family (has tools) but no ensemble_id is set,
    # so no candidate tool's required args are satisfiable. Avoids "ensemble"
    # (would misroute to the tool-less EXPERIMENT bucket, see the test above)
    # and avoids bare referents ("this"/"that"/"it"/"here") so this exercises
    # the missing-context path rather than the clarification short-circuit.
    context = _context()
    request = _request("Explain the general uncertainty in the modeling assumptions.", context)

    response = await handle_message(request)

    assert response.execution_class == ExecutionClass.INSUFFICIENT_EVIDENCE
    assert response.trace.tools_invoked == []


async def test_response_always_carries_safety_disclaimer() -> None:
    context = _context()
    request = _request("What is the current EF?", context)

    response = await handle_message(request)

    assert response.safety_disclaimer
