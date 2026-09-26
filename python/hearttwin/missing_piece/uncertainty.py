"""Descriptive uncertainty magnitudes from accepted M5.5 samples.

This module deliberately does not interpret confidence metadata as a
probability or measurement error. It reports normalized empirical spread only.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from python.hearttwin.ensemble import PARAMETER_BOUNDS, EnsembleResponse


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _samples(ensemble: EnsembleResponse | Mapping[str, Any]) -> list[Any]:
    if isinstance(ensemble, EnsembleResponse):
        return [sample for sample in ensemble.samples if sample.valid]
    return [sample for sample in ensemble.get("samples", []) if sample.get("valid", False)]


def parameter_uncertainty(ensemble: EnsembleResponse | Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return q05/q95 normalized spread for every bounded parameter.

    Fewer than two usable values are represented as unavailable, not as zero.
    """

    samples = _samples(ensemble)
    result: dict[str, dict[str, Any]] = {}
    for parameter_id, (lower, upper) in PARAMETER_BOUNDS.items():
        values: list[float] = []
        for sample in samples:
            parameters = sample.parameters if hasattr(sample, "parameters") else sample.get("parameters", {})
            value = parameters.get(parameter_id)
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                values.append(float(value))
        if len(values) < 2:
            result[parameter_id] = {
                "parameter_id": parameter_id,
                "available": False,
                "uncertainty_magnitude": None,
                "q05": None,
                "q95": None,
                "sample_count": len(values),
                "reason": "at least two accepted parameter samples are required",
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
        }
    return result


__all__ = ["parameter_uncertainty"]
