"""Canonical paired Shadow Trial execution over a persisted M5.5 ensemble."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

from python.hearttwin.ensemble import (
    PARAMETER_BOUNDS,
    EnsembleResponse,
    EnsembleSample,
    _derived_state as canonical_derived_state,
    _evaluate as canonical_evaluate,
)
from python.hearttwin.safety import DISCLAIMER
from python.hearttwin.schemas import CardiacTwinState, MeasuredValue, ValueSource
from python.hearttwin.shadow_trial_contracts import (
    DEFAULT_METRICS,
    METRIC_UNITS,
    NEAR_ZERO_TOLERANCES,
    SHADOW_TRIAL_ENGINE_VERSION,
    PairedTwinResult,
    ScenarioDefinition,
    ScenarioParameterChange,
    ShadowTrialDefinition,
    ShadowTrialProvenance,
    ShadowTrialResult,
)
from python.hearttwin.shadow_trial_identity import scenario_sample_id
from python.hearttwin.shadow_trial_metrics import effect_distribution

TRIAL_ENGINE_VERSION = SHADOW_TRIAL_ENGINE_VERSION
SCENARIO_PHYSIOLOGY_VERSION = "m5.5-ensemble-projection-v1"
DEFAULT_EFFECT_METRICS = tuple(DEFAULT_METRICS)
EFFECT_METRIC_UNITS = dict(METRIC_UNITS)
EFFECT_METRIC_UNITS["pv_loop_area_index"] = "index"


def _validate_metrics(metrics: Sequence[str]) -> tuple[str, ...]:
    if not metrics:
        raise ValueError("at least one effect metric is required")
    if len(metrics) != len(set(metrics)):
        raise ValueError("effect metrics must be unique")
    unknown = [metric for metric in metrics if metric not in EFFECT_METRIC_UNITS]
    if unknown:
        raise ValueError(f"unsupported effect metric(s): {', '.join(unknown)}")
    return tuple(metrics)


def _read_value(state: CardiacTwinState, section: str, field: str) -> float | None:
    measured = getattr(getattr(state, section), field, None)
    value = getattr(measured, "value", None)
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None


def _read_metric(state: CardiacTwinState, metric_id: str, outputs: Mapping[str, float] | None = None) -> float | None:
    output_key = {"map_mmhg": "map", "edv_ml": "edv", "esv_ml": "esv"}.get(metric_id, metric_id)
    if outputs is not None and output_key in outputs:
        return float(outputs[output_key])
    locations = {
        "ejection_fraction_pct": ("measurements", "ejection_fraction_pct"),
        "stroke_volume_ml": ("measurements", "stroke_volume_ml"),
        "cardiac_output_l_min": ("measurements", "cardiac_output_l_min"),
        "heart_rate_bpm": ("measurements", "heart_rate_bpm"),
        "edv_ml": ("measurements", "edv_ml"),
        "esv_ml": ("measurements", "esv_ml"),
    }
    if metric_id in locations:
        return _read_value(state, *locations[metric_id])
    if metric_id == "map_mmhg":
        systolic = _read_value(state, "measurements", "systolic_bp_mmhg")
        diastolic = _read_value(state, "measurements", "diastolic_bp_mmhg")
        if systolic is not None and diastolic is not None and diastolic < systolic:
            return diastolic + (systolic - diastolic) / 3.0
    if metric_id == "pv_loop_area_index":
        return _read_value(state, "hemodynamics", "pv_loop_area_index")
    return None


def _derived(value: float, unit: str, method: str) -> MeasuredValue:
    return MeasuredValue(value=float(value), unit=unit, source=ValueSource.DERIVED, confidence=1.0, method=method, evidence="M6 paired canonical scenario projection")


def _validate_scenario(scenario: ScenarioDefinition) -> None:
    """Validate the declarative scenario before attempting any pair.

    A malformed scenario is a request error, not a population of invalid
    pairs. Pair-level invalidity is reserved for a rejected baseline member or
    a derived counterfactual that fails a sample-specific invariant.
    """
    expected_units = {
        "heart_rate_bpm": "bpm",
        "preload_index": "index",
        "afterload_index": "index",
        "contractility_index": "index",
        "systemic_vascular_resistance_index": "index",
    }
    for change in scenario.parameters:
        bounds = PARAMETER_BOUNDS.get(change.parameter)
        if bounds is None:
            raise ValueError(f"unsupported scenario parameter: {change.parameter}")
        if not math.isfinite(change.value) or not bounds[0] <= change.value <= bounds[1]:
            raise ValueError(
                f"{change.parameter}: scenario value must be within [{bounds[0]}, {bounds[1]}]"
            )
        expected_unit = expected_units[change.parameter]
        if change.unit is not None and change.unit != expected_unit:
            raise ValueError(f"{change.parameter}: expected unit {expected_unit}")


def _apply_scenario(sample: EnsembleSample, scenario: ScenarioDefinition) -> tuple[CardiacTwinState, dict[str, float]]:
    """Apply bounded scenario values through the existing Python evaluator."""
    if _read_value(sample.state, "measurements", "edv_ml") is None or _read_value(sample.state, "measurements", "esv_ml") is None:
        raise ValueError("baseline state must include EDV and ESV")
    if sample.projection_base is None:
        raise ValueError(
            "baseline ensemble sample lacks the persisted projection base; regenerate the M5.5 ensemble"
        )
    base = dict(sample.projection_base)
    target_parameters = dict(sample.parameters)
    for change in scenario.parameters:
        if change.parameter not in target_parameters:
            raise ValueError(f"baseline sample is missing scenario parameter: {change.parameter}")
        target_parameters[change.parameter] = change.value
    outputs = canonical_evaluate(base, target_parameters)
    if all(target_parameters[key] == sample.parameters[key] for key in PARAMETER_BOUNDS):
        # Preserve the persisted baseline exactly for an identity scenario;
        # recomputing from a projected state can introduce tiny drift.
        return sample.state.model_copy(deep=True), dict(sample.outputs)
    projected = canonical_derived_state(sample.state, outputs)
    projected.hemodynamics = projected.hemodynamics.model_copy(update={
        "preload_index": _derived(target_parameters["preload_index"], "index", "scenario preload input"),
        "afterload_index": _derived(target_parameters["afterload_index"], "index", "scenario afterload input"),
        "contractility_index": _derived(target_parameters["contractility_index"], "index", "scenario contractility input"),
        "systemic_vascular_resistance_index": _derived(target_parameters["systemic_vascular_resistance_index"], "index", "scenario SVR input"),
    })
    projected.electrophysiology = projected.electrophysiology.model_copy(update={
        "rr_interval_ms": _derived(60000.0 / target_parameters["heart_rate_bpm"], "ms", "RR = 60000 / HR"),
    })
    projected.warnings = [*projected.warnings, "Hypothetical M6 paired scenario; not clinical evidence or treatment advice."]
    return projected, outputs


def _trial_id(
    ensemble: EnsembleResponse,
    scenario: ScenarioDefinition,
    metrics: Sequence[str],
    tolerances: Mapping[str, float],
) -> tuple[str, str]:
    identity = {
        "baseline_ensemble_id": ensemble.id,
        "scenario": scenario.model_dump(mode="json"),
        "metrics": sorted(metrics),
        "neutral_tolerances": {metric: tolerances[metric] for metric in sorted(metrics)},
        "engine_version": TRIAL_ENGINE_VERSION,
        "physiology_version": SCENARIO_PHYSIOLOGY_VERSION,
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return f"shadow-trial-{digest[:12]}", digest


def _coerce_ensemble(value: EnsembleResponse | Mapping[str, Any]) -> EnsembleResponse:
    return value.model_copy(deep=True) if isinstance(value, EnsembleResponse) else EnsembleResponse.model_validate(value)


def run_shadow_trial(
    baseline_ensemble: EnsembleResponse | Mapping[str, Any],
    scenario: ScenarioDefinition | Mapping[str, Any],
    *,
    metrics: Sequence[str] | None = None,
    neutral_tolerance: float | None = None,
) -> ShadowTrialResult:
    """Run a deterministic same-sample paired trial without resampling."""
    ensemble = _coerce_ensemble(baseline_ensemble)
    scenario_model = scenario if isinstance(scenario, ScenarioDefinition) else ScenarioDefinition.model_validate(scenario)
    selected_metrics = tuple(sorted(_validate_metrics(metrics or DEFAULT_EFFECT_METRICS)))
    # Parameter declaration order is presentation metadata, not experiment
    # identity. Canonicalize it so equivalent definitions hash and persist
    # identically.
    scenario_model = scenario_model.model_copy(
        update={"parameters": sorted(scenario_model.parameters, key=lambda item: item.parameter)},
    )
    # Parameter declaration order is presentation metadata, not experiment
    # identity. Canonicalize it so semantically identical requests replay to
    # the same immutable result and fingerprint.
    scenario_model = scenario_model.model_copy(
        update={"parameters": sorted(scenario_model.parameters, key=lambda item: item.parameter)},
    )
    if scenario_model.origin_snapshot_id and scenario_model.origin_snapshot_id != ensemble.origin_snapshot_id:
        raise ValueError("scenario origin snapshot does not match baseline ensemble")
    _validate_scenario(scenario_model)
    tolerances = {metric: neutral_tolerance if neutral_tolerance is not None else NEAR_ZERO_TOLERANCES.get(metric, 1e-9) for metric in selected_metrics}
    trial_id, fingerprint = _trial_id(ensemble, scenario_model, selected_metrics, tolerances)
    pairs: list[PairedTwinResult] = []
    for sample in sorted(ensemble.samples, key=lambda item: (item.id, item.index)):
        baseline_state = sample.state.model_copy(deep=True)
        scenario_state = baseline_state.model_copy(deep=True)
        parameters = dict(sample.parameters)
        scenario_parameters = dict(parameters)
        reasons = [f"baseline sample rejected: {reason}" for reason in sample.rejection_reasons] if not sample.valid else []
        deltas: dict[str, float] = {}
        if not reasons:
            try:
                scenario_state, scenario_outputs = _apply_scenario(sample, scenario_model)
                # The persisted sample outputs are the baseline authority. Do
                # not re-evaluate them from a projected state: doing so can
                # apply the sampled parameters twice and break exact pairing.
                baseline_outputs = sample.outputs
                for metric in selected_metrics:
                    baseline_value = _read_metric(baseline_state, metric, baseline_outputs)
                    scenario_value = _read_metric(scenario_state, metric, scenario_outputs)
                    if baseline_value is None or scenario_value is None:
                        reasons.append(f"{metric}: metric is unavailable in baseline or scenario state")
                    else:
                        delta = scenario_value - baseline_value
                        # Preserve the raw paired delta. Near-zero handling is
                        # a descriptive classification rule, not rounding.
                        deltas[metric] = delta
                for change in scenario_model.parameters:
                    scenario_parameters[change.parameter] = change.value
            except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
                reasons.append(str(exc))
        if reasons:
            # A pair is atomic for effect reporting: retain the state and
            # rejection reasons, but never expose a partial metric vector as
            # if it were a usable paired outcome.
            deltas = {}
        pairs.append(PairedTwinResult(
            sample_id=sample.id,
            baseline_twin_id=sample.id,
            scenario_twin_id=scenario_sample_id(trial_id, sample.id),
            baseline_state=baseline_state,
            scenario_state=scenario_state,
            baseline_parameters=parameters,
            scenario_parameters=scenario_parameters,
            parameters=parameters,
            deltas=deltas,
            delta_units={metric: EFFECT_METRIC_UNITS[metric] for metric in deltas},
            valid=not reasons,
            rejection_reasons=reasons,
        ))
    valid_pairs = [pair for pair in pairs if pair.valid]
    distributions = [
        effect_distribution(
            metric,
            [pair.deltas[metric] for pair in valid_pairs],
            neutral_tolerance=tolerances[metric],
        )
        for metric in selected_metrics
    ]
    created_at = scenario_model.created_at or ensemble.provenance.created_at
    provenance = ShadowTrialProvenance(
        origin_snapshot_id=ensemble.origin_snapshot_id,
        baseline_ensemble_id=ensemble.id,
        scenario_definition_id=scenario_model.id,
        scenario_parameter_changes=list(scenario_model.parameters),
        origin_quality=ensemble.provenance.origin_quality,
        origin_provenance=list(ensemble.provenance.origin_provenance),
        evidence_ids=list(ensemble.provenance.evidence_ids),
        seed=ensemble.seed,
        physiology_version=ensemble.provenance.physiology_version,
        ensemble_version=ensemble.provenance.distribution_config_version,
        prior_version=ensemble.provenance.prior_version,
        created_at=created_at,
        assumptions=[
            "Each scenario twin reuses the corresponding baseline parameters; no second population is sampled.",
            "Scenario values are absolute bounded targets; optional baseline and delta fields are descriptive origin metadata.",
            "Effect percentiles summarize valid paired deterministic simulations and are not probabilities or confidence intervals.",
            "Scenario label and description are inert display metadata and are not sent to an agent or used as numerical input.",
        ],
        scenario_definition_hash=fingerprint,
    )
    scenario_for_definition = scenario_model
    if scenario_for_definition.origin_snapshot_id is None:
        scenario_for_definition = scenario_for_definition.model_copy(
            update={"origin_snapshot_id": ensemble.origin_snapshot_id},
        )
    definition = ShadowTrialDefinition(
        id=scenario_model.id,
        origin_snapshot_id=ensemble.origin_snapshot_id,
        baseline_ensemble_id=ensemble.id,
        scenario=scenario_for_definition,
        metrics=list(selected_metrics),
        created_at=created_at,
        provenance=provenance,
    )
    warnings = [
        "Hypothetical paired simulation only; not diagnosis, treatment advice, or clinical efficacy evidence.",
        "Effect distributions describe simulated metric direction only; sign does not imply clinical value.",
    ]
    if ensemble.provenance.origin_quality == "synthetic":
        warnings.append("Baseline ensemble origin is synthetic replay data; it is not patient evidence.")
    if len(valid_pairs) != len(pairs):
        warnings.append(f"{len(pairs) - len(valid_pairs)} paired twin(s) were invalid and retained with rejection reasons.")
    if not valid_pairs:
        warnings.append("No valid paired outcomes were available for effect distributions.")
    return ShadowTrialResult(
        id=trial_id,
        definition_id=scenario_model.id,
        baseline_ensemble_id=ensemble.id,
        requested_pairs=len(pairs),
        valid_pairs=len(valid_pairs),
        invalid_pairs=len(pairs) - len(valid_pairs),
        paired_results=pairs,
        effect_distributions=distributions,
        provenance=provenance,
        definition=definition,
        warnings=warnings,
        status="complete" if valid_pairs else "failed",
        fingerprint=fingerprint,
        safety_disclaimer=DISCLAIMER,
    )


execute_shadow_trial = run_shadow_trial
run_paired_shadow_trial = run_shadow_trial

__all__ = [
    "DEFAULT_EFFECT_METRICS", "EFFECT_METRIC_UNITS", "ScenarioDefinition",
    "ScenarioParameterChange", "run_shadow_trial", "execute_shadow_trial",
    "run_paired_shadow_trial", "TRIAL_ENGINE_VERSION",
]
