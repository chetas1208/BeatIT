from __future__ import annotations

import pytest
from pydantic import ValidationError

from python.hearttwin.missing_piece.api_models import (
    MissingPieceRequest,
    MissingPieceResponse,
)
from python.hearttwin.missing_piece.contracts import (
    MissingPieceProvenance,
    MissingPieceResult,
)
from python.hearttwin.safety import DISCLAIMER


def _response_payload() -> dict[str, object]:
    return MissingPieceResult(
        target_metric="stroke_volume_ml",
        limitations=["Local deterministic sensitivity only."],
        provenance=MissingPieceProvenance(
            analysis_id="analysis-1",
            sensitivity_method="finite_difference",
            ranking_method="evidence-priority-score-v1",
            assumptions=["Synthetic test fixture."],
        ),
    ).model_dump(mode="json")


def test_missing_piece_request_is_strict_and_identifier_bounded() -> None:
    request = MissingPieceRequest(
        baseline_ensemble_id=" ensemble-abc ",
        target_metric="stroke_volume_ml",
        available_evidence_types=[" repeat_ecg "],
    )
    assert request.baseline_ensemble_id == "ensemble-abc"
    assert request.available_evidence_types == ["repeat_ecg"]

    with pytest.raises(ValidationError):
        MissingPieceRequest(baseline_ensemble_id=123, target_metric="stroke_volume_ml")
    with pytest.raises(ValidationError):
        MissingPieceRequest(baseline_ensemble_id="ensemble-abc", target_metric="patient email")
    with pytest.raises(ValidationError):
        MissingPieceRequest(
            baseline_ensemble_id="ensemble-abc",
            target_metric="stroke_volume_ml",
            available_evidence_types=["repeat_ecg", "repeat_ecg"],
        )
    with pytest.raises(ValidationError):
        MissingPieceRequest(
            baseline_ensemble_id="ensemble-abc",
            target_metric="stroke_volume_ml",
            unexpected="value",
        )


def test_missing_piece_response_requires_canonical_disclaimer_and_safe_metadata() -> None:
    payload = _response_payload()
    response = MissingPieceResponse.model_validate(payload)
    assert response.safety_disclaimer == DISCLAIMER

    with pytest.raises(ValidationError):
        MissingPieceResponse.model_validate({**payload, "safety_disclaimer": "custom"})
    with pytest.raises(ValidationError):
        MissingPieceResponse.model_validate(
            {**payload, "completeness": {"api_key": "should-not-persist"}}
        )


def test_shadow_effect_request_requires_a_persisted_trial_id() -> None:
    request = MissingPieceRequest(
        baseline_ensemble_id="ensemble-abc",
        target_metric="stroke_volume_ml",
        target_kind="shadow_effect",
        shadow_trial_id="trial-abc",
    )
    assert request.target_kind == "shadow_effect"
    with pytest.raises(ValidationError):
        MissingPieceRequest(
            baseline_ensemble_id="ensemble-abc",
            target_metric="stroke_volume_ml",
            target_kind="shadow_effect",
        )
