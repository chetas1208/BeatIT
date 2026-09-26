"""Focused contract tests for the backend-only M6 Shadow Trial models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from python.hearttwin.schemas import CardiacTwinState
from python.hearttwin.shadow_trial_contracts import (
    EffectDistribution,
    EffectQuantiles,
    PairedTwinResult,
    ScenarioDefinition,
    ScenarioParameterChange,
    ShadowTrialDefinition,
    ShadowTrialProvenance,
    ShadowTrialResult,
)


NOW = datetime(2026, 9, 26, tzinfo=timezone.utc)


def _state() -> CardiacTwinState:
    return CardiacTwinState()


def _change() -> ScenarioParameterChange:
    return ScenarioParameterChange(
        parameter="afterload_index",
        baseline=1.0,
        value=0.8,
        delta=-0.2,
        unit="index",
    )


def _scenario() -> ScenarioDefinition:
    return ScenarioDefinition(
        id="scenario-1",
        label="Bounded afterload change",
        origin_snapshot_id="snapshot-1",
        parameters=[_change()],
        created_at=NOW,
    )


def _provenance() -> ShadowTrialProvenance:
    return ShadowTrialProvenance(
        origin_snapshot_id="snapshot-1",
        baseline_ensemble_id="ensemble-1",
        scenario_definition_id="scenario-1",
        scenario_parameter_changes=[_change()],
        origin_quality="derived",
        seed=7,
        physiology_version="m6-test-physiology-v1",
        ensemble_version="m5.5-backend-ensemble-v1",
        prior_version="m5-priors-v1",
        created_at=NOW,
    )


def _pair(sample_id: str, ef_delta: float, valid: bool = True) -> PairedTwinResult:
    return PairedTwinResult(
        sample_id=sample_id,
        baseline_twin_id=sample_id,
        scenario_twin_id=f"{sample_id}-scenario",
        baseline_state=_state(),
        scenario_state=_state(),
        delta_units={"ejection_fraction_pct": "percentage_points"} if valid else {},
        deltas={"ejection_fraction_pct": ef_delta} if valid else {},
        valid=valid,
        rejection_reasons=[] if valid else ["scenario invariant failed"],
    )


def _distribution(deltas: list[float]) -> EffectDistribution:
    return EffectDistribution(
        metric_id="ejection_fraction_pct",
        unit="percentage_points",
        deltas=deltas,
        mean_delta=sum(deltas) / len(deltas),
        median_delta=2.0,
        quantiles=EffectQuantiles(q05=1.1, q25=1.5, q75=2.5, q95=2.9),
        positive_count=2,
        neutral_count=0,
        negative_count=0,
    )


def test_definition_preserves_scenario_and_provenance_lineage() -> None:
    definition = ShadowTrialDefinition(
        id="trial-definition-1",
        origin_snapshot_id="snapshot-1",
        baseline_ensemble_id="ensemble-1",
        scenario=_scenario(),
        metrics=["ejection_fraction_pct", "stroke_volume_ml"],
        created_at=NOW,
        provenance=_provenance(),
    )

    assert definition.provenance.scenario_definition_id == definition.scenario.id
    assert definition.provenance.scenario_parameter_changes == definition.scenario.parameters


def test_effect_distribution_requires_explicit_units_and_categories() -> None:
    distribution = _distribution([1.0, 3.0])

    assert distribution.unit == "percentage_points"
    assert distribution.positive_count == 2
    assert distribution.neutral_count == 0
    assert distribution.negative_count == 0

    with pytest.raises(ValidationError, match="percentage_points"):
        EffectDistribution(
            metric_id="ejection_fraction_pct",
            unit="%",
            deltas=[1.0],
            mean_delta=1.0,
            median_delta=1.0,
            quantiles=EffectQuantiles(q05=1.0, q25=1.0, q75=1.0, q95=1.0),
            positive_count=1,
            neutral_count=0,
            negative_count=0,
        )


def test_result_requires_identity_preserving_pairs_and_matching_effects() -> None:
    pairs = [_pair("sample-1", 1.0), _pair("sample-2", 3.0)]
    result = ShadowTrialResult(
        id="trial-1",
        definition_id="trial-definition-1",
        baseline_ensemble_id="ensemble-1",
        requested_pairs=2,
        valid_pairs=2,
        invalid_pairs=0,
        paired_results=pairs,
        effect_distributions=[_distribution([1.0, 3.0])],
        provenance=_provenance(),
    )

    assert [pair.baseline_twin_id for pair in result.paired_results] == ["sample-1", "sample-2"]

    with pytest.raises(ValidationError, match="unique"):
        ShadowTrialResult(
            id="trial-1",
            definition_id="trial-definition-1",
            baseline_ensemble_id="ensemble-1",
            requested_pairs=2,
            valid_pairs=2,
            invalid_pairs=0,
            paired_results=[_pair("sample-1", 1.0), _pair("sample-1", 3.0)],
            effect_distributions=[_distribution([1.0, 3.0])],
            provenance=_provenance(),
        )
