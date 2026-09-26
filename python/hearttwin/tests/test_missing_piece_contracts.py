from __future__ import annotations

import pytest
from pydantic import ValidationError

from python.hearttwin.missing_piece.contracts import (
    ParameterSensitivity,
    SensitivityProvenance,
)


def _provenance() -> SensitivityProvenance:
    return SensitivityProvenance(analysis_id="a", model_version="test")


def test_unsupported_global_methods_are_rejected_at_contract_boundary() -> None:
    with pytest.raises(ValidationError):
        ParameterSensitivity(
            parameter_id="heart_rate_bpm",
            metric_id="heart_rate_bpm",
            method="sobol",
            sensitivity=1.0,
            baseline_value=80.0,
            provenance=_provenance(),
        )


def test_unavailable_sensitivity_cannot_carry_numeric_values() -> None:
    with pytest.raises(ValidationError):
        ParameterSensitivity(
            parameter_id="heart_rate_bpm",
            metric_id="heart_rate_bpm",
            method="finite_difference",
            sensitivity=1.0,
            baseline_value=80.0,
            available=False,
            unavailable_reason="projection unavailable",
            provenance=_provenance(),
        )


def test_shadow_effect_contract_is_explicit() -> None:
    record = ParameterSensitivity(
        parameter_id="afterload_index",
        metric_id="stroke_volume_ml",
        method="finite_difference",
        sensitivity=-1.0,
        baseline_value=-4.0,
        perturbation=0.05,
        normalized_sensitivity=-0.2,
        target_kind="shadow_effect",
        provenance=_provenance(),
    )
    assert record.target_kind == "shadow_effect"
