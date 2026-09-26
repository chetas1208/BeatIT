"""Lead orchestration for the deterministic M8 Missing Piece analysis."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

from python.hearttwin.ensemble import (
    PARAMETER_BOUNDS,
    EnsembleResponse,
    _evaluate,
)

from .completeness import assess_completeness
from .contracts import (
    MissingPieceProvenance,
    MissingPieceResult,
    ParameterSensitivity,
    SensitivityProvenance,
)
from .effect_drivers import run_effect_sensitivity
from .evidence import evidence_constraints
from .evidence_value import rank_evidence
from .impact import build_uncertainty_impacts
from .perturbations import PerturbationPolicy
from .uncertainty import parameter_uncertainty

ENGINE_VERSION = "m8-missing-piece-tier1-v1"
_OUTPUT_KEYS = {"map_mmhg": "map", "edv_ml": "edv", "esv_ml": "esv"}
_OUTPUT_FLOORS = {
    "ejection_fraction_pct": 1.0,
    "stroke_volume_ml": 1.0,
    "edv_ml": 1.0,
    "esv_ml": 1.0,
    "cardiac_output_l_min": 0.1,
    "heart_rate_bpm": 1.0,
    "map_mmhg": 1.0,
}
_METRIC_UNITS = {
    "ejection_fraction_pct": "%",
    "stroke_volume_ml": "mL",
    "edv_ml": "mL",
    "esv_ml": "mL",
    "cardiac_output_l_min": "L/min",
    "heart_rate_bpm": "bpm",
    "map_mmhg": "mmHg",
}
_PARAMETER_UNITS = {
    "heart_rate_bpm": "bpm",
    "preload_index": "index",
    "afterload_index": "index",
    "contractility_index": "index",
    "systemic_vascular_resistance_index": "index",
}
_SUPPORTED_TARGET_METRICS = frozenset(
    {
        "ejection_fraction_pct",
        "stroke_volume_ml",
        "cardiac_output_l_min",
        "heart_rate_bpm",
        "edv_ml",
        "esv_ml",
        "map_mmhg",
    }
)


def _metric_key(metric_id: str) -> str:
    return _OUTPUT_KEYS.get(metric_id, metric_id)


def _finite_metric(outputs: Mapping[str, float], metric_id: str) -> float:
    key = _metric_key(metric_id)
    value = outputs.get(key)
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"canonical evaluator did not return finite target metric: {metric_id}")
    return float(value)


def _analysis_id(ensemble: EnsembleResponse, target_metric: str) -> str:
    payload = {
        "ensemble_id": ensemble.id,
        "target_metric": target_metric,
        "engine_version": ENGINE_VERSION,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return f"missing-piece-{digest[:12]}"


def _sample_sensitivity(
    sample: Any,
    target_metric: str,
    *,
    analysis_id: str,
    ensemble: EnsembleResponse,
) -> tuple[list[ParameterSensitivity], str | None]:
    if not sample.valid or sample.projection_base is None:
        if not sample.valid:
            reasons = "; ".join(sample.rejection_reasons) or "sample is invalid"
            return [], f"{sample.id}: {reasons}"
        return [], f"{sample.id}: persisted projection_base is unavailable"
    base = dict(sample.projection_base)
    parameters = dict(sample.parameters)
    try:
        # Re-evaluate the persisted projection base so a stale or edited output
        # field cannot become the finite-difference baseline.
        baseline = _finite_metric(_evaluate(base, parameters), target_metric)
        records: list[ParameterSensitivity] = []
        for parameter_id, bounds in PARAMETER_BOUNDS.items():
            policy = PerturbationPolicy(parameter_id, step=0.05)
            points = policy.points(parameters[parameter_id])
            lower_output = upper_output = None
            if points.lower is not None:
                lower_parameters = dict(parameters)
                lower_parameters[parameter_id] = points.lower
                lower_output = _finite_metric(_evaluate(base, lower_parameters), target_metric)
            if points.upper is not None:
                upper_parameters = dict(parameters)
                upper_parameters[parameter_id] = points.upper
                upper_output = _finite_metric(_evaluate(base, upper_parameters), target_metric)
            if points.method == "central":
                derivative = (upper_output - lower_output) / (2.0 * points.step)
            elif points.method == "forward":
                derivative = (upper_output - baseline) / points.step
            elif points.method == "backward":
                derivative = (baseline - lower_output) / points.step
            else:
                return [], f"{sample.id}: bounded perturbation is unavailable for {parameter_id}"
            scale = max(abs(parameters[parameter_id]), 0.5 * (bounds[1] - bounds[0]))
            normalized = derivative * scale / max(abs(baseline), _OUTPUT_FLOORS.get(target_metric, 1.0))
            if not math.isfinite(derivative) or not math.isfinite(normalized):
                return [], f"{sample.id}: canonical {target_metric} response is non-finite"
            records.append(
                ParameterSensitivity(
                    parameter_id=parameter_id,
                    metric_id=target_metric,
                    method="finite_difference",
                    sensitivity=derivative,
                    baseline_value=baseline,
                    perturbation=points.step,
                    normalized_sensitivity=normalized,
                    difference_scheme=points.method,
                    target_kind="baseline_output",
                    parameter_unit=_PARAMETER_UNITS[parameter_id],
                    metric_unit=_METRIC_UNITS[target_metric],
                    perturbation_mode="fractional",
                    perturbation_fraction=0.05,
                    max_range_fraction=0.05,
                    parameter_scale=scale,
                    output_floor=_OUTPUT_FLOORS.get(target_metric, 1.0),
                    provenance=SensitivityProvenance(
                        source="ensemble",
                        analysis_id=analysis_id,
                        ensemble_id=ensemble.id,
                        sample_count=1,
                        seed=sample.seed,
                        model_version=ENGINE_VERSION,
                        assumptions=[
                            "Accepted persisted sample and projection base are the numerical authority.",
                            "Local finite difference is not a causal or clinical estimate.",
                            "Normalized response uses the versioned parameter scale and metric floor.",
                        ],
                    ),
                )
            )
        return records, None
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return [], f"{sample.id}: canonical {target_metric} evaluation is unavailable"


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def run_missing_piece(
    baseline_ensemble: EnsembleResponse | Mapping[str, Any],
    target_metric: str,
    *,
    available_evidence_types: Sequence[str] = (),
) -> MissingPieceResult:
    """Produce deterministic target-specific sensitivity and evidence ranking."""

    ensemble = baseline_ensemble if isinstance(baseline_ensemble, EnsembleResponse) else EnsembleResponse.model_validate(baseline_ensemble)
    target_metric = target_metric.strip()
    if not target_metric:
        raise ValueError("target_metric must be a non-empty string")
    if target_metric not in _SUPPORTED_TARGET_METRICS:
        raise ValueError(f"unsupported target_metric: {target_metric}")
    analysis_id = _analysis_id(ensemble, target_metric)
    by_parameter: dict[str, list[ParameterSensitivity]] = {}
    unavailable_reasons: list[str] = []
    for sample in sorted(ensemble.samples, key=lambda item: (item.id, item.index)):
        records, unavailable_reason = _sample_sensitivity(
            sample,
            target_metric,
            analysis_id=analysis_id,
            ensemble=ensemble,
        )
        if unavailable_reason is not None:
            unavailable_reasons.append(unavailable_reason)
        for record in records:
            by_parameter.setdefault(record.parameter_id, []).append(record)

    aggregate: list[ParameterSensitivity] = []
    for parameter_id in sorted(by_parameter):
        records = by_parameter[parameter_id]
        aggregate.append(
            records[0].model_copy(update={
                "sensitivity": _median([record.sensitivity for record in records]),
                "baseline_value": _median([record.baseline_value for record in records]),
                "perturbation": _median([record.perturbation for record in records if record.perturbation is not None]),
                "normalized_sensitivity": _median([abs(record.normalized_sensitivity) for record in records if record.normalized_sensitivity is not None]),
                "normalized_q25": _quantile([abs(record.normalized_sensitivity) for record in records if record.normalized_sensitivity is not None], 0.25),
                "normalized_q75": _quantile([abs(record.normalized_sensitivity) for record in records if record.normalized_sensitivity is not None], 0.75),
                "contributing_sample_count": len(records),
                "provenance": records[0].provenance.model_copy(update={"sample_count": len(records)}),
            })
        )

    uncertainty = parameter_uncertainty(ensemble)
    impacts = build_uncertainty_impacts(aggregate, uncertainty, metric_id=target_metric)
    constraints = evidence_constraints()
    rankings = rank_evidence(target_metric, impacts, constraints, analysis_id=analysis_id)
    completeness = assess_completeness(
        PARAMETER_BOUNDS,
        constraints,
        available_evidence_types=available_evidence_types,
        target_metric=target_metric,
    )
    sensitivity_availability = {
        "available": bool(aggregate),
        "contributing_sample_count": max(
            (len(records) for records in by_parameter.values()),
            default=0,
        ),
        "unavailable_sample_count": len(unavailable_reasons),
        "unavailable_reasons": sorted(unavailable_reasons),
    }
    completeness["sensitivity_availability"] = sensitivity_availability
    return MissingPieceResult(
        target_metric=target_metric,
        sensitivities=aggregate,
        dominant_uncertainty_drivers=impacts,
        evidence_ranking=rankings,
        evidence_constraints=list(constraints),
        completeness=completeness,
        sensitivity_availability=sensitivity_availability,
        limitations=[
            "Sensitivity is a local deterministic finite-difference response.",
            "Uncertainty impact is a sampled-spread times normalized-response heuristic.",
            "Evidence Priority Score is not expected information gain or a medical recommendation.",
            "Missing or insufficient samples remain unavailable rather than being imputed.",
        ],
        provenance=MissingPieceProvenance(
            source="ensemble",
            analysis_id=analysis_id,
            ensemble_id=ensemble.id,
            sensitivity_method="finite_difference",
            ranking_method="evidence-priority-score-v1",
            model_version=ENGINE_VERSION,
            assumptions=[
                "M5.5 accepted samples and their persisted projection bases are authoritative.",
                "M5 parameter distributions are descriptive and independently sampled.",
            ],
        ),
    )


def run_missing_piece_shadow_effect(
    baseline_ensemble: EnsembleResponse | Mapping[str, Any],
    scenario: Any,
    target_metric: str,
    *,
    shadow_trial_id: str | None = None,
    available_evidence_types: Sequence[str] = (),
) -> MissingPieceResult:
    """Analyze uncertainty in a fixed M6 paired Shadow Trial effect.

    The scenario remains an absolute target while the corresponding persisted
    sample baseline is perturbed. This is a local deterministic effect
    sensitivity, not a causal or clinical estimate.
    """

    ensemble = baseline_ensemble if isinstance(baseline_ensemble, EnsembleResponse) else EnsembleResponse.model_validate(baseline_ensemble)
    target_metric = target_metric.strip()
    if not target_metric:
        raise ValueError("target_metric must be a non-empty string")
    analysis_id = _analysis_id(ensemble, f"shadow_effect:{target_metric}")
    by_parameter: dict[str, list[ParameterSensitivity]] = {}
    unavailable: list[str] = []
    for parameter_id in PARAMETER_BOUNDS:
        try:
            records = run_effect_sensitivity(
                ensemble,
                scenario,
                parameter_id=parameter_id,
                metric_id=target_metric,
                shadow_trial_id=shadow_trial_id,
            )
        except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
            unavailable.append(f"{parameter_id}: {exc}")
            continue
        if records:
            by_parameter[parameter_id] = records
        else:
            unavailable.append(f"{parameter_id}: no valid paired samples")

    aggregate: list[ParameterSensitivity] = []
    for parameter_id in sorted(by_parameter):
        records = by_parameter[parameter_id]
        normalized = [abs(record.normalized_sensitivity) for record in records if record.normalized_sensitivity is not None]
        aggregate.append(records[0].model_copy(update={
            "sensitivity": _median([record.sensitivity for record in records]),
            "baseline_value": _median([record.baseline_value for record in records]),
            "normalized_sensitivity": _median(normalized),
            "normalized_q25": _quantile(normalized, 0.25),
            "normalized_q75": _quantile(normalized, 0.75),
            "contributing_sample_count": len(records),
            "provenance": records[0].provenance.model_copy(update={"analysis_id": analysis_id, "sample_count": len(records)}),
        }))

    uncertainty = parameter_uncertainty(ensemble)
    impacts = build_uncertainty_impacts(aggregate, uncertainty, metric_id=target_metric)
    constraints = evidence_constraints()
    rankings = rank_evidence(target_metric, impacts, constraints, analysis_id=analysis_id)
    completeness = assess_completeness(PARAMETER_BOUNDS, constraints, available_evidence_types=available_evidence_types, target_metric=target_metric)
    availability = {
        "available": bool(aggregate),
        "target_kind": "shadow_effect",
        "contributing_sample_count": max((len(records) for records in by_parameter.values()), default=0),
        "unavailable_sample_count": len(unavailable),
        "unavailable_reasons": sorted(unavailable),
    }
    completeness["sensitivity_availability"] = availability
    return MissingPieceResult(
        target_metric=target_metric,
        sensitivities=aggregate,
        dominant_uncertainty_drivers=impacts,
        evidence_ranking=rankings,
        evidence_constraints=list(constraints),
        completeness=completeness,
        sensitivity_availability=availability,
        limitations=[
            "This is sensitivity of a paired Shadow Trial effect under a fixed absolute scenario target.",
            "It is not a causal, treatment, diagnostic, or clinical response estimate.",
            "Uncertainty impact and Evidence Priority Score remain deterministic heuristics.",
        ],
        provenance=MissingPieceProvenance(
            source="shadow_trial",
            analysis_id=analysis_id,
            ensemble_id=ensemble.id,
            shadow_trial_id=shadow_trial_id,
            sensitivity_method="finite_difference",
            ranking_method="evidence-priority-score-v1",
            model_version="m8-shadow-effect-missing-piece-v1",
            assumptions=[
                "M6 same-sample pairing is preserved; no second population is sampled.",
                "Scenario parameter values remain fixed absolute targets.",
            ],
        ),
    )


__all__ = ["ENGINE_VERSION", "run_missing_piece", "run_missing_piece_shadow_effect"]
