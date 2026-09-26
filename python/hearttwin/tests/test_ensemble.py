"""Focused tests for seeded plausible-twin ensemble generation."""

from __future__ import annotations

import math
from datetime import datetime

import pytest
from pydantic import ValidationError

from python.hearttwin.ensemble import (
    PARAMETER_BOUNDS,
    EnsembleDistributionRequest,
    EnsembleRequest,
    EnsembleResponse,
    run_ensemble,
)
from python.hearttwin.schemas import (
    CardiacTwinState,
    Hemodynamics,
    MeasuredValue,
    Measurements,
    ValueSource,
)
from python.hearttwin.tools.cardiac_state import (
    compute_cardiac_output,
    compute_ejection_fraction,
    compute_stroke_volume,
)


def _measured(value: float, unit: str) -> MeasuredValue:
    return MeasuredValue(
        value=value,
        unit=unit,
        source=ValueSource.FILE_EXTRACTION,
        confidence=1.0,
    )


def _state(baseline_vitals: dict) -> CardiacTwinState:
    return CardiacTwinState(
        case_id="ensemble-fixture-case",
        created_at=datetime(2026, 1, 2, 3, 4, 5),  # noqa: DTZ001 - canonical naive fixture timestamp
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


def _distribution(
    parameter_id: str,
    *,
    family: str = "normal",
    parameters: dict[str, float | list[float]] | None = None,
    bounds: dict[str, float] | None = None,
) -> EnsembleDistributionRequest:
    defaults: dict[str, tuple[dict[str, float | list[float]], dict[str, float]]] = {
        "heart_rate_bpm": ({"mean": 72.0, "sd": 2.0}, {"min": 30.0, "max": 200.0}),
        "preload_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 1.5}),
        "afterload_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 2.0}),
        "contractility_index": ({"mean": 1.0, "sd": 0.1}, {"min": 0.0, "max": 1.5}),
        "systemic_vascular_resistance_index": (
            {"mean": 1.0, "sd": 0.1},
            {"min": 0.0, "max": 2.0},
        ),
    }
    default_parameters, default_bounds = defaults[parameter_id]
    return EnsembleDistributionRequest(
        parameter_id=parameter_id,
        family=family,
        parameters=parameters or default_parameters,
        bounds=bounds or default_bounds,
        source="measurement",
        evidence_ids=["manual_baseline.json"],
        rationale="Synthetic baseline fixture for ensemble testing",
        version="test-v1",
    )


def _request(
    state: CardiacTwinState,
    *,
    seed: int = 17,
    sample_count: int = 24,
    distributions: list[EnsembleDistributionRequest] | None = None,
) -> EnsembleRequest:
    return EnsembleRequest(
        origin_snapshot_id="snapshot-baseline",
        state=state,
        seed=seed,
        sample_count=sample_count,
        distributions=distributions
        or [_distribution(parameter_id) for parameter_id in PARAMETER_BOUNDS],
        origin_quality="observed",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("parameter_id", "unknown_parameter"),
        ("bounds", {"min": -0.1, "max": 1.0}),
        ("parameters", {"value": 201.0}),
        ("parameters", {"mean": 72.0, "sd": 0.0}),
        ("parameters", {"min": 1.2, "max": 0.8}),
        ("parameters", {"values": []}),
    ],
)
def test_distribution_validation_rejects_invalid_configuration(field: str, value: object) -> None:
    kwargs: dict[str, object] = {
        "parameter_id": "heart_rate_bpm",
        "family": "normal",
        "parameters": {"mean": 72.0, "sd": 2.0},
        "bounds": {"min": 30.0, "max": 200.0},
        "source": "measurement",
        "rationale": "test rationale",
        "version": "test-v1",
    }
    if field == "parameter_id" or field == "bounds":
        kwargs[field] = value
    elif value == {"value": 201.0}:
        kwargs["family"] = "fixed"
        kwargs[field] = value
    elif value == {"min": 1.2, "max": 0.8}:
        kwargs["family"] = "uniform"
        kwargs[field] = value
    elif value == {"values": []}:
        kwargs["family"] = "empirical"
        kwargs[field] = value
    else:
        kwargs[field] = value

    with pytest.raises((ValidationError, ValueError)):
        EnsembleDistributionRequest(**kwargs)


