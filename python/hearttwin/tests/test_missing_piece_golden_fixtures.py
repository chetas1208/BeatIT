"""Golden fixtures for M8 uncertainty-impact and engine invariants."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from python.hearttwin.ensemble import run_ensemble
from python.hearttwin.missing_piece.engine import run_missing_piece, run_missing_piece_shadow_effect
from python.hearttwin.missing_piece.impact import build_uncertainty_impacts
from python.hearttwin.missing_piece.contracts import ParameterSensitivity, SensitivityProvenance
from python.hearttwin.shadow_trial_engine import ScenarioDefinition, ScenarioParameterChange
from python.hearttwin.tests.test_ensemble import _request, _state

_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "golden" / "missing_piece"


def _load(name: str) -> dict:
    return json.loads((_FIXTURE_DIR / f"{name}.json").read_text())


def _sens(
    parameter_id: str,
    sensitivity: float,
    *,
    normalized: float | None,
    metric_id: str = "stroke_volume_ml",
) -> ParameterSensitivity:
    return ParameterSensitivity(
        parameter_id=parameter_id,
        metric_id=metric_id,
        method="finite_difference",
        sensitivity=sensitivity,
        baseline_value=1.0,
        perturbation=0.05,
        normalized_sensitivity=normalized,
        provenance=SensitivityProvenance(sample_count=2),
    )


def test_golden_manifest_lists_all_cases() -> None:
    manifest = _load("manifest")
    cases = set(manifest["cases"])
    on_disk = {path.stem for path in _FIXTURE_DIR.glob("*.json")} - {"manifest"}
    assert cases == on_disk


def test_single_dominant_parameter_fixture() -> None:
    expected = _load("single-dominant-parameter")
    impacts = build_uncertainty_impacts(
        [
            _sens("contractility_index", 10.0, normalized=0.8),
            _sens("heart_rate_bpm", 1.0, normalized=0.05),
        ],
        {
            "contractility_index": {"uncertainty_magnitude": 0.5},
            "heart_rate_bpm": {"uncertainty_magnitude": 0.1},
        },
        metric_id="stroke_volume_ml",
    )
    assert impacts[0].parameter_id == expected["expected_top_driver"]


def test_well_constrained_sensitive_beats_high_sensitivity_low_uncertainty() -> None:
    expected = _load("well-constrained-sensitive")
    impacts = build_uncertainty_impacts(
        [
            _sens("contractility_index", 5.0, normalized=1.0),
            _sens("preload_index", 5.0, normalized=0.5),
        ],
        {
            "contractility_index": {"uncertainty_magnitude": 0.05},
            "preload_index": {"uncertainty_magnitude": 0.4},
        },
        metric_id="stroke_volume_ml",
    )
    assert impacts[0].parameter_id == expected["expected_top_driver"]


def test_uncertain_insensitive_excludes_unnormalized_response() -> None:
    expected = _load("uncertain-insensitive")
    impacts = build_uncertainty_impacts(
        [
            _sens("heart_rate_bpm", 100.0, normalized=None),
            _sens("afterload_index", 1.0, normalized=0.3),
        ],
        {
            "heart_rate_bpm": {"uncertainty_magnitude": 0.9},
            "afterload_index": {"uncertainty_magnitude": 0.2},
        },
        metric_id="stroke_volume_ml",
    )
    assert [item.parameter_id for item in impacts] == expected["expected_drivers"]


def test_zero_sensitivity_high_uncertainty_ranks_low() -> None:
    expected = _load("zero-sensitivity-high-uncertainty")
    impacts = build_uncertainty_impacts(
        [
            _sens("preload_index", 0.0, normalized=0.0),
            _sens("contractility_index", 1.0, normalized=0.4),
        ],
        {
            "preload_index": {"uncertainty_magnitude": 0.8},
            "contractility_index": {"uncertainty_magnitude": 0.3},
        },
        metric_id="stroke_volume_ml",
    )
    assert impacts[0].parameter_id == expected["expected_top_driver"]


def _golden_ensemble():
    return run_ensemble(
        _request(
            _state(
                {
                    "heart_rate_bpm": 88.0,
                    "systolic_bp_mmhg": 135.0,
                    "diastolic_bp_mmhg": 85.0,
                    "edv_ml": 130.0,
                    "esv_ml": 70.0,
                }
            ),
            seed=91,
            sample_count=12,
        )
    )


def test_target_specific_evidence_ranking_may_differ() -> None:
    fixture = _load("target-specific-evidence")
    ensemble = _golden_ensemble()
    sv = run_missing_piece(ensemble, "stroke_volume_ml")
    co = run_missing_piece(ensemble, "cardiac_output_l_min")
    assert sv.provenance.analysis_id != co.provenance.analysis_id
    if fixture["rankings_differ"]:
        assert sv.evidence_ranking[:3] != co.evidence_ranking[:3]


def test_shadow_trial_driver_fixture_produces_drivers() -> None:
    fixture = _load("shadow-trial-driver")
    ensemble = _golden_ensemble()
    scenario = ScenarioDefinition(
        id="m8-golden-afterload",
        label="Afterload increase",
        origin_snapshot_id=ensemble["origin_snapshot_id"],
        parameters=[
            ScenarioParameterChange(
                parameter="afterload_index",
                baseline=1.0,
                value=1.2,
                delta=0.2,
                unit="index",
            ),
        ],
    )
    result = run_missing_piece_shadow_effect(ensemble, scenario, fixture["target_metric"])
    assert result.sensitivities
    assert result.dominant_uncertainty_drivers
    assert result.dominant_uncertainty_drivers[0].parameter_id == fixture["top_driver"]


@pytest.mark.parametrize("case", ["no-missing-evidence", "missing-structural-evidence"])
def test_engine_completeness_fixtures(case: str) -> None:
    fixture = _load(case)
    ensemble = _golden_ensemble()
    evidence = fixture.get("available_evidence_types", [])
    result = run_missing_piece(ensemble, "stroke_volume_ml", available_evidence_types=evidence)
    if case == "no-missing-evidence":
        assert result.evidence_ranking
    else:
        assert fixture["expected_includes_contractility"]
        assert "contractility_index" in result.completeness["unavailable_evidence_parameters"]
