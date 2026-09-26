"""Target-specific evidence completeness checks for M8."""

from __future__ import annotations

from collections.abc import Iterable

from .contracts import EvidenceConstraint


def assess_completeness(
    parameter_ids: Iterable[str],
    constraints: Iterable[EvidenceConstraint],
    *,
    available_evidence_types: Iterable[str] = (),
    target_metric: str | None = None,
) -> dict[str, object]:
    """Report declared and currently available evidence coverage.

    ``parameter_ids`` is the target-specific parameter set supplied by the
    caller.  A declared mapping means that the reviewed taxonomy names an
    evidence type for the parameter; an available mapping additionally
    requires that type to be present in ``available_evidence_types``.

    ``complete`` intentionally retains its historical availability-based
    meaning.  ``declared_complete`` makes the reviewed mapping status
    explicit without implying identifiability, validity, or clinical utility.
    """

    parameters = sorted({_clean(value, "parameter_id") for value in parameter_ids})
    evidence = sorted({_clean(value, "evidence_type") for value in available_evidence_types})
    evidence_set = set(evidence)
    mapped: dict[str, list[str]] = {parameter_id: [] for parameter_id in parameters}
    usable: dict[str, list[str]] = {parameter_id: [] for parameter_id in parameters}
    for constraint in constraints:
        for parameter_id in constraint.constrained_parameters:
            if parameter_id in mapped:
                if constraint.evidence_type not in mapped[parameter_id]:
                    mapped[parameter_id].append(constraint.evidence_type)
                if constraint.evidence_type in evidence_set and constraint.evidence_type not in usable[parameter_id]:
                    usable[parameter_id].append(constraint.evidence_type)

    for values in (*mapped.values(), *usable.values()):
        values.sort()

    declared_covered = [parameter_id for parameter_id, values in mapped.items() if values]
    available_covered = [parameter_id for parameter_id, values in usable.items() if values]
    declared_uncovered = [parameter_id for parameter_id in parameters if not mapped[parameter_id]]
    unavailable = [
        parameter_id
        for parameter_id in declared_covered
        if not usable[parameter_id]
    ]
    declared_fraction = len(declared_covered) / len(parameters) if parameters else 0.0
    available_fraction = len(available_covered) / len(parameters) if parameters else 0.0

    return {
        "method": "declared-evidence-map-coverage-v1",
        "target_metric": target_metric.strip() if target_metric and target_metric.strip() else None,
        "parameter_count": len(parameters),
        "parameter_ids": parameters,
        "covered_parameter_count": len(declared_covered),
        "coverage_fraction": declared_fraction,
        "declared_covered_parameters": declared_covered,
        "declared_coverage_fraction": declared_fraction,
        "declared_complete": bool(parameters) and len(declared_covered) == len(parameters),
        "mapped_evidence": mapped,
        "available_evidence": usable,
        "available_covered_parameters": available_covered,
        "available_coverage_fraction": available_fraction,
        "uncovered_parameters": declared_uncovered,
        "unavailable_evidence_parameters": unavailable,
        "complete": bool(parameters) and len(available_covered) == len(parameters),
        "limitations": [
            "Coverage reports only the reviewed evidence-to-model-proxy mapping for this target parameter set.",
            "Declared coverage does not establish identifiability or uniqueness of any parameter.",
            "Available evidence coverage does not establish measurement validity or clinical utility.",
            "Uncovered parameters are mapping gaps, not statements about real-world observability.",
        ],
    }


def _clean(value: str, field_name: str) -> str:
    """Normalize an identifier while rejecting empty or non-string values."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


__all__ = ["assess_completeness"]
