"""Focused tests for the honest M8 local aggregate boundary."""

from __future__ import annotations

import pytest

from python.hearttwin.missing_piece.contracts import (
    ParameterSensitivity,
    SensitivityProvenance,
)
from python.hearttwin.missing_piece.global_sensitivity import (
    aggregate_local_sensitivity,
)


def _record(parameter_id: str, metric_id: str, sensitivity: float) -> ParameterSensitivity:
    return ParameterSensitivity(
        parameter_id=parameter_id,
        metric_id=metric_id,
        method="finite_difference",
        sensitivity=sensitivity,
        baseline_value=1.0,
        perturbation=0.05,
        provenance=SensitivityProvenance(sample_count=1),
    )


def test_aggregate_is_deterministic_and_keeps_local_method_boundary() -> None:
    records = [
        _record("preload_index", "stroke_volume_ml", -2.0),
        _record("preload_index", "stroke_volume_ml", 4.0),
        _record("afterload_index", "stroke_volume_ml", 1.0),
    ]

    first = aggregate_local_sensitivity(records)
    second = aggregate_local_sensitivity(reversed(records))

    assert first == second
    assert [item.parameter_id for item in first] == ["preload_index", "afterload_index"]
    assert first[0].method == "median_absolute_local_response_v1"
    assert first[0].median_absolute_sensitivity == pytest.approx(3.0)
    assert first[0].q25_absolute_sensitivity == pytest.approx(2.5)
    assert first[0].q75_absolute_sensitivity == pytest.approx(3.5)
    assert first[0].sample_count == 2
    assert "sobol" not in first[0].method
    assert "shapley" not in first[0].method


def test_unsupported_global_method_is_not_reinterpreted() -> None:
    record = _record("preload_index", "stroke_volume_ml", 2.0).model_copy(
        update={"method": "sobol"}
    )

    with pytest.raises(ValueError, match="local finite-difference"):
        aggregate_local_sensitivity([record])
