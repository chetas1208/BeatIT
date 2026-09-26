"""Focused tests for M8 effect analysis over the canonical M6 pairing seam."""

from __future__ import annotations

from copy import deepcopy

from python.hearttwin.ensemble import (
    PARAMETER_BOUNDS,
    EnsembleResponse,
    _evaluate,
    run_ensemble,
)
from python.hearttwin.safety import DISCLAIMER
from python.hearttwin.shadow_trial_engine import (
    ScenarioDefinition,
    ScenarioParameterChange,
    run_shadow_trial,
)
from python.hearttwin.tests.test_ensemble import _request, _state


def _ensemble(baseline_vitals: dict, *, sample_count: int = 6) -> dict:
    """Build the deterministic M5 fixture used by the existing M6 tests."""

    return run_ensemble(_request(_state(baseline_vitals), seed=91, sample_count=sample_count))


def _fixed_afterload_scenario(ensemble: dict) -> ScenarioDefinition:
    return ScenarioDefinition(
        id="fixed-afterload-effect-driver",
        label="Fixed afterload hypothetical",
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


def test_effect_is_deterministic_and_paired_to_the_same_sample(baseline_vitals) -> None:
    ensemble = _ensemble(baseline_vitals)
    scenario = _fixed_afterload_scenario(ensemble)

    first = run_shadow_trial(ensemble, scenario, metrics=["stroke_volume_ml"])
    second = run_shadow_trial(ensemble, scenario, metrics=["stroke_volume_ml"])

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.valid_pairs == len(ensemble["samples"])

    for pair, sample in zip(first.paired_results, sorted(ensemble["samples"], key=lambda item: item["id"])):
        expected_parameters = {**sample["parameters"], "afterload_index": 1.2}
        expected_outputs = _evaluate(sample["projection_base"], expected_parameters)

        assert pair.sample_id == sample["id"]
        assert pair.baseline_parameters == sample["parameters"]
        assert pair.scenario_parameters == expected_parameters
        assert pair.deltas["stroke_volume_ml"] == (
            expected_outputs["stroke_volume_ml"] - sample["outputs"]["stroke_volume_ml"]
        )


def test_intervention_target_remains_fixed_while_baseline_sample_varies(baseline_vitals) -> None:
    ensemble = _ensemble(baseline_vitals, sample_count=8)
    scenario = _fixed_afterload_scenario(ensemble)

    result = run_shadow_trial(ensemble, scenario, metrics=["ejection_fraction_pct"])

    assert result.valid_pairs == len(ensemble["samples"])
    for pair in result.paired_results:
        assert pair.scenario_parameters["afterload_index"] == 1.2
        for parameter_id in PARAMETER_BOUNDS:
            if parameter_id != "afterload_index":
                assert pair.scenario_parameters[parameter_id] == pair.baseline_parameters[parameter_id]


def test_missing_projection_base_is_retained_as_an_invalid_pair(baseline_vitals) -> None:
    ensemble = EnsembleResponse.model_validate(_ensemble(baseline_vitals, sample_count=3))
    missing_base = ensemble.samples[0].model_copy(update={"projection_base": None})
    broken = ensemble.model_copy(update={"samples": [missing_base, *ensemble.samples[1:]]})

    result = run_shadow_trial(
        broken,
        _fixed_afterload_scenario(broken.model_dump(mode="python")),
        metrics=["stroke_volume_ml"],
    )

    pair = next(item for item in result.paired_results if item.sample_id == missing_base.id)
    assert pair.valid is False
    assert pair.deltas == {}
    assert any("projection base" in reason for reason in pair.rejection_reasons)
    assert result.invalid_pairs == 1


def test_rejected_sample_is_not_used_as_an_effect_driver(baseline_vitals) -> None:
    ensemble = EnsembleResponse.model_validate(_ensemble(baseline_vitals, sample_count=3))
    rejected = ensemble.samples[0].model_copy(
        update={
            "valid": False,
            "projection_base": None,
            "rejection_reasons": ["fixture rejection"],
        }
    )
    broken = ensemble.model_copy(update={"samples": [rejected, *ensemble.samples[1:]]})

    result = run_shadow_trial(
        broken,
        _fixed_afterload_scenario(broken.model_dump(mode="python")),
        metrics=["stroke_volume_ml"],
    )

    pair = next(item for item in result.paired_results if item.sample_id == rejected.id)
    assert pair.valid is False
    assert pair.deltas == {}
    assert any("fixture rejection" in reason for reason in pair.rejection_reasons)


def test_effect_driver_exposes_simulation_boundary_without_clinical_claims(baseline_vitals) -> None:
    ensemble = _ensemble(baseline_vitals, sample_count=2)
    before = deepcopy(ensemble)
    result = run_shadow_trial(
        ensemble,
        _fixed_afterload_scenario(ensemble),
        metrics=["stroke_volume_ml"],
    )

    assert result.safety_disclaimer == DISCLAIMER
    warning_text = " ".join(result.warnings).lower()
    assert "hypothetical paired simulation" in warning_text
    assert "not diagnosis" in warning_text
    assert "clinical efficacy evidence" in warning_text
    assert not any(
        phrase in warning_text
        for phrase in (
            "is a diagnosis",
            "diagnoses the",
            "treats the",
            "recommended treatment",
            "proven effective",
        )
    )
    assert ensemble == before
