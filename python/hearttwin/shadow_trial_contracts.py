"""Backend-only contracts for paired M6 Shadow Trials.

These models describe a deterministic virtual experiment.  A scenario is
applied to each baseline sample by identity; it is not an independently
sampled population.  The contracts carry descriptive simulation metadata and
must not be read as clinical treatment or outcome predictions.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from python.hearttwin.safety import DISCLAIMER
from python.hearttwin.schemas import CardiacTwinState


SHADOW_TRIAL_ENGINE_VERSION = "m6-shadow-trial-v1"
ShadowTrialMetricId = Literal[
    "ejection_fraction_pct",
    "stroke_volume_ml",
    "cardiac_output_l_min",
    "heart_rate_bpm",
    "map_mmhg",
    "edv_ml",
    "esv_ml",
    "pv_loop_area_index",
]
ShadowTrialMetricUnit = Literal["percentage_points", "mL", "L/min", "bpm", "mmHg", "index"]
ShadowTrialOriginQuality = Literal["observed", "derived", "interpolated", "synthetic"]

METRIC_UNITS: dict[ShadowTrialMetricId, ShadowTrialMetricUnit] = {
    "ejection_fraction_pct": "percentage_points",
    "stroke_volume_ml": "mL",
    "cardiac_output_l_min": "L/min",
    "heart_rate_bpm": "bpm",
    "map_mmhg": "mmHg",
    "edv_ml": "mL",
    "esv_ml": "mL",
    "pv_loop_area_index": "index",
}
DEFAULT_METRICS = ["ejection_fraction_pct", "stroke_volume_ml", "cardiac_output_l_min", "heart_rate_bpm", "map_mmhg", "edv_ml", "esv_ml"]
NEAR_ZERO_TOLERANCES = {
    "ejection_fraction_pct": 0.01,
    "stroke_volume_ml": 0.01,
    "cardiac_output_l_min": 0.001,
    "heart_rate_bpm": 0.01,
    "map_mmhg": 0.01,
    "edv_ml": 0.01,
    "esv_ml": 0.01,
    "pv_loop_area_index": 0.001,
}


def _is_finite(value: float) -> bool:
    return math.isfinite(value)


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


class ScenarioParameterChange(BaseModel):
    """One bounded, user-visible parameter change in a scenario."""

    model_config = ConfigDict(extra="forbid")

    parameter: str = Field(min_length=1)
    baseline: float | None = None
    value: float
    delta: float | None = None
    unit: str | None = None

    @model_validator(mode="after")
    def validate_values(self) -> "ScenarioParameterChange":
        if not _is_finite(self.value) or (self.baseline is not None and not _is_finite(self.baseline)):
            raise ValueError("scenario parameter values must be finite")
        if self.delta is not None and self.baseline is not None and not math.isclose(self.value - self.baseline, self.delta, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("scenario parameter delta must equal value minus baseline")
        return self


class ScenarioDefinition(BaseModel):
    """Serializable M4-compatible scenario description consumed by M6."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str | None = None
    origin_snapshot_id: str | None = None
    parameters: list[ScenarioParameterChange] = Field(default_factory=list)
    created_at: datetime | None = None

    @model_validator(mode="after")
    def unique_parameters(self) -> "ScenarioDefinition":
        parameter_ids = [item.parameter for item in self.parameters]
        if len(parameter_ids) != len(set(parameter_ids)):
            raise ValueError("scenario parameter IDs must be unique")
        return self


class ShadowTrialProvenance(BaseModel):
    """Lineage required to reproduce and audit a paired Shadow Trial."""

    model_config = ConfigDict(extra="forbid")

    origin_snapshot_id: str = Field(min_length=1)
    baseline_ensemble_id: str = Field(min_length=1)
    scenario_definition_id: str = Field(min_length=1)
    scenario_parameter_changes: list[ScenarioParameterChange] = Field(default_factory=list)
    origin_quality: ShadowTrialOriginQuality
    origin_provenance: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    seed: int
    physiology_version: str = Field(min_length=1)
    ensemble_version: str = Field(min_length=1)
    prior_version: str = Field(min_length=1)
    created_at: datetime | None = None
    assumptions: list[str] = Field(default_factory=list)
    provenance_schema_version: str = "m6-shadow-provenance-v1"
    shadow_trial_engine_version: str = SHADOW_TRIAL_ENGINE_VERSION
    effect_metrics_version: str = "m6-effect-metrics-v1"
    pairing_policy: str = "same baseline sample identity; no scenario resampling"
    scenario_definition_hash: str = ""

    @field_validator("seed")
    @classmethod
    def safe_seed(cls, value: int) -> int:
        if not -(2**53) < value < 2**53:
            raise ValueError("seed must be a safe integer")
        return value


