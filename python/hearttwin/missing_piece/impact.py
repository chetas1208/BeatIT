"""Explicit uncertainty-impact heuristic for M8 target rankings."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

from .contracts import ParameterSensitivity, ParameterUncertaintyImpact

_METHOD = "uncertainty-impact-heuristic-v1"


def _finite_number(value: object) -> float | None:
    """Return finite, non-boolean numbers as floats."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    converted = float(value)
    return converted if math.isfinite(converted) else None


def build_uncertainty_impacts(
    sensitivities: Iterable[ParameterSensitivity],
    uncertainty: Mapping[str, Mapping[str, object]],
    *,
    metric_id: str,
) -> list[ParameterUncertaintyImpact]:
    """Combine normalized local response and sampled spread.

    The score is intentionally named an uncertainty-impact heuristic. Raw
    derivatives are not compared across mixed output units; callers should
    provide a normalized sensitivity in the contract when available.
    """

    candidates: list[tuple[str, float, float]] = []
    for item in sensitivities:
        if item.metric_id != metric_id:
            continue
        spread = uncertainty.get(item.parameter_id, {})
        if not isinstance(spread, Mapping):
            continue
        uncertainty_magnitude = _finite_number(spread.get("uncertainty_magnitude"))
        if uncertainty_magnitude is None or uncertainty_magnitude < 0.0:
            continue

        normalized_response = getattr(item, "normalized_sensitivity", None)
        # Cross-parameter ranking is not valid in mixed native units. A raw
        # derivative without the explicit normalized response is unavailable,
        # not a reason to silently fall back to an incomparable number.
        response = _finite_number(normalized_response)
        if response is None:
            continue
        candidates.append((item.parameter_id, uncertainty_magnitude, abs(response)))

    scores = [uncertainty_value * sensitivity_value for _, uncertainty_value, sensitivity_value in candidates]
    total = sum(scores)
    result = [
        ParameterUncertaintyImpact(
            parameter_id=parameter_id,
            metric_id=metric_id,
            uncertainty_magnitude=uncertainty_value,
            sensitivity_magnitude=sensitivity_value,
            impact_score=score,
            normalized_impact=(score / total if total > 0 else 0.0),
            method=_METHOD,
        )
        for (parameter_id, uncertainty_value, sensitivity_value), score in zip(candidates, scores)
    ]
    return sorted(result, key=lambda item: (-item.impact_score, item.parameter_id))


__all__ = ["build_uncertainty_impacts"]
