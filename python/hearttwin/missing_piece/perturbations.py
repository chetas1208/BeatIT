"""Bounded perturbation policies for deterministic M8 sensitivity analysis.

The policy works in each parameter's native unit.  Fractional steps are
relative to a stable parameter scale, while every resolved step is capped at
five percent of the parameter's declared model range.  This keeps local
finite differences comparable without allowing an arbitrary percentage to
cross the deterministic evaluator's domain.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from python.hearttwin.ensemble import PARAMETER_BOUNDS

PerturbationMode = Literal["absolute", "fractional"]
PerturbationDirection = Literal["lower", "upper"]
DifferenceMethod = Literal["central", "forward", "backward", "unavailable"]

DEFAULT_FRACTIONAL_STEP = 0.05
DEFAULT_MAX_RANGE_FRACTION = 0.05


def _finite_number(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field_name} must be a finite number")
    return float(value)


def _parameter_bounds(parameter_id: str) -> tuple[float, float]:
    if not isinstance(parameter_id, str) or not parameter_id.strip():
        raise ValueError("parameter_id must be a non-empty string")
    try:
        return PARAMETER_BOUNDS[parameter_id]
    except KeyError as exc:
        raise ValueError(f"unknown perturbation parameter: {parameter_id}") from exc


def validate_baseline(parameter_id: str, baseline_value: float) -> float:
    """Validate and return a baseline value inside the model domain."""

    low, high = _parameter_bounds(parameter_id)
    baseline = _finite_number(baseline_value, "baseline_value")
    if not low <= baseline <= high:
        raise ValueError(
            f"{parameter_id}: baseline_value must be within [{low}, {high}]"
        )
    return baseline


@dataclass(frozen=True, slots=True)
class PerturbationPoints:
    """Valid finite-difference points for one parameter baseline."""

    parameter_id: str
    baseline_value: float
    step: float
    lower: float | None
    upper: float | None

    @property
    def method(self) -> DifferenceMethod:
        if self.lower is not None and self.upper is not None:
            return "central"
        if self.upper is not None:
            return "forward"
        if self.lower is not None:
            return "backward"
        return "unavailable"

    @property
    def at_lower_bound(self) -> bool:
        low, _ = _parameter_bounds(self.parameter_id)
        return self.baseline_value == low

    @property
    def at_upper_bound(self) -> bool:
        _, high = _parameter_bounds(self.parameter_id)
        return self.baseline_value == high


@dataclass(frozen=True, slots=True)
class PerturbationPolicy:
    """Resolve bounded perturbations for one deterministic model parameter.

    ``step`` is interpreted as native units for ``absolute`` mode.  In
    ``fractional`` mode it is a fraction of
    ``max(abs(baseline), 0.5 * parameter_range)``.  The resolved value is
    always capped at ``max_range_fraction * parameter_range``.
    """

    parameter_id: str
    step: float
    mode: PerturbationMode = "fractional"
    max_range_fraction: float = DEFAULT_MAX_RANGE_FRACTION

    def __post_init__(self) -> None:
        _parameter_bounds(self.parameter_id)
        step = _finite_number(self.step, "step")
        if step <= 0:
            raise ValueError("step must be positive")
        if self.mode not in ("absolute", "fractional"):
            raise ValueError("mode must be 'absolute' or 'fractional'")
        if self.mode == "fractional" and step > 1:
            raise ValueError("fractional step must be no greater than 1")
        max_fraction = _finite_number(self.max_range_fraction, "max_range_fraction")
        if not 0 < max_fraction <= 0.5:
            raise ValueError("max_range_fraction must be in the interval (0, 0.5]")

    @property
    def bounds(self) -> tuple[float, float]:
        return _parameter_bounds(self.parameter_id)

    @property
    def parameter_range(self) -> float:
        low, high = self.bounds
        return high - low

    @property
    def maximum_step(self) -> float:
        return self.max_range_fraction * self.parameter_range

    def raw_step(self, baseline_value: float) -> float:
        """Return the requested native-unit step before the range cap."""

        baseline = validate_baseline(self.parameter_id, baseline_value)
        if self.mode == "absolute":
            return float(self.step)
        scale = max(abs(baseline), 0.5 * self.parameter_range)
        return float(self.step) * scale

    def resolved_step(self, baseline_value: float) -> float:
        """Return the bounded native-unit step used by finite differences."""

        return min(self.raw_step(baseline_value), self.maximum_step)

    def points(self, baseline_value: float) -> PerturbationPoints:
        """Return only in-domain points, selecting one-sided differences at bounds."""

        baseline = validate_baseline(self.parameter_id, baseline_value)
        step = self.resolved_step(baseline)
        low, high = self.bounds
        lower = baseline - step
        upper = baseline + step
        return PerturbationPoints(
            parameter_id=self.parameter_id,
            baseline_value=baseline,
            step=step,
            lower=lower if lower >= low else None,
            upper=upper if upper <= high else None,
        )

    def value(
        self,
        baseline_value: float,
        direction: PerturbationDirection,
    ) -> float | None:
        """Return one valid directional point, or ``None`` at that bound."""

        points = self.points(baseline_value)
        if direction == "lower":
            return points.lower
        if direction == "upper":
            return points.upper
        raise ValueError("direction must be 'lower' or 'upper'")


def resolve_perturbation_step(
    parameter_id: str,
    baseline_value: float,
    *,
    step: float = DEFAULT_FRACTIONAL_STEP,
    mode: PerturbationMode = "fractional",
    max_range_fraction: float = DEFAULT_MAX_RANGE_FRACTION,
) -> float:
    """Convenience wrapper for resolving one bounded native-unit step."""

    return PerturbationPolicy(
        parameter_id=parameter_id,
        step=step,
        mode=mode,
        max_range_fraction=max_range_fraction,
    ).resolved_step(baseline_value)


__all__ = [
    "DEFAULT_FRACTIONAL_STEP",
    "DEFAULT_MAX_RANGE_FRACTION",
    "DifferenceMethod",
    "PerturbationDirection",
    "PerturbationMode",
    "PerturbationPoints",
    "PerturbationPolicy",
    "resolve_perturbation_step",
    "validate_baseline",
]
