"""Paired effect statistics with explicit educational units."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

from python.hearttwin.shadow_trial_contracts import (
    EffectDistribution,
    EffectQuantiles,
    NEAR_ZERO_TOLERANCES,
    metric_unit,
    ShadowTrialMetricId,
)


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot calculate a quantile for an empty collection")
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def effect_distribution(
    metric_id: ShadowTrialMetricId,
    deltas: Iterable[float],
    *,
    neutral_tolerance: float | None = None,
) -> EffectDistribution:
    values = [float(value) for value in deltas]
    if any(not math.isfinite(value) for value in values):
        raise ValueError(f"{metric_id}: effect deltas must be finite")
    tolerance = NEAR_ZERO_TOLERANCES[metric_id] if neutral_tolerance is None else neutral_tolerance
    if tolerance < 0 or not math.isfinite(tolerance):
        raise ValueError("neutral tolerance must be finite and non-negative")
    positive = sum(value > tolerance for value in values)
    near_zero = sum(abs(value) <= tolerance for value in values)
    negative = sum(value < -tolerance for value in values)
    if values:
        mean = sum(values) / len(values)
        median = quantile(values, 0.5)
        quantiles = EffectQuantiles(
            q05=quantile(values, 0.05),
            q25=quantile(values, 0.25),
            q75=quantile(values, 0.75),
            q95=quantile(values, 0.95),
        )
    else:
        mean = median = None
        quantiles = EffectQuantiles()
    return EffectDistribution(
        metric_id=metric_id,
        unit=metric_unit(metric_id),
        deltas=values,
        mean_delta=mean,
        median_delta=median,
        quantiles=quantiles,
        positive_count=positive,
        neutral_count=near_zero,
        negative_count=negative,
        neutral_tolerance=tolerance,
    )


def deltas_for_pairs(pairs: Iterable[Mapping[str, Any]], metric_id: ShadowTrialMetricId) -> list[float]:
    return [float(pair["deltas"][metric_id]) for pair in pairs if pair.get("valid")]
