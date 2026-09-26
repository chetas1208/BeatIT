"""Target-specific Evidence Priority Score calculations."""

from __future__ import annotations

from collections.abc import Iterable
from math import fsum

from .contracts import (
    EvidenceConstraint,
    EvidenceValueEstimate,
    EvidenceValueProvenance,
)
from .evidence import EVIDENCE_MAP_VERSION
from .evidence_map import build_priority_inputs


def rank_evidence(
    target_metric: str,
    impacts: Iterable[object],
    constraints: Iterable[EvidenceConstraint],
    *,
    analysis_id: str | None = None,
) -> list[EvidenceValueEstimate]:
    """Rank mapped evidence using uncertainty-impact scores only.

    Each score is the sum of ``impact_score * reviewed_mapping_weight`` for
    parameters mapped to ``target_metric``.  It is a deterministic Evidence
    Priority Score, not a probability or an information-gain calculation.
    """

    target_metric = target_metric.strip()
    if not target_metric:
        raise ValueError("target_metric must be a non-empty string")

    # Materialize once so generators are safe to reuse for every constraint.
    impact_items = tuple(impacts)
    rows: list[EvidenceValueEstimate] = []
    for constraint in constraints:
        priority_inputs = build_priority_inputs(
            (constraint,),
            impact_items,
            target_metric=target_metric,
        )
        score = fsum(item.contribution for item in priority_inputs)
        rows.append(
            EvidenceValueEstimate(
                evidence_type=constraint.evidence_type,
                target_metric=target_metric,
                constrained_parameters=[item.parameter_id for item in priority_inputs],
                estimated_reduction=None,
                ranking_score=score,
                method="evidence-priority-score-v1",
                assumptions=[
                    "Score equals impact multiplied by the reviewed mapping weight for each parameter.",
                    "Score is not a probability and is not an information-gain calculation.",
                    "Evidence labels are educational proxy mappings, not medical recommendations.",
                ],
                provenance=EvidenceValueProvenance(
                    evidence_map_version=EVIDENCE_MAP_VERSION,
                    analysis_id=analysis_id,
                    assumptions=["Mapping is explicit and versioned."],
                ),
            )
        )
    return sorted(rows, key=lambda row: (-row.ranking_score, row.evidence_type))


__all__ = ["rank_evidence"]
