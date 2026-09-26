"""Descriptive parameter-spread analysis for an accepted M5.5 ensemble.

This agent reports an empirical q05/q95 spread for each deterministic model
parameter.  The spread is normalized by that parameter's declared evaluator
range so it can be combined with the separate M8 uncertainty-impact
heuristic.  It is not a probability, confidence level, or measurement-error
estimate.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

from python.hearttwin.ensemble import PARAMETER_BOUNDS, EnsembleResponse


class ParameterUncertaintyRecord(TypedDict, total=False):
    """JSON-compatible descriptive uncertainty record for one parameter."""

    parameter_id: str
    available: bool
    uncertainty_magnitude: float | None
    q05: float | None
    q95: float | None
    sample_count: int
    reason: str
    bounds: dict[str, float]
    method: str
    interpretation: str


def _quantile(values: Sequence[float], probability: float) -> float:
    """Return a deterministic linearly interpolated empirical quantile."""

    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _as_response(ensemble: EnsembleResponse | Mapping[str, Any]) -> EnsembleResponse:
    """Normalize the persisted mapping returned by ``run_ensemble``.

    Re-validating mappings keeps this boundary on the canonical ensemble
    contract while allowing callers to pass either an API payload or an
    already validated response.
    """

    if isinstance(ensemble, EnsembleResponse):
        return ensemble
    if isinstance(ensemble, Mapping):
        return EnsembleResponse.model_validate(ensemble)
    raise TypeError("ensemble must be an EnsembleResponse or persisted mapping")


def _parameter_values(response: EnsembleResponse, parameter_id: str) -> list[float]:
    """Collect finite values only from accepted samples."""

    values: list[float] = []
    for sample in response.samples:
        if not sample.valid:
            continue
        value = sample.parameters.get(parameter_id)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            values.append(float(value))
    return values


def run_uncertainty_agent(
    ensemble: EnsembleResponse | Mapping[str, Any],
) -> dict[str, ParameterUncertaintyRecord]:
    """Summarize accepted parameter spread for a canonical ensemble.

    Each parameter is summarized independently using q05 and q95 over its
    finite values in accepted samples.  Fewer than two usable values are
    explicitly marked unavailable; they are never converted to zero.  The
    ``MeasuredValue.confidence`` metadata is intentionally not read or used.
    """

    response = _as_response(ensemble)
    result: dict[str, ParameterUncertaintyRecord] = {}
    interpretation = (
        "descriptive normalized spread of accepted deterministic samples; "
        "not a probability, confidence level, or measurement-error estimate"
    )

    for parameter_id, (lower, upper) in PARAMETER_BOUNDS.items():
        values = _parameter_values(response, parameter_id)
        if len(values) < 2:
            result[parameter_id] = {
                "parameter_id": parameter_id,
                "available": False,
                "uncertainty_magnitude": None,
                "q05": None,
                "q95": None,
                "sample_count": len(values),
                "reason": "at least two accepted finite parameter values are required",
                "interpretation": interpretation,
            }
            continue

        q05 = _quantile(values, 0.05)
        q95 = _quantile(values, 0.95)
        magnitude = min(1.0, max(0.0, (q95 - q05) / (upper - lower)))
        result[parameter_id] = {
            "parameter_id": parameter_id,
            "available": True,
            "uncertainty_magnitude": magnitude,
            "q05": q05,
            "q95": q95,
            "sample_count": len(values),
            "bounds": {"min": lower, "max": upper},
            "method": "empirical_q05_q95_over_declared_range",
            "interpretation": interpretation,
        }
    return result


# Descriptive aliases make the calculation usable from both the agent naming
# convention and the shorter M8 analysis vocabulary.
analyze_parameter_uncertainty = run_uncertainty_agent
parameter_uncertainty = run_uncertainty_agent


__all__ = [
    "ParameterUncertaintyRecord",
    "analyze_parameter_uncertainty",
    "parameter_uncertainty",
    "run_uncertainty_agent",
]
