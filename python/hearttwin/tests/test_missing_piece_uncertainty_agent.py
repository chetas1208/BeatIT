from __future__ import annotations

from python.hearttwin.ensemble import PARAMETER_BOUNDS, EnsembleResponse, EnsembleSample
from python.hearttwin.missing_piece.uncertainty_agent import run_uncertainty_agent


def _response(values: list[dict[str, float]], valid: list[bool] | None = None) -> EnsembleResponse:
    validity = valid or [True] * len(values)
    samples = [
        EnsembleSample.model_construct(
            id=f"sample-{index}",
            index=index,
            seed=7,
            origin_snapshot_id="snapshot-test",
            origin_quality="synthetic",
            parameters=parameters,
            projection_base=None,
            outputs={},
            state=None,
            valid=is_valid,
            rejection_reasons=[] if is_valid else ["test rejection"],
        )
        for index, (parameters, is_valid) in enumerate(zip(values, validity))
    ]
    return EnsembleResponse.model_construct(samples=samples)


def test_uses_only_accepted_samples_and_reports_empirical_q05_q95() -> None:
    first = {parameter_id: low for parameter_id, (low, _) in PARAMETER_BOUNDS.items()}
    second = {parameter_id: high for parameter_id, (_, high) in PARAMETER_BOUNDS.items()}
    result = run_uncertainty_agent(_response([first, second]))

    heart_rate = result["heart_rate_bpm"]
    assert heart_rate["available"] is True
    assert heart_rate["q05"] == 38.5
    assert heart_rate["q95"] == 191.5
    assert heart_rate["uncertainty_magnitude"] == 0.9
    assert "probability" in heart_rate["interpretation"]
    assert "confidence" in heart_rate["interpretation"]


def test_fewer_than_two_accepted_values_are_unavailable_not_zero() -> None:
    sample = {
        parameter_id: (low + high) / 2
        for parameter_id, (low, high) in PARAMETER_BOUNDS.items()
    }
    result = run_uncertainty_agent(_response([sample, sample], valid=[True, False]))

    for record in result.values():
        assert record["available"] is False
        assert record["uncertainty_magnitude"] is None
        assert record["q05"] is None
        assert record["q95"] is None
        assert "at least two" in record["reason"]
