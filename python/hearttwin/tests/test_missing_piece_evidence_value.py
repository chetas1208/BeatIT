"""Focused tests for target-specific Evidence Priority Scores."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from python.hearttwin.missing_piece.contracts import EvidenceConstraint
from python.hearttwin.missing_piece.evidence_value import rank_evidence


def _constraint(evidence_type: str, parameters: list[str], strength: str) -> EvidenceConstraint:
    return EvidenceConstraint(
        evidence_type=evidence_type,
        constrained_parameters=parameters,
        strength=strength,
        rationale="Reviewed deterministic proxy mapping.",
        source="focused test",
    )


def test_rank_evidence_multiplies_target_impact_by_reviewed_weight() -> None:
    constraints = [
        _constraint(
            "echocardiographic_measurement",
            ["preload_index", "contractility_index"],
            "strong",
        ),
        _constraint("repeat_ecg", ["heart_rate_bpm"], "moderate"),
    ]
    impacts = [
        SimpleNamespace(parameter_id="heart_rate_bpm", metric_id="ef", impact_score=8.0),
        SimpleNamespace(parameter_id="preload_index", metric_id="ef", impact_score=4.0),
        SimpleNamespace(parameter_id="contractility_index", metric_id="ef", impact_score=2.0),
        SimpleNamespace(parameter_id="preload_index", metric_id="stroke_volume_ml", impact_score=99.0),
    ]

    ranked = rank_evidence("ef", reversed(impacts), reversed(constraints))

    assert [(item.evidence_type, item.ranking_score) for item in ranked] == [
        ("echocardiographic_measurement", 4.5),
        ("repeat_ecg", 4.0),
    ]
    assert all(item.target_metric == "ef" for item in ranked)
    assert all(item.method == "evidence-priority-score-v1" for item in ranked)
    assert all("probability" not in item.method for item in ranked)


def test_rank_evidence_rejects_ambiguous_target_impacts() -> None:
    constraint = _constraint("repeat_ecg", ["heart_rate_bpm"], "moderate")
    impacts = [
        SimpleNamespace(parameter_id="heart_rate_bpm", metric_id="ef", impact_score=1.0),
        SimpleNamespace(parameter_id="heart_rate_bpm", metric_id="ef", impact_score=2.0),
    ]

    with pytest.raises(ValueError, match="duplicate impact scores"):
        rank_evidence("ef", impacts, [constraint])


def test_rank_evidence_uses_only_reviewed_parameters() -> None:
    constraint = _constraint("repeat_ecg", ["preload_index"], "moderate")

    with pytest.raises(ValueError, match="unsupported parameter mapping"):
        rank_evidence("ef", [], [constraint])
