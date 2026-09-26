"""Seeded plausible-twin ensembles over the deterministic cardiac formulas.

This module deliberately samples input proxies and then evaluates deterministic
physiology. It never adds noise directly to an output metric and never labels a
simulation percentile as a clinical confidence interval.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from python.hearttwin.safety import DISCLAIMER
from python.hearttwin.schemas import CardiacTwinState, MeasuredValue, ValueSource

PARAMETER_BOUNDS: dict[str, tuple[float, float]] = {
    "heart_rate_bpm": (30.0, 200.0),
    "preload_index": (0.0, 1.5),
    "afterload_index": (0.0, 2.0),
    "contractility_index": (0.0, 1.5),
    "systemic_vascular_resistance_index": (0.0, 2.0),
}


class EnsembleDistributionRequest(BaseModel):
    parameter_id: str
    family: Literal["fixed", "normal", "lognormal", "uniform", "empirical"]
    parameters: dict[str, float | list[float]]
    bounds: dict[str, float]
    source: Literal["measurement", "derived", "population_prior", "expert_prior", "scenario"]
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1)
    version: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_distribution(self) -> EnsembleDistributionRequest:
        if self.parameter_id not in PARAMETER_BOUNDS:
            raise ValueError(f"unknown ensemble parameter: {self.parameter_id}")
        low = self.bounds.get("min")
        high = self.bounds.get("max")
        if low is None or high is None or not math.isfinite(low) or not math.isfinite(high) or low > high:
            raise ValueError(f"{self.parameter_id}: invalid bounds")
        allowed_low, allowed_high = PARAMETER_BOUNDS[self.parameter_id]
        if low < allowed_low or high > allowed_high:
            raise ValueError(f"{self.parameter_id}: bounds exceed deterministic model bounds")
        if self.family == "fixed":
            value = self.parameters.get("value")
            if not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"{self.parameter_id}: invalid fixed value")
        elif self.family in {"normal", "lognormal"}:
            mean = self.parameters.get("mean")
            sd = self.parameters.get("sd")
            if not isinstance(mean, (int, float)) or not math.isfinite(mean) or not low <= mean <= high:
                raise ValueError(f"{self.parameter_id}: invalid mean")
            if not isinstance(sd, (int, float)) or not math.isfinite(sd) or sd <= 0:
                raise ValueError(f"{self.parameter_id}: standard deviation must be positive")
            if self.family == "lognormal" and mean <= 0:
                raise ValueError(f"{self.parameter_id}: lognormal mean must be positive")
        elif self.family == "uniform":
            minimum = self.parameters.get("min")
            maximum = self.parameters.get("max")
            if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)) or not low <= minimum <= maximum <= high:
                raise ValueError(f"{self.parameter_id}: invalid uniform range")
        else:
            values = self.parameters.get("values")
            if not isinstance(values, list) or not values or any(not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high for value in values):
                raise ValueError(f"{self.parameter_id}: invalid empirical values")
        return self


class EnsembleRequest(BaseModel):
    origin_snapshot_id: str = Field(min_length=1)
    state: CardiacTwinState
    seed: int
    sample_count: int = Field(ge=1, le=1000)
    distributions: list[EnsembleDistributionRequest]
    physiology_version: str = "m5.5-ensemble-projection-v1"
    distribution_config_version: str = "m5.5-backend-ensemble-v1"
    prior_version: str = "m5-priors-v1"
    origin_quality: Literal["observed", "derived", "interpolated", "synthetic"]
    parent_scenario_id: str | None = None
    origin_provenance: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("seed")
    @classmethod
    def safe_seed(cls, value: int) -> int:
        if not -(2**53) < value < 2**53:
            raise ValueError("seed must be a safe integer")
        return value

    @model_validator(mode="after")
    def unique_parameters(self) -> EnsembleRequest:
        ids = [item.parameter_id for item in self.distributions]
        if len(ids) != len(set(ids)):
            raise ValueError("distribution parameter IDs must be unique")
        if set(ids) != set(PARAMETER_BOUNDS):
            raise ValueError("one distribution is required for each deterministic parameter")
        if self.origin_quality == "observed" and any(
            item.get("source") == "synthetic_replay" or "replay" in str(item.get("note", "")).lower()
            for item in self.origin_provenance
        ):
            raise ValueError("synthetic replay provenance cannot be labeled observed")
        return self


# ---------------------------------------------------------------------------
# Canonical response contract
# ---------------------------------------------------------------------------


EnsembleMetricId = Literal[
    "ejection_fraction_pct",
    "stroke_volume_ml",
    "cardiac_output_l_min",
    "heart_rate_bpm",
]


class EnsembleQuantiles(BaseModel):
    """Fixed percentile keys used by every metric distribution."""

    model_config = ConfigDict(extra="forbid")

    q05: float
    q25: float
    q75: float
    q95: float


class EnsembleMetricDistribution(BaseModel):
    """Descriptive statistics for one canonical ensemble output metric."""

    model_config = ConfigDict(extra="forbid")

    metric_id: EnsembleMetricId
    unit: str = Field(min_length=1)
    samples: list[float] = Field(min_length=1)
    mean: float
    median: float
    variance: float = Field(ge=0.0)
    standard_deviation: float = Field(ge=0.0)
    quantiles: EnsembleQuantiles
    min: float
    max: float

    @model_validator(mode="after")
    def validate_summary(self) -> "EnsembleMetricDistribution":
        if self.min > self.max:
            raise ValueError("metric distribution min must not exceed max")
        if len(self.samples) == 0:
            raise ValueError("metric distribution requires at least one sample")
        if any(not math.isfinite(value) for value in self.samples):
            raise ValueError("metric distribution samples must be finite")
        if any(not math.isfinite(value) for value in (
            self.mean,
            self.median,
            self.variance,
            self.standard_deviation,
            self.min,
            self.max,
            self.quantiles.q05,
            self.quantiles.q25,
            self.quantiles.q75,
            self.quantiles.q95,
        )):
            raise ValueError("metric distribution statistics must be finite")
        ordered_quantiles = [
            self.min,
            self.quantiles.q05,
            self.quantiles.q25,
            self.median,
            self.quantiles.q75,
            self.quantiles.q95,
            self.max,
        ]
        if any(left > right for left, right in zip(ordered_quantiles, ordered_quantiles[1:])):
            raise ValueError("metric distribution quantiles must be ordered")
        return self


class EnsembleSample(BaseModel):
    """One sampled input proxy and its deterministic physiology result."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    index: int = Field(ge=0)
    seed: int
    origin_snapshot_id: str = Field(min_length=1)
    origin_quality: Literal["observed", "derived", "interpolated", "synthetic"]
    parameters: dict[str, float]
    outputs: dict[str, float]
    state: CardiacTwinState
    valid: bool
    rejection_reasons: list[str]

    @model_validator(mode="after")
    def validate_sample(self) -> "EnsembleSample":
        if any(not math.isfinite(value) for value in self.parameters.values()):
            raise ValueError("sample parameters must be finite")
        if any(not math.isfinite(value) for value in self.outputs.values()):
            raise ValueError("sample outputs must be finite")
        if self.valid and self.rejection_reasons:
            raise ValueError("valid samples cannot have rejection reasons")
        if not self.valid and not self.rejection_reasons:
            raise ValueError("rejected samples must include rejection reasons")
        return self


