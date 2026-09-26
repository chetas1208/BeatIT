"""Tests for assistant Shadow Trial + Missing Piece tools."""

from __future__ import annotations

import pytest

from python.hearttwin.assistant.simulation_tools import register_simulation_tools
from python.hearttwin.assistant.tool_registry import ToolRegistry
from python.hearttwin.ensemble import PARAMETER_BOUNDS, EnsembleDistributionRequest, EnsembleRequest, run_ensemble
from python.hearttwin.schemas import CardiacTwinState, Hemodynamics, MeasuredValue, Measurements, ValueSource
from python.hearttwin.storage.ensemble_store import create_ensemble_store
from python.hearttwin.storage.missing_piece_store import SQLiteMissingPieceStore
from python.hearttwin.storage.shadow_trial_store import SQLiteShadowTrialStore
from datetime import datetime


def _measured(value: float, unit: str) -> MeasuredValue:
    return MeasuredValue(value=value, unit=unit, source=ValueSource.FILE_EXTRACTION, confidence=1.0)


def _state(baseline_vitals: dict) -> CardiacTwinState:
    return CardiacTwinState(
        case_id="sim-tools-case",
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
        evidence_ids=["sim_tools.json"],
        rationale="simulation tools fixture",
        version="test-v1",
    )


@pytest.fixture
def sim_registry(baseline_vitals: dict, tmp_path, monkeypatch) -> ToolRegistry:
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
    ensemble = run_ensemble(
        EnsembleRequest(
            origin_snapshot_id="snap-sim",
            state=_state(baseline_vitals),
            seed=9,
            sample_count=4,
            distributions=[_distribution(pid) for pid in PARAMETER_BOUNDS],
            origin_quality="observed",
        )
    )
    create_ensemble_store().save(ensemble["id"], ensemble)
    registry = ToolRegistry()
    register_simulation_tools(registry)
    registry._fixture_ensemble_id = ensemble["id"]  # type: ignore[attr-defined]
    return registry


@pytest.mark.asyncio
async def test_run_shadow_trial_and_get_roundtrip(sim_registry: ToolRegistry) -> None:
    eid = sim_registry._fixture_ensemble_id  # type: ignore[attr-defined]
    run = await sim_registry.execute("run_shadow_trial", baseline_ensemble_id=eid)
    trial_id = run.canonical_payload["shadow_trial_id"]
    got = await sim_registry.execute("get_shadow_trial", shadow_trial_id=trial_id)
    assert got.canonical_payload["id"] == trial_id
    assert got.canonical_payload["valid_pairs"] >= 1


@pytest.mark.asyncio
async def test_run_missing_piece_and_get_roundtrip(sim_registry: ToolRegistry) -> None:
    eid = sim_registry._fixture_ensemble_id  # type: ignore[attr-defined]
    run = await sim_registry.execute(
        "run_missing_piece",
        baseline_ensemble_id=eid,
        target_metric="stroke_volume_ml",
    )
    mp_id = run.canonical_payload["missing_piece_id"]
    got = await sim_registry.execute("get_missing_piece", missing_piece_id=mp_id)
    assert got.canonical_payload["target_metric"] == "stroke_volume_ml"
