"""Focused correctness tests for the isolated M6 paired trial engine."""

from __future__ import annotations

from copy import deepcopy

from python.hearttwin.ensemble import EnsembleResponse, _evaluate, run_ensemble
from python.hearttwin.shadow_trial_engine import (
    DEFAULT_EFFECT_METRICS,
    ScenarioDefinition,
    ScenarioParameterChange,
    run_shadow_trial,
)
from python.hearttwin.tests.test_ensemble import _request, _state


def _ensemble(baseline_vitals: dict, *, sample_count: int = 8):
    return run_ensemble(_request(_state(baseline_vitals), seed=91, sample_count=sample_count))


def test_pairs_each_sample_without_resampling_and_keeps_effect_units(baseline_vitals) -> None:
    ensemble = _ensemble(baseline_vitals)
    scenario = ScenarioDefinition(
        id="afterload-120",
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

    result = run_shadow_trial(ensemble, scenario)

    assert result.requested_pairs == len(ensemble["samples"])
    assert result.valid_pairs == result.requested_pairs
    assert result.invalid_pairs == 0
    assert [pair.sample_id for pair in result.paired_results] == sorted(
        sample["id"] for sample in ensemble["samples"]
    )
    for pair, sample in zip(result.paired_results, sorted(ensemble["samples"], key=lambda item: item["id"])):
        assert pair.sample_id == sample["id"]
        assert pair.scenario_twin_id == f"{result.id}-scenario-{sample['id']}"
        assert pair.parameters == sample["parameters"]
        assert pair.baseline_state.model_dump(mode="json") == sample["state"]
        assert pair.deltas["ejection_fraction_pct"] != 0.0

    distributions = {item.metric_id: item for item in result.effect_distributions}
    assert set(distributions) == set(DEFAULT_EFFECT_METRICS)
    assert distributions["ejection_fraction_pct"].unit == "percentage_points"
    assert distributions["stroke_volume_ml"].unit == "mL"
    assert distributions["cardiac_output_l_min"].unit == "L/min"
    assert distributions["heart_rate_bpm"].unit == "bpm"


def test_noop_scenario_has_exact_zero_deltas_and_does_not_mutate_ensemble(baseline_vitals) -> None:
    ensemble = _ensemble(baseline_vitals)
    before = deepcopy(ensemble)

    result = run_shadow_trial(
        ensemble,
        ScenarioDefinition(id="no-op", label="No-op hypothetical"),
    )

    assert result.valid_pairs == result.requested_pairs
    assert all(delta == 0.0 for pair in result.paired_results for delta in pair.deltas.values())
    assert ensemble == before
    assert all(pair.baseline_state == pair.scenario_state for pair in result.paired_results)
    assert all(item.mean_delta == 0.0 for item in result.effect_distributions)


def test_pairing_is_order_independent_and_reproducible(baseline_vitals) -> None:
    ensemble = _ensemble(baseline_vitals)
    scenario = ScenarioDefinition(
        id="preload-110",
        label="Preload hypothetical",
        parameters=[ScenarioParameterChange(parameter="preload_index", value=1.1)],
    )
    shuffled = {**ensemble, "samples": list(reversed(ensemble["samples"]))}

    first = run_shadow_trial(ensemble, scenario)
    second = run_shadow_trial(shuffled, scenario)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.model_dump(mode="json") == run_shadow_trial(ensemble, scenario).model_dump(mode="json")


def test_invalid_pair_is_retained_and_excluded_from_effects(baseline_vitals) -> None:
    ensemble = EnsembleResponse.model_validate(_ensemble(baseline_vitals, sample_count=3))
    bad_state = ensemble.samples[0].state.model_copy(
        update={
            "measurements": ensemble.samples[0].state.measurements.model_copy(
                update={"edv_ml": None, "esv_ml": None}
            )
        }
    )
    bad_sample = ensemble.samples[0].model_copy(update={"state": bad_state})
    broken = ensemble.model_copy(update={"samples": [bad_sample, *ensemble.samples[1:]]})

    result = run_shadow_trial(
        broken,
        ScenarioDefinition(
            id="invalid-baseline",
            label="Invalid baseline test",
            parameters=[ScenarioParameterChange(parameter="afterload_index", value=1.2)],
        ),
    )

    invalid = next(pair for pair in result.paired_results if pair.sample_id == bad_sample.id)
    assert result.invalid_pairs == 1
    assert result.valid_pairs == 2
    assert invalid.valid is False
    assert invalid.deltas == {}
    assert any("baseline state" in reason for reason in invalid.rejection_reasons)
    assert all(len(distribution.deltas) == result.valid_pairs for distribution in result.effect_distributions)
    assert any("invalid" in warning for warning in result.warnings)


def test_mixed_sample_scenario_uses_persisted_projection_base_once(baseline_vitals) -> None:
    ensemble = _ensemble(baseline_vitals, sample_count=4)
    scenario = ScenarioDefinition(
        id="mixed-afterload",
        label="Afterload hypothetical over mixed baseline",
        parameters=[ScenarioParameterChange(parameter="afterload_index", value=1.2)],
    )

    result = run_shadow_trial(ensemble, scenario)
    for pair, sample in zip(result.paired_results, sorted(ensemble["samples"], key=lambda item: item["id"])):
        expected_parameters = {**sample["parameters"], "afterload_index": 1.2}
        expected_outputs = _evaluate(sample["projection_base"], expected_parameters)
        assert pair.scenario_parameters == expected_parameters
        assert pair.deltas["stroke_volume_ml"] == expected_outputs["stroke_volume_ml"] - sample["outputs"]["stroke_volume_ml"]


def test_missing_pv_metric_is_explicitly_invalid_not_fabricated(baseline_vitals) -> None:
    result = run_shadow_trial(
        _ensemble(baseline_vitals, sample_count=2),
        ScenarioDefinition(id="pv-request", label="PV request"),
        metrics=["pv_loop_area_index"],
    )

    assert result.valid_pairs == 0
    assert result.invalid_pairs == result.requested_pairs
    assert all("pv_loop_area_index" in pair.rejection_reasons[0] for pair in result.paired_results)
    distribution = result.effect_distributions[0]
    assert distribution.deltas == []
    assert distribution.mean_delta is None