class EnsembleProvenance(BaseModel):
    """Lineage and model-version metadata carried with every response."""

    model_config = ConfigDict(extra="forbid")

    origin_snapshot_id: str = Field(min_length=1)
    origin_timestamp: datetime
    origin_quality: Literal["observed", "derived", "interpolated", "synthetic"]
    origin_provenance: list[dict[str, Any]]
    parent_scenario_id: str | None = None
    evidence_ids: list[str]
    seed: int
    physiology_version: str = Field(min_length=1)
    distribution_config_version: str = Field(min_length=1)
    prior_version: str = Field(min_length=1)
    created_at: datetime
    assumptions: list[str]


class EnsembleResponse(BaseModel):
    """Stable, machine-readable response contract for plausible twin runs."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    origin_snapshot_id: str = Field(min_length=1)
    seed: int
    requested_sample_count: int = Field(ge=1, le=1000)
    accepted_sample_count: int = Field(ge=1)
    rejected_sample_count: int = Field(ge=0)
    samples: list[EnsembleSample] = Field(min_length=1)
    distributions: list[EnsembleMetricDistribution] = Field(min_length=1)
    parameter_distributions: list[EnsembleDistributionRequest] = Field(min_length=1)
    provenance: EnsembleProvenance
    warnings: list[str]
    safety_disclaimer: str = Field(min_length=1)
    representative_sample_ids: dict[str, str] = Field(min_length=3)

    @model_validator(mode="after")
    def validate_counts_and_lineage(self) -> "EnsembleResponse":
        if self.accepted_sample_count + self.rejected_sample_count != self.requested_sample_count:
            raise ValueError("ensemble sample counts do not reconcile")
        if len(self.samples) != self.requested_sample_count:
            raise ValueError("ensemble samples do not match requested sample count")
        if sum(sample.valid for sample in self.samples) != self.accepted_sample_count:
            raise ValueError("accepted sample count does not match sample validity")
        if self.provenance.origin_snapshot_id != self.origin_snapshot_id:
            raise ValueError("provenance origin snapshot does not match response")
        if self.provenance.seed != self.seed:
            raise ValueError("provenance seed does not match response")
        if self.provenance.origin_quality != self.samples[0].origin_quality:
            raise ValueError("provenance origin quality does not match samples")
        if any(sample.origin_snapshot_id != self.origin_snapshot_id for sample in self.samples):
            raise ValueError("sample origin snapshot does not match response")
        if any(sample.seed != self.seed for sample in self.samples):
            raise ValueError("sample seed does not match response")
        if len({sample.id for sample in self.samples}) != len(self.samples):
            raise ValueError("ensemble sample IDs must be unique")
        if {sample.index for sample in self.samples} != set(range(self.requested_sample_count)):
            raise ValueError("ensemble sample indices must cover the requested range")
        if any(set(sample.parameters) != set(PARAMETER_BOUNDS) for sample in self.samples):
            raise ValueError("ensemble samples must contain every deterministic parameter")
        if self.safety_disclaimer != DISCLAIMER:
            raise ValueError("ensemble safety disclaimer must use the canonical disclaimer")
        if set(self.representative_sample_ids) != {"low", "median", "high"}:
            raise ValueError("representative sample IDs must include low, median, and high")
        valid_sample_ids = {sample.id for sample in self.samples if sample.valid}
        if any(sample_id not in valid_sample_ids for sample_id in self.representative_sample_ids.values()):
            raise ValueError("representative sample ID is not present in ensemble samples")
        expected_units = {
            "ejection_fraction_pct": "%",
            "stroke_volume_ml": "mL",
            "cardiac_output_l_min": "L/min",
            "heart_rate_bpm": "bpm",
        }
        if len({distribution.metric_id for distribution in self.distributions}) != len(self.distributions):
            raise ValueError("ensemble distributions must not contain duplicate metrics")
        distributions_by_metric = {distribution.metric_id: distribution for distribution in self.distributions}
        if set(distributions_by_metric) != set(expected_units):
            raise ValueError("ensemble distributions must contain the canonical output metrics")
        if any(distributions_by_metric[metric_id].unit != unit for metric_id, unit in expected_units.items()):
            raise ValueError("ensemble distribution units do not match canonical output metrics")
        accepted = [sample for sample in self.samples if sample.valid]
        for metric_id, distribution in distributions_by_metric.items():
            try:
                values = sorted(float(sample.outputs[metric_id]) for sample in accepted)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"accepted samples are missing metric {metric_id}") from exc
            if len(values) != len(distribution.samples) or any(
                not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
                for actual, expected in zip(values, distribution.samples)
            ):
                raise ValueError(f"distribution samples do not match accepted {metric_id} outputs")
            expected_summary = _summary(metric_id, values, distribution.unit)
            for key in ("mean", "median", "variance", "standard_deviation", "min", "max"):
                if not math.isclose(getattr(distribution, key), expected_summary[key], rel_tol=1e-12, abs_tol=1e-12):
                    raise ValueError(f"distribution {metric_id} {key} does not match accepted samples")
            for key, expected in expected_summary["quantiles"].items():
                if not math.isclose(getattr(distribution.quantiles, key), expected, rel_tol=1e-12, abs_tol=1e-12):
                    raise ValueError(f"distribution {metric_id} {key} does not match accepted samples")
        return self


def _value(measurements: Any, name: str, fallback: float) -> float:
    entry = getattr(measurements, name, None)
    value = getattr(entry, "value", None)
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else fallback


def _baseline(state: CardiacTwinState) -> dict[str, float]:
    hr = min(220.0, max(30.0, _value(state.measurements, "heart_rate_bpm", 70.0)))
    edv = min(400.0, max(40.0, _value(state.measurements, "edv_ml", 130.0)))
    ef = min(90.0, max(5.0, _value(state.measurements, "ejection_fraction_pct", 60.0)))
    esv = min(edv - 1.0, max(5.0, _value(state.measurements, "esv_ml", edv * (1 - ef / 100))))
    return {
        "heart_rate_bpm": hr,
        "preload_index": _value(state.hemodynamics, "preload_index", 1.0),
        "afterload_index": _value(state.hemodynamics, "afterload_index", 1.0),
        "contractility_index": _value(state.hemodynamics, "contractility_index", 1.0),
        "systemic_vascular_resistance_index": _value(state.hemodynamics, "systemic_vascular_resistance_index", 1.0),
        "edv": edv,
        "esv": esv,
        "map": (_value(state.measurements, "diastolic_bp_mmhg", 80.0) + max(0.0, _value(state.measurements, "systolic_bp_mmhg", 120.0) - _value(state.measurements, "diastolic_bp_mmhg", 80.0)) / 3),
    }


def _sample(distribution: EnsembleDistributionRequest, rng: random.Random) -> float:
    parameters = distribution.parameters
    if distribution.family == "fixed":
        return float(parameters["value"])
    if distribution.family == "normal":
        return rng.gauss(float(parameters["mean"]), float(parameters["sd"]))
    if distribution.family == "lognormal":
        return rng.lognormvariate(math.log(float(parameters["mean"])), float(parameters["sd"]))
    if distribution.family == "uniform":
        return rng.uniform(float(parameters["min"]), float(parameters["max"]))
    values = parameters["values"]
    if not isinstance(values, list):
        raise TypeError("empirical values must be a list")
    return float(rng.choice(values))


def _evaluate(base: dict[str, float], parameters: dict[str, float]) -> dict[str, float]:
    preload_factor = parameters["preload_index"] / base["preload_index"] if base["preload_index"] > 0 else 1.0
    afterload_factor = parameters["afterload_index"] / base["afterload_index"] if base["afterload_index"] > 0 else 1.0
    contractility_factor = parameters["contractility_index"] / base["contractility_index"] if base["contractility_index"] > 0 else 1.0
    svr_factor = parameters["systemic_vascular_resistance_index"] / base["systemic_vascular_resistance_index"] if base["systemic_vascular_resistance_index"] > 0 else 1.0
    edv = min(400.0, max(40.0, base["edv"] * preload_factor))
    esv = min(edv - 1.0, max(5.0, base["esv"] + base["edv"] * 0.25 * (afterload_factor - 1) - base["esv"] * 0.5 * (contractility_factor - 1)))
    sv = edv - esv
    co = parameters["heart_rate_bpm"] * sv / 1000
    ef = sv / edv * 100
    return {"ejection_fraction_pct": ef, "stroke_volume_ml": sv, "cardiac_output_l_min": co, "heart_rate_bpm": parameters["heart_rate_bpm"], "edv": edv, "esv": esv, "map": max(20.0, base["map"] * (1 + 0.35 * (svr_factor - 1) + 0.1 * (co / max(0.1, base["heart_rate_bpm"] * (base["edv"] - base["esv"]) / 1000) - 1)))}


def _derived_state(state: CardiacTwinState, outputs: dict[str, float]) -> CardiacTwinState:
    """Project canonical scalar outputs into the typed state consumed by the UI."""
    projected = state.model_copy(deep=True)
    for field, output_key, unit in (
        ("heart_rate_bpm", "heart_rate_bpm", "bpm"),
        ("edv_ml", "edv", "mL"),
        ("esv_ml", "esv", "mL"),
        ("ejection_fraction_pct", "ejection_fraction_pct", "%"),
        ("stroke_volume_ml", "stroke_volume_ml", "mL"),
        ("cardiac_output_l_min", "cardiac_output_l_min", "L/min"),
    ):
        setattr(projected.measurements, field, MeasuredValue(
            value=outputs[output_key],
            unit=unit,
            source=ValueSource.DERIVED,
            confidence=1.0,
            method="m5.5 deterministic ensemble projection",
        ))
    return projected


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _summary(metric_id: str, values: list[float], unit: str) -> dict[str, Any]:
    ordered = sorted(values)
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return {"metric_id": metric_id, "unit": unit, "samples": ordered, "mean": mean, "median": _quantile(values, 0.5), "variance": variance, "standard_deviation": math.sqrt(variance), "quantiles": {"q05": _quantile(values, 0.05), "q25": _quantile(values, 0.25), "q75": _quantile(values, 0.75), "q95": _quantile(values, 0.95)}, "min": ordered[0], "max": ordered[-1]}


def run_ensemble(request: EnsembleRequest) -> dict[str, Any]:
    base = _baseline(request.state)
    rng = random.Random(request.seed)
    identity = json.dumps({"origin": request.origin_snapshot_id, "origin_quality": request.origin_quality, "origin_timestamp": request.state.created_at.isoformat(), "seed": request.seed, "count": request.sample_count, "versions": {"physiology": request.physiology_version, "distribution": request.distribution_config_version, "prior": request.prior_version}, "parent_scenario_id": request.parent_scenario_id, "distributions": [item.model_dump(mode="json") for item in request.distributions]}, sort_keys=True).encode()
    ensemble_id = f"ensemble-{hashlib.sha256(identity).hexdigest()[:12]}"
    samples: list[dict[str, Any]] = []
    for index in range(request.sample_count):
        parameters = {distribution.parameter_id: _sample(distribution, rng) for distribution in request.distributions}
        reasons = [f"{name}: sampled value outside declared bounds" for name, value in parameters.items() if not request.distributions[[item.parameter_id for item in request.distributions].index(name)].bounds["min"] <= value <= request.distributions[[item.parameter_id for item in request.distributions].index(name)].bounds["max"]]
        outputs: dict[str, float] = {}
        if not reasons:
            outputs = _evaluate(base, parameters)
            if outputs["edv"] <= outputs["esv"] or outputs["stroke_volume_ml"] <= 0 or not 0 <= outputs["ejection_fraction_pct"] <= 100:
                reasons.append("physiological invariant failed")
        state = _derived_state(request.state, outputs) if not reasons else request.state
        sample = {"id": f"{ensemble_id}-sample-{index}", "index": index, "seed": request.seed, "origin_snapshot_id": request.origin_snapshot_id, "origin_quality": request.origin_quality, "parameters": parameters, "outputs": outputs, "state": state, "valid": not reasons, "rejection_reasons": reasons}
        samples.append(sample)
    accepted = [sample for sample in samples if sample["valid"]]
    if not accepted:
        raise ValueError("no valid plausible twins were accepted")
    metrics = [("ejection_fraction_pct", "%"), ("stroke_volume_ml", "mL"), ("cardiac_output_l_min", "L/min"), ("heart_rate_bpm", "bpm")]
    distributions = [_summary(metric, [sample["outputs"][metric] for sample in accepted], unit) for metric, unit in metrics]
    ef_median = next(item["median"] for item in distributions if item["metric_id"] == "ejection_fraction_pct")
    ordered_by_ef = sorted(accepted, key=lambda sample: sample["outputs"]["ejection_fraction_pct"])
    median_sample = min(accepted, key=lambda sample: abs(sample["outputs"]["ejection_fraction_pct"] - ef_median))
    provenance = {"origin_snapshot_id": request.origin_snapshot_id, "origin_timestamp": request.state.created_at.isoformat(), "origin_quality": request.origin_quality, "origin_provenance": request.origin_provenance, "parent_scenario_id": request.parent_scenario_id, "evidence_ids": sorted(set(request.evidence_ids + [evidence_id for item in request.distributions for evidence_id in item.evidence_ids])), "seed": request.seed, "physiology_version": request.physiology_version, "distribution_config_version": request.distribution_config_version, "prior_version": request.prior_version, "created_at": request.state.created_at.isoformat(), "assumptions": ["Input proxies are sampled independently because no validated joint correlation model is available.", "Percentiles summarize accepted deterministic simulations and are not clinical confidence intervals."]}
    response = EnsembleResponse.model_validate({
        "id": ensemble_id,
        "origin_snapshot_id": request.origin_snapshot_id,
        "seed": request.seed,
        "requested_sample_count": request.sample_count,
        "accepted_sample_count": len(accepted),
        "rejected_sample_count": len(samples) - len(accepted),
        "samples": samples,
        "distributions": distributions,
        "parameter_distributions": [item.model_dump(mode="json") for item in request.distributions],
        "provenance": provenance,
        "warnings": [
            "Educational simulation only; not diagnosis or treatment advice.",
            *( [f"{len(samples) - len(accepted)} sampled twin(s) were rejected by validity checks."] if len(samples) != len(accepted) else [] ),
            *( ["Only one accepted simulation; percentile range is descriptive and degenerate."] if len(accepted) == 1 else [] ),
        ],
        "safety_disclaimer": DISCLAIMER,
        "representative_sample_ids": {
            "low": ordered_by_ef[0]["id"],
            "median": median_sample["id"],
            "high": ordered_by_ef[-1]["id"],
        },
    })
    # Keep the existing mapping return type until the API route adopts
    # EnsembleResponse as its response_model. Validation above ensures every
    # route currently consuming this mapping sees the canonical contract.
    return response.model_dump(mode="json")
