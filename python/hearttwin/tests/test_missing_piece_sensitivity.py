"""Focused tests for the bounded M8 local sensitivity surface."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime

import pytest

from python.hearttwin.ensemble import PARAMETER_BOUNDS
from python.hearttwin.missing_piece.perturbations import (
    PerturbationPolicy,
    validate_baseline,
)
from python.hearttwin.missing_piece.sensitivity import run_local_sensitivity
from python.hearttwin.schemas import (
    CardiacTwinState,
    Hemodynamics,
    MeasuredValue,
    Measurements,
    ValueSource,
)


def _measured(value: float, unit: str) -> MeasuredValue:
    return MeasuredValue(
        value=value,
        unit=unit,
        source=ValueSource.FILE_EXTRACTION,
        confidence=1.0,
    )


def _state(baseline_vitals: dict[str, float]) -> CardiacTwinState:
    return CardiacTwinState(
        case_id="m8-sensitivity-fixture",
        created_at=datetime(2026, 1, 2, 3, 4, 5),  # noqa: DTZ001 - deterministic fixture
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


def test_known_finite_difference_is_deterministic_and_finite(baseline_vitals) -> None:
    state = _state(baseline_vitals)
    bounds = {"heart_rate_bpm": PARAMETER_BOUNDS["heart_rate_bpm"]}

    first = run_local_sensitivity(state, bounds, "heart_rate_bpm")
    second = run_local_sensitivity(state, bounds, "heart_rate_bpm")

    assert first == second
    assert len(first) == 1
    result = first[0]
    assert result.method == "finite_difference"
    assert result.metric_id == "heart_rate_bpm"
    assert result.sensitivity == pytest.approx(1.0)
    assert result.perturbation == pytest.approx(4.25)
    assert result.provenance.assumptions


def test_perturbations_are_bounded_and_switch_to_one_sided_at_domain_edges() -> None:
    policy = PerturbationPolicy("heart_rate_bpm", step=0.5, mode="absolute")

    lower = policy.points(30.0)
    upper = policy.points(200.0)

    assert lower.method == "forward"
    assert lower.lower is None
    assert lower.upper == pytest.approx(30.5)
    assert upper.method == "backward"
    assert upper.lower == pytest.approx(199.5)
    assert upper.upper is None
    assert 0.0 < lower.step <= policy.maximum_step
    assert validate_baseline("heart_rate_bpm", 30.0) == 30.0

    with pytest.raises(ValueError, match="within"):
        validate_baseline("heart_rate_bpm", 200.1)
    with pytest.raises(ValueError, match="bounds exceed"):
        run_local_sensitivity(
            _state({
                "heart_rate_bpm": 72.0,
                "systolic_bp_mmhg": 120.0,
                "diastolic_bp_mmhg": 80.0,
                "edv_ml": 120.0,
                "esv_ml": 50.0,
            }),
            {"heart_rate_bpm": (29.0, 200.0)},
            "heart_rate_bpm",
        )


def test_output_is_target_specific_and_preserves_metric_identity(baseline_vitals) -> None:
    state = _state(baseline_vitals)
    bounds = {"preload_index": PARAMETER_BOUNDS["preload_index"]}

    ef_result = run_local_sensitivity(state, bounds, "ejection_fraction_pct")[0]
    sv_result = run_local_sensitivity(state, bounds, "stroke_volume_ml")[0]

    assert ef_result.metric_id == "ejection_fraction_pct"
    assert sv_result.metric_id == "stroke_volume_ml"
    assert ef_result.baseline_value == pytest.approx(58.3333333333)
    assert sv_result.baseline_value == pytest.approx(70.0)
    assert ef_result.baseline_value != sv_result.baseline_value


def test_sensitivity_does_not_mutate_state_or_bounds(baseline_vitals) -> None:
    state = _state(baseline_vitals)
    bounds = {"afterload_index": [0.0, 2.0]}
    state_before = deepcopy(state)
    bounds_before = deepcopy(bounds)

    run_local_sensitivity(state, bounds, "stroke_volume_ml")

    assert state == state_before
    assert bounds == bounds_before


def test_results_have_no_synthetic_clinical_labels(baseline_vitals) -> None:
    results = run_local_sensitivity(
        _state(baseline_vitals),
        {"contractility_index": PARAMETER_BOUNDS["contractility_index"]},
        "ejection_fraction_pct",
    )

    for result in results:
        assert not hasattr(result, "clinical_label")
        assert "clinical_label" not in result.model_dump(mode="python")
        text = " ".join(result.provenance.assumptions).lower()
        assert not any(
            forbidden in text
            for forbidden in (
                "diagnos",
                "treat",
                "recommend",
                "benefit",
                "harm",
                "risk",
                "normal",
                "abnormal",
            )
        )