@pytest.mark.parametrize(
    ("family", "parameters", "bounds"),
    [
        ("fixed", {"value": 72.0}, {"min": 72.0, "max": 72.0}),
        ("normal", {"mean": 72.0, "sd": 0.01}, {"min": 30.0, "max": 200.0}),
        ("lognormal", {"mean": 72.0, "sd": 0.01}, {"min": 30.0, "max": 200.0}),
        ("uniform", {"min": 71.99, "max": 72.01}, {"min": 30.0, "max": 200.0}),
        ("empirical", {"values": [72.0]}, {"min": 30.0, "max": 200.0}),
    ],
)
def test_each_distribution_family_samples_finite_bounded_parameters(
    baseline_vitals,
    family: str,
    parameters: dict[str, float | list[float]],
    bounds: dict[str, float],
) -> None:
    heart_rate = _distribution(
        "heart_rate_bpm",
        family=family,
        parameters=parameters,
        bounds=bounds,
    )
    distributions = [
        heart_rate,
        *[
            _distribution(parameter_id, family="fixed", parameters={"value": 1.0})
            for parameter_id in PARAMETER_BOUNDS
            if parameter_id != "heart_rate_bpm"
        ],
    ]

    result = run_ensemble(_request(_state(baseline_vitals), seed=2048, sample_count=8, distributions=distributions))

    assert result["accepted_sample_count"] == 8
    for sample in result["samples"]:
        value = sample["parameters"]["heart_rate_bpm"]
        assert math.isfinite(value)
        assert bounds["min"] <= value <= bounds["max"]


@pytest.mark.parametrize(
    ("family", "parameters", "bounds"),
    [
        ("fixed", {"value": 72.0}, {"min": 72.0, "max": 72.0}),
        ("uniform", {"min": 72.0, "max": 72.0}, {"min": 72.0, "max": 72.0}),
        ("empirical", {"values": [72.0]}, {"min": 72.0, "max": 72.0}),
    ],
)
def test_deterministic_degenerate_distributions_are_supported(
    baseline_vitals,
    family: str,
    parameters: dict[str, float | list[float]],
    bounds: dict[str, float],
) -> None:
    distribution = _distribution(
        "heart_rate_bpm",
        family=family,
        parameters=parameters,
        bounds=bounds,
    )

    assert distribution.parameters == parameters
    assert distribution.bounds == bounds
    distributions = [
        distribution,
        *[
            _distribution(parameter_id, family="fixed", parameters={"value": 1.0})
            for parameter_id in PARAMETER_BOUNDS
            if parameter_id != "heart_rate_bpm"
        ],
    ]
    result = run_ensemble(_request(_state(baseline_vitals), seed=2048, sample_count=4, distributions=distributions))

    assert result["accepted_sample_count"] == 4
    assert all(sample["parameters"]["heart_rate_bpm"] == 72.0 for sample in result["samples"])


@pytest.mark.parametrize(
    ("family", "parameters"),
    [
        ("normal", {"mean": 72.0, "sd": 0.0}),
        ("normal", {"mean": 72.0, "sd": -0.1}),
        ("lognormal", {"mean": 72.0, "sd": 0.0}),
        ("lognormal", {"mean": 72.0, "sd": -0.1}),
    ],
)
def test_continuous_degenerate_distributions_require_positive_spread(
    family: str,
    parameters: dict[str, float | list[float]],
) -> None:
    with pytest.raises(ValidationError, match="standard deviation must be positive"):
        _distribution("heart_rate_bpm", family=family, parameters=parameters)


@pytest.mark.parametrize(
    ("family", "parameters", "bounds"),
    [
        ("fixed", {"value": math.nan}, None),
        ("fixed", {"value": math.inf}, None),
        ("normal", {"mean": math.nan, "sd": 2.0}, None),
        ("normal", {"mean": 72.0, "sd": math.inf}, None),
        ("lognormal", {"mean": math.nan, "sd": 0.1}, None),
        ("lognormal", {"mean": 72.0, "sd": math.inf}, None),
        ("uniform", {"min": math.nan, "max": 72.0}, None),
        ("uniform", {"min": 71.0, "max": math.inf}, None),
        ("empirical", {"values": [72.0, math.nan]}, None),
        ("empirical", {"values": [72.0, math.inf]}, None),
        ("normal", {"mean": 72.0, "sd": 2.0}, {"min": math.nan, "max": 200.0}),
        ("normal", {"mean": 72.0, "sd": 2.0}, {"min": 30.0, "max": math.inf}),
    ],
)
def test_distribution_validation_rejects_nan_and_infinity(
    family: str,
    parameters: dict[str, float | list[float]],
    bounds: dict[str, float] | None,
) -> None:
    with pytest.raises(ValidationError):
        _distribution(
            "heart_rate_bpm",
            family=family,
            parameters=parameters,
            bounds=bounds,
        )


