"""Full product conversation path (backend): twin → shadow → missing piece."""

from __future__ import annotations

from datetime import datetime

import pytest

from python.hearttwin.assistant.orchestrator import handle_message
from python.hearttwin.assistant.schemas import AssistantRequest, ConversationContext, ExecutionClass
from python.hearttwin.ensemble import PARAMETER_BOUNDS, EnsembleDistributionRequest, EnsembleRequest, run_ensemble
from python.hearttwin.schemas import CardiacTwinState, Hemodynamics, MeasuredValue, Measurements, ValueSource
from python.hearttwin.storage.ensemble_store import create_ensemble_store
from python.hearttwin.storage.missing_piece_store import SQLiteMissingPieceStore
from python.hearttwin.storage.shadow_trial_store import SQLiteShadowTrialStore


def _measured(value: float, unit: str) -> MeasuredValue:
    return MeasuredValue(value=value, unit=unit, source=ValueSource.FILE_EXTRACTION, confidence=1.0)


def _state(baseline_vitals: dict) -> CardiacTwinState:
    return CardiacTwinState(
        case_id="full-e2e-case",
        created_at=datetime(2026, 1, 2, 3, 4, 5),  # noqa: DTZ001
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
        evidence_ids=["full_e2e.json"],
        rationale="full product e2e",
        version="test-v1",
    )


@pytest.fixture
def ensemble_id(baseline_vitals: dict, tmp_path, monkeypatch) -> str:
    monkeypatch.setenv("BEATIT_ENSEMBLE_DB_PATH", str(tmp_path / "ensemble.sqlite3"))
    monkeypatch.setenv("BEATIT_SHADOW_TRIAL_DB_PATH", str(tmp_path / "shadow.sqlite3"))
    monkeypatch.setenv("BEATIT_MISSING_PIECE_DB_PATH", str(tmp_path / "missing.sqlite3"))
    monkeypatch.setattr(
        "python.hearttwin.assistant.simulation_tools.create_shadow_trial_store",
        lambda: SQLiteShadowTrialStore(tmp_path / "shadow.sqlite3"),
    )
    monkeypatch.setattr(
        "python.hearttwin.assistant.simulation_tools.create_missing_piece_store",
        lambda: SQLiteMissingPieceStore(tmp_path / "missing.sqlite3"),
    )
    import python.hearttwin.assistant.tool_registry as tr

    tr._REGISTRY = None  # type: ignore[attr-defined]
    result = run_ensemble(
        EnsembleRequest(
            origin_snapshot_id="snap-full",
            state=_state(baseline_vitals),
            seed=3,
            sample_count=4,
            distributions=[_distribution(pid) for pid in PARAMETER_BOUNDS],
            origin_quality="observed",
        )
    )
    create_ensemble_store().save(result["id"], result)
    return result["id"]


@pytest.mark.asyncio
async def test_conversation_b_shadow_then_missing_piece(ensemble_id: str) -> None:
    conv = "full-product-conv-b"
    ctx = ConversationContext(conversation_id=conv, audience="physician", ensemble_id=ensemble_id)

    r1 = await handle_message(
        AssistantRequest(conversation_id=conv, message="Run a shadow trial on this ensemble.", context=ctx),
    )
    assert "get_shadow_trial" not in r1.trace.tools_invoked
    assert "run_shadow_trial" in r1.trace.tools_invoked

    r2 = await handle_message(
        AssistantRequest(
            conversation_id=conv,
            message="What would reduce uncertainty in stroke volume?",
            context=ConversationContext(
                conversation_id=conv,
                audience="physician",
                ensemble_id=ensemble_id,
                target_metric="stroke_volume_ml",
            ),
        ),
    )
    assert r2.safety_disclaimer
    assert r2.execution_class in {
        ExecutionClass.DETERMINISTIC_COMPUTATION,
        ExecutionClass.EVIDENCE_RETRIEVAL,
        ExecutionClass.CLARIFICATION_REQUIRED,
    }
