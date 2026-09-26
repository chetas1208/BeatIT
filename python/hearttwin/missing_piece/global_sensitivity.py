"""Honest aggregation boundary for M8 sensitivity records.

The available M8 method is local finite perturbation.  This module therefore
provides only a deterministic aggregate of repeated local records for the
same parameter and target.  It does not estimate a variance contribution and
must not be described as Sobol, Morris, Shapley, or global sensitivity.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from .contracts import ParameterSensitivity


@dataclass(frozen=True, slots=True)
class LocalSensitivityAggregate:
    """Robust descriptive aggregate of local responses for one target.

    All values are absolute raw derivatives and therefore retain the units of
    the input records.  Aggregates are only comparable within the same
    ``parameter_id`` and ``metric_id`` unless a caller supplies an explicit
    unit-normalization policy outside this module.
    """

    parameter_id: str
    metric_id: str
    method: str
    median_absolute_sensitivity: float
    q25_absolute_sensitivity: float
    q75_absolute_sensitivity: float
    minimum_absolute_sensitivity: float
    maximum_absolute_sensitivity: float
    sample_count: int


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def aggregate_local_sensitivity(
    records: Iterable[ParameterSensitivity],
) -> tuple[LocalSensitivityAggregate, ...]:
    """Aggregate repeated local finite-difference records deterministically.

    Records are grouped by parameter and target metric.  The median absolute
    derivative is the aggregate score; quartiles and extrema remain visible
    so callers do not mistake it for a variance share.  The returned tuple is
    sorted by metric, descending aggregate response, then parameter ID.

    Only ``finite_difference`` and the descriptive ``local`` method are
    accepted.  In particular, a record marked ``sobol``, ``morris``, or
    ``shapley`` is rejected rather than silently reinterpreted.
    """

    grouped: defaultdict[tuple[str, str], list[float]] = defaultdict(list)
    for record in records:
        if not isinstance(record, ParameterSensitivity):
            raise TypeError("records must contain ParameterSensitivity values")
        if record.method not in {"finite_difference", "local"}:
            raise ValueError(
                "aggregate_local_sensitivity accepts only local finite-difference records"
            )
        value = abs(float(record.sensitivity))
        if not math.isfinite(value):
            raise ValueError("sensitivity records must contain finite values")
        grouped[(record.parameter_id, record.metric_id)].append(value)

    aggregates = [
        LocalSensitivityAggregate(
            parameter_id=parameter_id,
            metric_id=metric_id,
            method="median_absolute_local_response_v1",
            median_absolute_sensitivity=_quantile(values, 0.5),
            q25_absolute_sensitivity=_quantile(values, 0.25),
            q75_absolute_sensitivity=_quantile(values, 0.75),
            minimum_absolute_sensitivity=min(values),
            maximum_absolute_sensitivity=max(values),
            sample_count=len(values),
        )
        for (parameter_id, metric_id), values in grouped.items()
    ]
    return tuple(
        sorted(
            aggregates,
            key=lambda item: (
                item.metric_id,
                -item.median_absolute_sensitivity,
                item.parameter_id,
            ),
        )
    )


__all__ = ["LocalSensitivityAggregate", "aggregate_local_sensitivity"]
