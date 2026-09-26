"""Local sensitivity of a fixed M6 paired Shadow Trial effect."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from python.hearttwin.ensemble import PARAMETER_BOUNDS, EnsembleResponse, _evaluate
from python.hearttwin.shadow_trial_contracts import ScenarioDefinition

from .contracts import ParameterSensitivity, SensitivityProvenance
from .perturbations import PerturbationPolicy


def _key(metric_id: str) -> str:
    return {"map_mmhg": "map", "edv_ml": "edv", "esv_ml": "esv"}.get(metric_id, metric_id)


def _metric(outputs: Mapping[str, float], metric_id: str) -> float:
    value = outputs.get(_key(metric_id))
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"metric is unavailable: {metric_id}")
    return float(value)


def _effect(base: Mapping[str, float], baseline: Mapping[str, float], scenario: ScenarioDefinition, metric_id: str) -> float:
    scenario_parameters = dict(baseline)
    for change in scenario.parameters:
        scenario_parameters[change.parameter] = change.value
    return _metric(_evaluate(dict(base), scenario_parameters), metric_id) - _metric(
        _evaluate(dict(base), dict(baseline)), metric_id
    )


def run_effect_sensitivity(
    baseline_ensemble: EnsembleResponse | Mapping[str, Any],
    scenario: ScenarioDefinition | Mapping[str, Any],
    *,
    parameter_id: str,
    metric_id: str,
    shadow_trial_id: str | None = None,
) -> list[ParameterSensitivity]:
    """Return per-sample local derivatives of the M6 effect.

    Scenario parameter values are absolute fixed targets. If the perturbed
    parameter is part of the scenario, the target stays fixed while the
    baseline varies; otherwise both paired states receive the same baseline
    perturbation. This preserves M6 same-sample pairing and does not imply a
    causal or clinical effect.
    """

    ensemble = baseline_ensemble if isinstance(baseline_ensemble, EnsembleResponse) else EnsembleResponse.model_validate(baseline_ensemble)
    scenario_model = scenario if isinstance(scenario, ScenarioDefinition) else ScenarioDefinition.model_validate(scenario)
    if parameter_id not in PARAMETER_BOUNDS:
        raise ValueError(f"unknown parameter: {parameter_id}")
    policy = PerturbationPolicy(parameter_id, step=0.05)
    records: list[ParameterSensitivity] = []
    for sample in sorted(ensemble.samples, key=lambda item: (item.id, item.index)):
        if not sample.valid or sample.projection_base is None:
            continue
        baseline_parameters = dict(sample.parameters)
        baseline_effect = _effect(sample.projection_base, baseline_parameters, scenario_model, metric_id)
        points = policy.points(baseline_parameters[parameter_id])
        def evaluate_at(
            value: float,
            *,
            sample_base: Mapping[str, float] = sample.projection_base,
            sample_parameters: Mapping[str, float] = baseline_parameters,
            selected_parameter: str = parameter_id,
        ) -> float:
            perturbed = dict(sample_parameters)
            perturbed[selected_parameter] = value
            # _effect applies declared scenario values after this baseline
            # vector, so scenario parameters remain fixed while all other
            # paired values vary with the same sample.
            return _effect(sample_base, perturbed, scenario_model, metric_id)

        lower_output = evaluate_at(points.lower) if points.lower is not None else None
        upper_output = evaluate_at(points.upper) if points.upper is not None else None
        if points.method == "central":
            derivative = (upper_output - lower_output) / (2.0 * points.step)
        elif points.method == "forward":
            derivative = (upper_output - baseline_effect) / points.step
        elif points.method == "backward":
            derivative = (baseline_effect - lower_output) / points.step
        else:
            continue
        records.append(
            ParameterSensitivity(
                parameter_id=parameter_id,
                metric_id=metric_id,
                method="finite_difference",
                sensitivity=derivative,
                baseline_value=baseline_effect,
                perturbation=points.step,
                normalized_sensitivity=(
                    derivative
                    * max(abs(baseline_parameters[parameter_id]), 0.5 * (PARAMETER_BOUNDS[parameter_id][1] - PARAMETER_BOUNDS[parameter_id][0]))
                    / max(abs(baseline_effect), 1.0)
                ),
                difference_scheme=points.method,
                target_kind="shadow_effect",
                parameter_unit="bpm" if parameter_id == "heart_rate_bpm" else "index",
                metric_unit={
                    "ejection_fraction_pct": "percentage_points",
                    "stroke_volume_ml": "mL",
                    "cardiac_output_l_min": "L/min",
                    "heart_rate_bpm": "bpm",
                    "map_mmhg": "mmHg",
                    "edv_ml": "mL",
                    "esv_ml": "mL",
                    "pv_loop_area_index": "index",
                }.get(metric_id, "unknown"),
                perturbation_mode="fractional",
                perturbation_fraction=0.05,
                max_range_fraction=0.05,
                provenance=SensitivityProvenance(
                    source="shadow_trial",
                    ensemble_id=ensemble.id,
                    shadow_trial_id=shadow_trial_id,
                    sample_count=1,
                    seed=sample.seed,
                    model_version="m8-shadow-effect-sensitivity-v1",
                    assumptions=[
                        "M6 same-sample pairing and persisted projection bases are retained.",
                        "Scenario values are fixed absolute targets during baseline perturbation.",
                        "Effect sensitivity is a local deterministic projection, not causal or clinical evidence.",
                    ],
                ),
            )
        )
    return records


__all__ = ["run_effect_sensitivity"]
