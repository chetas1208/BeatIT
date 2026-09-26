"""Deterministic local sensitivity over one canonical cardiac state.

This module is deliberately a thin adapter over the M5.5 evaluator.  It does
not reimplement physiology, sample parameters, or mutate the supplied state.
The returned records contain raw local response derivatives; they are not
global variance-attribution or clinical-effect estimates.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from python.hearttwin.ensemble import PARAMETER_BOUNDS, _baseline, _evaluate
from python.hearttwin.missing_piece.contracts import (
    ParameterSensitivity,
    SensitivityProvenance,
)
from python.hearttwin.schemas import CardiacTwinState

type _BoundsSpec = Sequence[float] | Mapping[str, float]


def _bounds_for(parameter_id: str, value: _BoundsSpec) -> tuple[float, float]:
    """Normalize and validate a caller-provided ``(low, high)`` bound."""

    if isinstance(value, Mapping):
        low = value.get("min")
        high = value.get("max")
    else:
        if len(value) != 2:
            raise ValueError(f"{parameter_id}: bounds must contain exactly two values")
        low, high = value

    if not isinstance(low, (int, float)) or isinstance(low, bool):
        raise TypeError(f"{parameter_id}: lower bound must be numeric")
    if not isinstance(high, (int, float)) or isinstance(high, bool):
        raise TypeError(f"{parameter_id}: upper bound must be numeric")
    low_float = float(low)
    high_float = float(high)
    if not math.isfinite(low_float) or not math.isfinite(high_float) or low_float >= high_float:
        raise ValueError(f"{parameter_id}: bounds must be finite and strictly increasing")

    allowed_low, allowed_high = PARAMETER_BOUNDS.get(parameter_id, (math.nan, math.nan))
    if not allowed_low <= low_float <= high_float <= allowed_high:
        raise ValueError(f"{parameter_id}: bounds exceed deterministic model bounds")
    return low_float, high_float


def _metric_value(outputs: Mapping[str, float], metric_id: str) -> float:
    value = outputs.get(metric_id)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"canonical evaluator did not return a finite {metric_id} value")
    return float(value)


def _provenance(
    base: SensitivityProvenance | None,
    *,
    parameter_id: str,
    metric_id: str,
    lower: float,
    upper: float,
    perturbation: float,
    scheme: str,
) -> SensitivityProvenance:
    """Create an independent, record-specific provenance object."""

    assumptions = list(base.assumptions) if base is not None else []
    details = [
        "single canonical state evaluated through the M5.5 deterministic evaluator",
        f"target_metric={metric_id}",
        f"parameter_id={parameter_id}",
        f"bounds=[{lower}, {upper}]",
        f"difference_scheme={scheme}",
        f"step={perturbation}",
        "sensitivity is a local numerical response, not a clinical or causal estimate",
    ]
    for detail in details:
        if detail not in assumptions:
            assumptions.append(detail)

    values = base.model_dump(mode="python") if base is not None else {}
    values["assumptions"] = assumptions
    return SensitivityProvenance.model_validate(values)


def run_local_sensitivity(
    state: CardiacTwinState,
    parameter_bounds: Mapping[str, _BoundsSpec],
    target_metric: str,
    *,
    provenance: SensitivityProvenance | None = None,
    perturbation_fraction: float = 0.05,
) -> list[ParameterSensitivity]:
    """Return bounded finite-difference records for ``target_metric``.

    The baseline parameter vector is extracted once from ``state`` and every
    evaluation uses the canonical M5.5 ``_evaluate`` seam.  A central
    difference is preferred; a forward or backward difference is selected at
    the corresponding bound.  Parameter bounds may be ``(min, max)`` pairs or
    mappings with ``min`` and ``max`` keys.
    """

    if not isinstance(target_metric, str) or not target_metric.strip():
        raise ValueError("target_metric must be a non-empty string")
    target_metric = target_metric.strip()
    if not isinstance(perturbation_fraction, (int, float)) or isinstance(perturbation_fraction, bool):
        raise TypeError("perturbation_fraction must be numeric")
    if not math.isfinite(float(perturbation_fraction)) or not 0.0 < float(perturbation_fraction) < 1.0:
        raise ValueError("perturbation_fraction must be finite and between zero and one")
    if not parameter_bounds:
        raise ValueError("parameter_bounds must contain at least one parameter")

    bounds = {
        parameter_id: _bounds_for(parameter_id, bound)
        for parameter_id, bound in parameter_bounds.items()
    }
    baseline_parameters = _baseline(state)
    if any(parameter_id not in baseline_parameters for parameter_id in bounds):
        unknown = next(parameter_id for parameter_id in bounds if parameter_id not in baseline_parameters)
        raise ValueError(f"unknown deterministic parameter: {unknown}")

    parameters = {parameter_id: float(baseline_parameters[parameter_id]) for parameter_id in baseline_parameters}
    for parameter_id, (lower, upper) in bounds.items():
        value = parameters[parameter_id]
        if not lower <= value <= upper:
            raise ValueError(f"{parameter_id}: canonical state value is outside supplied bounds")

    baseline_outputs = _evaluate(dict(baseline_parameters), dict(parameters))
    baseline_value = _metric_value(baseline_outputs, target_metric)
    results: list[ParameterSensitivity] = []

    for parameter_id, (lower, upper) in bounds.items():
        value = parameters[parameter_id]
        span = upper - lower
        step = min(
            float(perturbation_fraction) * max(abs(value), 0.5 * span),
            float(perturbation_fraction) * span,
        )
        if not math.isfinite(step) or step <= 0.0:
            raise ValueError(f"{parameter_id}: perturbation step is not usable")

        lower_value = value - step
        upper_value = value + step
        lower_parameters = dict(parameters)
        upper_parameters = dict(parameters)
        lower_parameters[parameter_id] = lower_value
        upper_parameters[parameter_id] = upper_value

        if lower_value >= lower and upper_value <= upper:
            lower_output = _metric_value(
                _evaluate(dict(baseline_parameters), lower_parameters), target_metric
            )
            upper_output = _metric_value(
                _evaluate(dict(baseline_parameters), upper_parameters), target_metric
            )
            derivative = (upper_output - lower_output) / (2.0 * step)
            scheme = "central"
        elif upper_value <= upper:
            upper_output = _metric_value(
                _evaluate(dict(baseline_parameters), upper_parameters), target_metric
            )
            derivative = (upper_output - baseline_value) / step
            scheme = "forward"
        elif lower_value >= lower:
            lower_output = _metric_value(
                _evaluate(dict(baseline_parameters), lower_parameters), target_metric
            )
            derivative = (baseline_value - lower_output) / step
            scheme = "backward"
        else:
            raise ValueError(f"{parameter_id}: perturbation cannot fit within supplied bounds")

        if not math.isfinite(derivative):
            raise ValueError(f"{parameter_id}: finite-difference result is not finite")
        results.append(
            ParameterSensitivity(
                parameter_id=parameter_id,
                metric_id=target_metric,
                method="finite_difference",
                sensitivity=derivative,
                baseline_value=baseline_value,
                perturbation=step,
                provenance=_provenance(
                    provenance,
                    parameter_id=parameter_id,
                    metric_id=target_metric,
                    lower=lower,
                    upper=upper,
                    perturbation=step,
                    scheme=scheme,
                ),
            )
        )
    return results


calculate_local_sensitivity = run_local_sensitivity


__all__ = ["calculate_local_sensitivity", "run_local_sensitivity"]
