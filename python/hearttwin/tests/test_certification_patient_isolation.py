"""Certification Wave D3 — context isolation (ensemble scope)."""

from __future__ import annotations

from datetime import datetime

import pytest

from python.hearttwin.assistant.orchestrator import handle_message
from python.hearttwin.assistant.schemas import AssistantRequest, ConversationContext
from python.hearttwin.ensemble import (
    PARAMETER_BOUNDS,
    EnsembleDistributionRequest,
    EnsembleRequest,
    run_ensemble,
)
from python.hearttwin.schemas import CardiacTwinState, Hemodynamics, MeasuredValue, Measurements, ValueSource
from python.hearttwin.storage.ensemble_store import create_ensemble_store


def _measured(value: float, unit: str) -> MeasuredValue:
    return MeasuredValue(value=value, unit=unit, source=ValueSource.FILE_EXTRACTION, confidence=1.0)


def _state(case_id: str, baseline_vitals: dict) -> CardiacTwinState:
    return CardiacTwinState(
        case_id=case_id,
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
        evidence_ids=["isolation_fixture.json"],
        rationale="Isolation certification fixture",
        version="test-v1",
    )


@pytest.fixture
def two_ensembles(baseline_vitals: dict, tmp_path, monkeypatch) -> tuple[dict, dict]:
    monkeypatch.setenv("BEATIT_ENSEMBLE_DB_PATH", str(tmp_path / "ensembles.sqlite3"))
    store = create_ensemble_store()
    results = []
    for seed in (11, 22):
        req = EnsembleRequest(
            origin_snapshot_id=f"snapshot-{seed}",
            state=_state(f"case-{seed}", baseline_vitals),
            seed=seed,
            sample_count=4,
            distributions=[_distribution(pid) for pid in PARAMETER_BOUNDS],
            origin_quality="observed",
        )
        result = run_ensemble(req)
        store.save(result["id"], result)
        results.append(result)
    return results[0], results[1]


@pytest.mark.asyncio
async def test_ensemble_b_response_does_not_reference_ensemble_a(two_ensembles: tuple[dict, dict]) -> None:
    ens_a, ens_b = two_ensembles
    conv = "cert-conv-isolation"

    await handle_message(
        AssistantRequest(
            conversation_id=conv,
            message="What is the uncertainty in the modeling assumptions?",
            context=ConversationContext(
                conversation_id=conv,
                audience="general",
                ensemble_id=ens_a["id"],
            ),
        ),
    )

    response_b = await handle_message(
        AssistantRequest(
            conversation_id=conv,
            message="What is the uncertainty in the modeling assumptions?",
            context=ConversationContext(
                conversation_id=conv,
                audience="general",
                ensemble_id=ens_b["id"],
            ),
        ),
    )

    assert ens_a["id"] not in response_b.message
    assert response_b.trace.tools_invoked == ["get_ensemble_assumptions"]
