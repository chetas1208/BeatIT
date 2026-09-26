"""Focused tests for the explicit M8 evidence map and priority inputs."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from python.hearttwin.missing_piece.contracts import EvidenceConstraint
from python.hearttwin.missing_piece.evidence_map import (
    EVIDENCE_PARAMETER_MAPPINGS,
    STRENGTH_WEIGHTS,
    build_priority_inputs,
    map_evidence_scores,
    mapped_parameters,
)


def _constraint(
    evidence_type: str = "echocardiographic_measurement",
    parameters: list[str] | None = None,
    strength: str = "strong",
) -> EvidenceConstraint:
    return EvidenceConstraint(
        evidence_type=evidence_type,
        constrained_parameters=parameters
        or list(EVIDENCE_PARAMETER_MAPPINGS[evidence_type]),
        strength=strength,
        rationale="Reviewed deterministic proxy mapping.",
        source="focused test",
    )


def test_explicit_mapping_preserves_reviewed_parameter_order() -> None:
    constraint = _constraint(parameters=["contractility_index"])

    assert mapped_parameters(constraint) == ("contractility_index",)
    assert EVIDENCE_PARAMETER_MAPPINGS["repeat_ecg"] == ("heart_rate_bpm",)


def test_priority_inputs_expose_weighted_score_inputs_deterministically() -> None:
    constraints = [
        _constraint("repeat_ecg", strength="moderate"),
        _constraint(parameters=["preload_index"], strength="strong"),
    ]
    impacts = [
        SimpleNamespace(parameter_id="heart_rate_bpm", metric_id="ef", impact_score=2.0),
        SimpleNamespace(parameter_id="preload_index", metric_id="other", impact_score=99.0),
        SimpleNamespace(parameter_id="preload_index", metric_id="ef", impact_score=4.0),
    ]

    inputs = build_priority_inputs(constraints, reversed(impacts), target_metric="ef")

    assert [(item.evidence_type, item.parameter_id) for item in inputs] == [
        ("echocardiographic_measurement", "preload_index"),
        ("repeat_ecg", "heart_rate_bpm"),
    ]
    assert [item.contribution for item in inputs] == [3.0, 1.0]
    assert map_evidence_scores(constraints, impacts, target_metric="ef") == {
        "echocardiographic_measurement": 3.0,
        "repeat_ecg": 1.0,
    }


def test_strength_weights_are_explicit_and_immutable() -> None:
    assert dict(STRENGTH_WEIGHTS) == {
        "direct": 1.0,
        "strong": 0.75,
        "moderate": 0.5,
        "weak": 0.25,
    }
    with pytest.raises(TypeError):
        STRENGTH_WEIGHTS["strong"] = 1.0  # type: ignore[index]


def test_unsupported_mapping_and_ambiguous_impacts_fail_loudly() -> None:
    with pytest.raises(ValueError, match="unsupported parameter mapping"):
        mapped_parameters(_constraint("repeat_ecg", parameters=["preload_index"]))

    impacts = [
        SimpleNamespace(parameter_id="heart_rate_bpm", metric_id="ef", impact_score=1.0),
        SimpleNamespace(parameter_id="heart_rate_bpm", metric_id="ef", impact_score=2.0),
    ]
    with pytest.raises(ValueError, match="duplicate impact scores"):
        map_evidence_scores([_constraint("repeat_ecg")], impacts, target_metric="ef")


def test_score_surface_is_explicitly_not_information_gain() -> None:
    assert "does not calculate information gain" in (map_evidence_scores.__doc__ or "")
