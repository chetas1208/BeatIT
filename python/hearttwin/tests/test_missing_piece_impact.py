"""Focused tests for the M8 uncertainty-impact heuristic."""

from __future__ import annotations

from python.hearttwin.missing_piece.contracts import (
    ParameterSensitivity,
    SensitivityProvenance,
)
from python.hearttwin.missing_piece.impact import build_uncertainty_impacts


def _sensitivity(
    parameter_id: str,
    sensitivity: float,
    *,
    metric_id: str = "stroke_volume_ml",
    normalized: float | None = None,
) -> ParameterSensitivity:
    return ParameterSensitivity(
        parameter_id=parameter_id,
        metric_id=metric_id,
        method="finite_difference",
        sensitivity=sensitivity,
        baseline_value=70.0,
        perturbation=0.05,
        normalized_sensitivity=normalized,
        provenance=SensitivityProvenance(sample_count=2),
    )


def test_prefers_normalized_local_response_and_sorts_ties_deterministically() -> None:
    records = [
        _sensitivity("preload_index", 100.0, normalized=0.2),
        _sensitivity("afterload_index", -1.0, normalized=-0.4),
    ]
    uncertainty = {
        "preload_index": {"uncertainty_magnitude": 0.5},
        "afterload_index": {"uncertainty_magnitude": 0.25},
    }

    result = build_uncertainty_impacts(records, uncertainty, metric_id="stroke_volume_ml")

    assert [item.parameter_id for item in result] == ["afterload_index", "preload_index"]
    assert result[0].sensitivity_magnitude == 0.4
    assert result[0].impact_score == result[1].impact_score == 0.1
    assert result[0].normalized_impact == result[1].normalized_impact == 0.5
    assert all(item.method == "uncertainty-impact-heuristic-v1" for item in result)


def test_raw_local_response_without_normalization_is_unavailable_for_ranking() -> None:
    result = build_uncertainty_impacts(
        [_sensitivity("heart_rate_bpm", -2.0, metric_id="heart_rate_bpm")],
        {"heart_rate_bpm": {"uncertainty_magnitude": 0.25}},
        metric_id="heart_rate_bpm",
    )

    assert result == []


def test_ignores_unavailable_or_invalid_sampled_spread() -> None:
    records = [
        _sensitivity("preload_index", 2.0),
        _sensitivity("afterload_index", 3.0),
        _sensitivity("contractility_index", 4.0),
    ]
    uncertainty = {
        "preload_index": {"uncertainty_magnitude": None},
        "afterload_index": {"uncertainty_magnitude": -0.1},
        "contractility_index": {"uncertainty_magnitude": float("nan")},
    }

    assert build_uncertainty_impacts(records, uncertainty, metric_id="stroke_volume_ml") == []
