"""Deterministic evidence-to-parameter mappings and priority-score inputs.

The map is deliberately small and explicit. It is a reviewed proxy map for
the deterministic model, not a claim that an observation uniquely identifies a
parameter. Scores produced here are Evidence Priority Scores: transparent
weighted sums of already-computed uncertainty-impact values.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType

from .contracts import EvidenceConstraint

EVIDENCE_MAP_VERSION = "m8-evidence-map-v1"

# Keep this allowlist next to the scoring code so an evidence type cannot gain
# a new parameter silently through a caller-provided EvidenceConstraint.
EVIDENCE_PARAMETER_MAPPINGS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "echocardiographic_measurement": (
            "preload_index",
            "contractility_index",
        ),
        "blood_pressure_series": (
            "afterload_index",
            "systemic_vascular_resistance_index",
        ),
        "repeat_ecg": ("heart_rate_bpm",),
    }
)

STRENGTH_WEIGHTS: Mapping[str, float] = MappingProxyType(
    {"direct": 1.0, "strong": 0.75, "moderate": 0.5, "weak": 0.25}
)


@dataclass(frozen=True, slots=True)
class EvidencePriorityInput:
    """One auditable contribution to an Evidence Priority Score."""

    evidence_type: str
    parameter_id: str
    impact_score: float
    strength: str
    strength_weight: float
    contribution: float


def mapped_parameters(constraint: EvidenceConstraint) -> tuple[str, ...]:
    """Return the explicitly reviewed parameters declared by ``constraint``.

    A known evidence type may constrain a subset of its reviewed mapping, but
    it may not add an undeclared parameter. Unknown evidence types are
    rejected rather than being accepted as an undocumented mapping.
    """

    try:
        reviewed = EVIDENCE_PARAMETER_MAPPINGS[constraint.evidence_type]
    except KeyError as exc:
        raise ValueError(
            "unsupported evidence type without an explicit parameter mapping: "
            f"{constraint.evidence_type}"
        ) from exc

    declared = tuple(constraint.constrained_parameters)
    unsupported = tuple(parameter for parameter in declared if parameter not in reviewed)
    if unsupported:
        raise ValueError(
            f"evidence type {constraint.evidence_type!r} has unsupported parameter mapping: "
            f"{', '.join(unsupported)}"
        )
    return tuple(parameter for parameter in reviewed if parameter in declared)


def evidence_weight(constraint: EvidenceConstraint, parameter_id: str) -> float:
    if parameter_id not in mapped_parameters(constraint):
        return 0.0
    return STRENGTH_WEIGHTS[constraint.strength]


def _impact_by_parameter(
    impacts: Iterable[object],
    *,
    target_metric: str | None,
) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in impacts:
        parameter_id = getattr(item, "parameter_id", None)
        impact_score = getattr(item, "impact_score", None)
        if parameter_id is None or impact_score is None:
            continue
        if target_metric is not None and getattr(item, "metric_id", None) != target_metric:
            continue

        parameter_id = str(parameter_id)
        score = float(impact_score)
        if not isfinite(score) or score < 0.0:
            raise ValueError(f"impact_score for {parameter_id!r} must be finite and non-negative")
        previous = values.get(parameter_id)
        if previous is not None and previous != score:
            raise ValueError(
                f"duplicate impact scores for parameter {parameter_id!r} are ambiguous"
            )
        values[parameter_id] = score
    return values


def build_priority_inputs(
    constraints: Iterable[EvidenceConstraint],
    impacts: Iterable[object],
    *,
    target_metric: str | None = None,
) -> tuple[EvidencePriorityInput, ...]:
    """Build deterministic, inspectable inputs for Evidence Priority Scores.

    Only the declared target metric is considered when ``target_metric`` is
    supplied. Results are sorted by evidence type and reviewed parameter
    order, making the same inputs reproducible regardless of iterable order.
    """

    impact_by_parameter = _impact_by_parameter(impacts, target_metric=target_metric)
    inputs: list[EvidencePriorityInput] = []
    for constraint in sorted(constraints, key=lambda item: item.evidence_type):
        for parameter_id in mapped_parameters(constraint):
            impact_score = impact_by_parameter.get(parameter_id, 0.0)
            weight = evidence_weight(constraint, parameter_id)
            inputs.append(
                EvidencePriorityInput(
                    evidence_type=constraint.evidence_type,
                    parameter_id=parameter_id,
                    impact_score=impact_score,
                    strength=constraint.strength,
                    strength_weight=weight,
                    contribution=impact_score * weight,
                )
            )
    return tuple(inputs)


def map_evidence_scores(
    constraints: Iterable[EvidenceConstraint],
    impacts: Iterable[object],
    *,
    target_metric: str | None = None,
) -> dict[str, float]:
    """Calculate deterministic Evidence Priority Scores.

    This is a weighted uncertainty-impact heuristic. It is not a probability
    of benefit and does not calculate information gain.
    """

    scores: dict[str, float] = {}
    for item in build_priority_inputs(constraints, impacts, target_metric=target_metric):
        scores[item.evidence_type] = scores.get(item.evidence_type, 0.0) + item.contribution
    return scores


__all__ = [
    "EVIDENCE_MAP_VERSION",
    "EVIDENCE_PARAMETER_MAPPINGS",
    "STRENGTH_WEIGHTS",
    "EvidencePriorityInput",
    "build_priority_inputs",
    "evidence_weight",
    "map_evidence_scores",
    "mapped_parameters",
]
