"""Focused review gates for the M8 orchestration engine."""

from __future__ import annotations

from copy import deepcopy

import pytest

from python.hearttwin.ensemble import EnsembleResponse, run_ensemble
from python.hearttwin.missing_piece.engine import run_missing_piece
from python.hearttwin.safety import DISCLAIMER
from python.hearttwin.tests.test_ensemble import _request, _state


def _ensemble() -> EnsembleResponse:
    return EnsembleResponse.model_validate(run_ensemble(
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
            sample_count=8,
        )
    ))


def test_engine_uses_persisted_projection_base_and_not_stored_outputs() -> None:
    original = _ensemble()
    tampered = deepcopy(original)
    for sample in tampered.samples:
        sample.outputs["stroke_volume_ml"] = 9999.0

    expected = run_missing_piece(original, "stroke_volume_ml")
    actual = run_missing_piece(tampered, "stroke_volume_ml")

    assert actual.model_dump(mode="json") == expected.model_dump(mode="json")


def test_engine_reports_missing_projection_base_as_unavailable() -> None:
    ensemble = deepcopy(_ensemble())
    for sample in ensemble.samples:
        sample.projection_base = None

    result = run_missing_piece(ensemble, "stroke_volume_ml")
    availability = result.completeness["sensitivity_availability"]

    assert result.sensitivities == []
    assert availability["available"] is False
    assert availability["unavailable_sample_count"] == len(ensemble.samples)
    assert availability["unavailable_reasons"]


def test_engine_target_is_specific_and_rejects_unknown_metrics() -> None:
    ensemble = _ensemble()
    ef = run_missing_piece(ensemble, "ejection_fraction_pct")
    stroke_volume = run_missing_piece(ensemble, "stroke_volume_ml")

    assert ef.provenance.analysis_id != stroke_volume.provenance.analysis_id
    assert {item.metric_id for item in ef.sensitivities} == {"ejection_fraction_pct"}
    assert {item.metric_id for item in stroke_volume.sensitivities} == {"stroke_volume_ml"}
    assert all(item.normalized_sensitivity is not None for item in ef.sensitivities)
    with pytest.raises(ValueError, match="unsupported target_metric"):
        run_missing_piece(ensemble, "diagnosis")


def test_engine_keeps_safety_and_information_gain_boundary_explicit() -> None:
    result = run_missing_piece(_ensemble(), "cardiac_output_l_min")
    text = " ".join(result.limitations).lower()

    assert result.safety_disclaimer == DISCLAIMER
    assert "not expected information gain" in text
    assert "medical recommendation" in text