@pytest.mark.parametrize(
    ("family", "parameters"),
    [
        ("fixed", {}),
        ("fixed", {"value": [72.0]}),
        ("normal", {"mean": 72.0}),
        ("normal", {"sd": 2.0}),
        ("lognormal", {"mean": 72.0}),
        ("uniform", {"min": 72.0}),
        ("uniform", {"max": 72.0}),
        ("empirical", {}),
        ("empirical", {"values": 72.0}),
        ("empirical", {"values": [72.0, "bad"]}),
    ],
)
def test_distribution_validation_rejects_malformed_parameter_shapes(
    family: str,
    parameters: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        EnsembleDistributionRequest(
            parameter_id="heart_rate_bpm",
            family=family,
            parameters=parameters,
            bounds={"min": 30.0, "max": 200.0},
            source="measurement",
            rationale="test rationale",
            version="test-v1",
        )


@pytest.mark.parametrize(
    ("family", "parameters", "bounds"),
    [
        ("gaussian", {"mean": 72.0, "sd": 2.0}, {"min": 30.0, "max": 200.0}),
        ("normal", {"mean": 72.0, "sd": 2.0}, {"min": 30.0}),
        ("normal", {"mean": 72.0, "sd": 2.0}, {"max": 200.0}),
        ("normal", None, {"min": 30.0, "max": 200.0}),
    ],
)
def test_distribution_validation_rejects_malformed_metadata(
    family: str,
    parameters: object,
    bounds: dict[str, float],
) -> None:
    with pytest.raises(ValidationError):
        EnsembleDistributionRequest(
            parameter_id="heart_rate_bpm",
            family=family,
            parameters=parameters,
            bounds=bounds,
            source="measurement",
            rationale="test rationale",
            version="test-v1",
        )


def test_ensemble_request_requires_all_unique_deterministic_parameters(baseline_vitals) -> None:
    distributions = [_distribution(parameter_id) for parameter_id in PARAMETER_BOUNDS]
    distributions[-1] = distributions[0]

    with pytest.raises(ValidationError, match="unique"):
        _request(_state(baseline_vitals), distributions=distributions)


def test_same_seed_is_repeatable(baseline_vitals) -> None:
    state = _state(baseline_vitals)

    first = run_ensemble(_request(state, seed=123))
    second = run_ensemble(_request(state, seed=123))

    assert first == second


def test_different_seeds_change_sampled_ensemble(baseline_vitals) -> None:
    state = _state(baseline_vitals)

    first = run_ensemble(_request(state, seed=123))
    second = run_ensemble(_request(state, seed=124))

    assert first["id"] != second["id"]
    assert first["samples"] != second["samples"]


def test_rejection_accounting_matches_sample_validity(baseline_vitals) -> None:
    distributions = [_distribution(parameter_id) for parameter_id in PARAMETER_BOUNDS]
    distributions[0] = _distribution(
        "heart_rate_bpm",
        bounds={"min": 71.0, "max": 73.0},
    )
    result = run_ensemble(_request(_state(baseline_vitals), seed=17, distributions=distributions))

    valid = [sample for sample in result["samples"] if sample["valid"]]
    rejected = [sample for sample in result["samples"] if not sample["valid"]]
    assert valid
    assert rejected
    assert result["requested_sample_count"] == len(result["samples"])
    assert result["accepted_sample_count"] == len(valid)
    assert result["rejected_sample_count"] == len(rejected)
    assert result["accepted_sample_count"] + result["rejected_sample_count"] == result["requested_sample_count"]
    assert all(sample["rejection_reasons"] for sample in rejected)
    assert all(not sample["rejection_reasons"] for sample in valid)


def test_accepted_samples_preserve_physiological_invariants(baseline_vitals) -> None:
    result = run_ensemble(_request(_state(baseline_vitals), seed=321, sample_count=48))

    assert result["accepted_sample_count"] > 0
    for sample in result["samples"]:
        if not sample["valid"]:
            continue
        outputs = sample["outputs"]
        assert outputs["edv"] > outputs["esv"]
        assert outputs["stroke_volume_ml"] > 0
        assert 0 <= outputs["ejection_fraction_pct"] <= 100
        assert outputs["cardiac_output_l_min"] > 0


def test_accepted_samples_match_deterministic_physiology_contracts(baseline_vitals) -> None:
    result = run_ensemble(_request(_state(baseline_vitals), seed=321, sample_count=48))

    for sample in result["samples"]:
        if not sample["valid"]:
            continue
        outputs = sample["outputs"]
        stroke_volume = compute_stroke_volume(outputs["edv"], outputs["esv"])

        assert outputs["stroke_volume_ml"] == pytest.approx(stroke_volume)
        assert outputs["ejection_fraction_pct"] == pytest.approx(
            compute_ejection_fraction(outputs["edv"], outputs["esv"])
        )
        assert outputs["cardiac_output_l_min"] == pytest.approx(
            compute_cardiac_output(outputs["heart_rate_bpm"], outputs["stroke_volume_ml"])
        )


def test_result_contains_seeded_provenance(baseline_vitals) -> None:
    state = _state(baseline_vitals)
    result = run_ensemble(_request(state, seed=456, sample_count=8))

    assert result["origin_snapshot_id"] == "snapshot-baseline"
    assert result["seed"] == 456
    assert result["provenance"] == {
        "origin_snapshot_id": "snapshot-baseline",
        "origin_timestamp": state.created_at.isoformat(),
        "origin_quality": "observed",
        "origin_provenance": [],
        "parent_scenario_id": None,
        "evidence_ids": ["manual_baseline.json"],
        "seed": 456,
        "physiology_version": "m5.5-ensemble-projection-v1",
        "distribution_config_version": "m5.5-backend-ensemble-v1",
        "prior_version": "m5-priors-v1",
        "created_at": state.created_at.isoformat(),
        "assumptions": [
            "Input proxies are sampled independently because no validated joint correlation model is available.",
            "Percentiles summarize accepted deterministic simulations and are not clinical confidence intervals.",
        ],
    }
    assert all(sample["origin_snapshot_id"] == "snapshot-baseline" for sample in result["samples"])
    assert all(sample["seed"] == 456 for sample in result["samples"])
    assert "Educational simulation only; not diagnosis or treatment advice." in result["warnings"]


def test_result_validates_against_canonical_response_contract(baseline_vitals) -> None:
    result = run_ensemble(_request(_state(baseline_vitals), seed=456, sample_count=8))

    response = EnsembleResponse.model_validate(result)

    assert response.model_dump(mode="json") == result
    assert response.requested_sample_count == 8
    assert response.accepted_sample_count == 8
    assert {distribution.metric_id for distribution in response.distributions} == {
        "ejection_fraction_pct",
        "stroke_volume_ml",
        "cardiac_output_l_min",
        "heart_rate_bpm",
    }
    assert response.provenance.origin_snapshot_id == response.origin_snapshot_id
    assert response.safety_disclaimer.startswith("Educational cardiac simulation only.")


def test_response_contract_rejects_inconsistent_counts(baseline_vitals) -> None:
    result = run_ensemble(_request(_state(baseline_vitals), sample_count=4))
    result["accepted_sample_count"] = 3

    with pytest.raises(ValidationError, match="counts do not reconcile"):
        EnsembleResponse.model_validate(result)


def test_response_contract_rejects_unknown_fields(baseline_vitals) -> None:
    result = run_ensemble(_request(_state(baseline_vitals), sample_count=4))
    result["unexpected"] = True

    with pytest.raises(ValidationError, match="unexpected"):
        EnsembleResponse.model_validate(result)


def test_response_contract_rejects_tampered_safety_disclaimer(baseline_vitals) -> None:
    result = run_ensemble(_request(_state(baseline_vitals), sample_count=4))
    result["safety_disclaimer"] = "arbitrary disclaimer"

    with pytest.raises(ValidationError, match="canonical disclaimer"):
        EnsembleResponse.model_validate(result)


def test_response_contract_rejects_tampered_distribution_summary(baseline_vitals) -> None:
    result = run_ensemble(_request(_state(baseline_vitals), sample_count=4))
    result["distributions"][0]["mean"] += 1.0

    with pytest.raises(ValidationError, match="does not match accepted samples"):
        EnsembleResponse.model_validate(result)