class ShadowTrialDefinition(BaseModel):
    """Immutable definition of one paired counterfactual experiment."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    origin_snapshot_id: str = Field(min_length=1)
    baseline_ensemble_id: str = Field(min_length=1)
    scenario: ScenarioDefinition
    metrics: list[ShadowTrialMetricId] = Field(min_length=1)
    created_at: datetime
    provenance: ShadowTrialProvenance

    @model_validator(mode="after")
    def validate_lineage(self) -> "ShadowTrialDefinition":
        if len(self.metrics) != len(set(self.metrics)):
            raise ValueError("shadow trial metrics must be unique")
        if self.scenario.origin_snapshot_id != self.origin_snapshot_id:
            raise ValueError("scenario origin snapshot does not match trial definition")
        if self.provenance.origin_snapshot_id != self.origin_snapshot_id:
            raise ValueError("provenance origin snapshot does not match trial definition")
        if self.provenance.baseline_ensemble_id != self.baseline_ensemble_id:
            raise ValueError("provenance baseline ensemble does not match trial definition")
        if self.provenance.scenario_definition_id != self.scenario.id:
            raise ValueError("provenance scenario does not match trial definition")
        if self.provenance.scenario_parameter_changes != self.scenario.parameters:
            raise ValueError("provenance scenario parameters do not match scenario")
        return self


class ShadowTrialRequest(BaseModel):
    """Creation payload; the backend derives the immutable trial identity."""

    model_config = ConfigDict(extra="forbid")

    baseline_ensemble_id: str = Field(min_length=1)
    scenario: ScenarioDefinition
    metrics: list[ShadowTrialMetricId] = Field(default_factory=lambda: list(DEFAULT_METRICS))

    @model_validator(mode="after")
    def validate_metrics(self) -> "ShadowTrialRequest":
        if not self.metrics:
            raise ValueError("at least one effect metric is required")
        if len(self.metrics) != len(set(self.metrics)):
            raise ValueError("shadow trial metrics must be unique")
        return self


class PairedTwinResult(BaseModel):
    """Result for one baseline sample and its same-sample scenario twin."""

    model_config = ConfigDict(extra="forbid")

    sample_id: str = Field(min_length=1)
    baseline_twin_id: str = Field(min_length=1)
    scenario_twin_id: str = Field(min_length=1)
    baseline_state: CardiacTwinState
    scenario_state: CardiacTwinState
    baseline_parameters: dict[str, float] = Field(default_factory=dict)
    scenario_parameters: dict[str, float] = Field(default_factory=dict)
    parameters: dict[str, float] = Field(default_factory=dict)
    deltas: dict[ShadowTrialMetricId, float] = Field(default_factory=dict)
    delta_units: dict[str, str] = Field(default_factory=dict)
    valid: bool
    rejection_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pair(self) -> "PairedTwinResult":
        if self.baseline_twin_id != self.sample_id:
            raise ValueError("baseline twin ID must preserve the baseline sample ID")
        if self.scenario_twin_id == self.baseline_twin_id:
            raise ValueError("scenario twin ID must be distinct from baseline twin ID")
        if any(not _is_finite(value) for value in self.deltas.values()):
            raise ValueError("paired deltas must be finite")
        if set(self.delta_units) != set(self.deltas):
            raise ValueError("pair delta units must cover exactly the returned deltas")
        for metric_id, unit in self.delta_units.items():
            if METRIC_UNITS.get(metric_id) != unit:
                raise ValueError(f"{metric_id} has an invalid delta unit")
        if self.valid and self.rejection_reasons:
            raise ValueError("valid paired results cannot have rejection reasons")
        if not self.valid and not self.rejection_reasons:
            raise ValueError("invalid paired results must include rejection reasons")
        return self


class EffectQuantiles(BaseModel):
    """Fixed descriptive percentile keys for paired effects."""

    model_config = ConfigDict(extra="forbid")

    q05: float | None = None
    q25: float | None = None
    q75: float | None = None
    q95: float | None = None

    @field_validator("q05", "q25", "q75", "q95")
    @classmethod
    def finite(cls, value: float | None) -> float | None:
        if value is not None and not _is_finite(value):
            raise ValueError("effect quantiles must be finite")
        return value


class EffectDistribution(BaseModel):
    """Descriptive distribution of paired scenario-minus-baseline effects."""

    model_config = ConfigDict(extra="forbid")

    metric_id: ShadowTrialMetricId
    unit: ShadowTrialMetricUnit
    deltas: list[float] = Field(default_factory=list)
    mean_delta: float | None = None
    median_delta: float | None = None
    quantiles: EffectQuantiles
    positive_count: int = Field(ge=0)
    neutral_count: int = Field(ge=0)
    negative_count: int = Field(ge=0)
    neutral_tolerance: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def validate_distribution(self) -> "EffectDistribution":
        expected_unit = METRIC_UNITS[self.metric_id]
        if self.unit != expected_unit:
            raise ValueError(f"{self.metric_id} effects must use unit {expected_unit}")
        if any(not _is_finite(value) for value in self.deltas):
            raise ValueError("effect deltas must be finite")
        if not self.deltas:
            if any(value != 0 for value in (self.positive_count, self.neutral_count, self.negative_count)):
                raise ValueError("empty effect distributions must have zero category counts")
            if self.mean_delta is not None or self.median_delta is not None:
                raise ValueError("empty effect distributions cannot have summary values")
            if any(value is not None for value in self.quantiles.model_dump().values()):
                raise ValueError("empty effect distributions cannot have quantiles")
            return self
        if self.mean_delta is None or self.median_delta is None or not all(_is_finite(value) for value in (self.mean_delta, self.median_delta)):
            raise ValueError("effect summary values must be finite")
        if self.positive_count + self.neutral_count + self.negative_count != len(self.deltas):
            raise ValueError("effect category counts must equal delta count")
        expected_positive = sum(value > self.neutral_tolerance for value in self.deltas)
        expected_neutral = sum(abs(value) <= self.neutral_tolerance for value in self.deltas)
        expected_negative = sum(value < -self.neutral_tolerance for value in self.deltas)
        if (self.positive_count, self.neutral_count, self.negative_count) != (
            expected_positive,
            expected_neutral,
            expected_negative,
        ):
            raise ValueError("effect category counts do not match delta signs")
        if not math.isclose(self.mean_delta, sum(self.deltas) / len(self.deltas), rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("mean delta does not match deltas")
        if not math.isclose(self.median_delta, _quantile(self.deltas, 0.5), rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("median delta does not match deltas")
        expected_quantiles = {
            "q05": _quantile(self.deltas, 0.05),
            "q25": _quantile(self.deltas, 0.25),
            "q75": _quantile(self.deltas, 0.75),
            "q95": _quantile(self.deltas, 0.95),
        }
        for key, expected in expected_quantiles.items():
            if not math.isclose(getattr(self.quantiles, key), expected, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"{key} does not match deltas")
        return self


class ShadowTrialEffectsResponse(BaseModel):
    """Typed read projection for effect summaries."""

    model_config = ConfigDict(extra="forbid")

    trial_id: str = Field(min_length=1)
    definition_id: str = Field(min_length=1)
    baseline_ensemble_id: str = Field(min_length=1)
    requested_pairs: int = Field(ge=0)
    valid_pairs: int = Field(ge=0)
    invalid_pairs: int = Field(ge=0)
    effect_distributions: list[EffectDistribution] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    safety_disclaimer: str = DISCLAIMER

    @model_validator(mode="after")
    def validate_counts(self) -> "ShadowTrialEffectsResponse":
        if self.valid_pairs + self.invalid_pairs != self.requested_pairs:
            raise ValueError("shadow trial effect counts do not reconcile")
        if self.safety_disclaimer != DISCLAIMER:
            raise ValueError("shadow trial safety disclaimer must be canonical")
        return self


class ShadowTrialPairResponse(BaseModel):
    """Typed read projection for one paired result."""

    model_config = ConfigDict(extra="forbid")

    trial_id: str = Field(min_length=1)
    pair: PairedTwinResult
    safety_disclaimer: str = DISCLAIMER

    @field_validator("safety_disclaimer")
    @classmethod
    def canonical_disclaimer(cls, value: str) -> str:
        if value != DISCLAIMER:
            raise ValueError("shadow trial safety disclaimer must be canonical")
        return value


class ShadowTrialResult(BaseModel):
    """Complete result of one identity-preserving paired Shadow Trial."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    definition_id: str = Field(min_length=1)
    baseline_ensemble_id: str = Field(min_length=1)
    requested_pairs: int = Field(ge=0)
    valid_pairs: int = Field(ge=0)
    invalid_pairs: int = Field(ge=0)
    paired_results: list[PairedTwinResult] = Field(default_factory=list)
    effect_distributions: list[EffectDistribution] = Field(default_factory=list)
    provenance: ShadowTrialProvenance
    definition: ShadowTrialDefinition | None = None
    warnings: list[str] = Field(default_factory=list)
    status: Literal["complete", "failed"] = "complete"
    fingerprint: str = ""
    safety_disclaimer: str = DISCLAIMER

    @model_validator(mode="after")
    def validate_result(self) -> "ShadowTrialResult":
        if self.valid_pairs + self.invalid_pairs != self.requested_pairs:
            raise ValueError("shadow trial pair counts do not reconcile")
        if len(self.paired_results) != self.requested_pairs:
            raise ValueError("paired results do not match requested pair count")
        if sum(pair.valid for pair in self.paired_results) != self.valid_pairs:
            raise ValueError("valid pair count does not match paired results")
        expected_status = "complete" if self.valid_pairs > 0 else "failed"
        if self.status != expected_status:
            raise ValueError("shadow trial status must match whether valid pairs exist")
        if len({pair.sample_id for pair in self.paired_results}) != len(self.paired_results):
            raise ValueError("paired sample IDs must be unique")
        if self.provenance.baseline_ensemble_id != self.baseline_ensemble_id:
            raise ValueError("result provenance baseline ensemble does not match result")
        if self.safety_disclaimer != DISCLAIMER:
            raise ValueError("shadow trial safety disclaimer must be canonical")
        expected_metrics = {metric_id for pair in self.paired_results for metric_id in pair.deltas}
        distribution_metrics = {distribution.metric_id for distribution in self.effect_distributions}
        if self.valid_pairs > 0 and distribution_metrics != expected_metrics:
            raise ValueError("effect distributions must cover exactly the paired delta metrics")
        valid_pairs = [pair for pair in self.paired_results if pair.valid]
        for distribution in self.effect_distributions:
            paired_values = [pair.deltas[distribution.metric_id] for pair in valid_pairs if distribution.metric_id in pair.deltas]
            if len(paired_values) != self.valid_pairs or any(
                not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
                for actual, expected in zip(sorted(distribution.deltas), sorted(paired_values))
            ):
                raise ValueError(f"effect distribution {distribution.metric_id} does not match valid pairs")
        return self


__all__ = [
    "EffectDistribution",
    "EffectQuantiles",
    "METRIC_UNITS",
    "PairedTwinResult",
    "ScenarioDefinition",
    "ScenarioParameterChange",
    "ShadowTrialDefinition",
    "ShadowTrialMetricId",
    "ShadowTrialMetricUnit",
    "ShadowTrialOriginQuality",
    "ShadowTrialProvenance",
    "ShadowTrialResult",
    "ShadowTrialEffectsResponse",
    "ShadowTrialPairResponse",
    "ShadowTrialRequest",
    "DEFAULT_METRICS",
    "NEAR_ZERO_TOLERANCES",
    "SHADOW_TRIAL_ENGINE_VERSION",
]


def metric_unit(metric_id: str) -> str:
    try:
        return METRIC_UNITS[metric_id]
    except KeyError as exc:
        raise ValueError(f"unsupported shadow trial metric: {metric_id}") from exc
