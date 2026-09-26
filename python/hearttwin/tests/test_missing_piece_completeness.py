"""Focused tests for target-specific M8 evidence coverage."""

from __future__ import annotations

from python.hearttwin.missing_piece.completeness import assess_completeness
from python.hearttwin.missing_piece.evidence import evidence_constraints


def test_reports_declared_and_available_coverage_separately() -> None:
    result = assess_completeness(
        ["heart_rate_bpm", "preload_index", "unknown_proxy"],
        evidence_constraints(),
        available_evidence_types=["repeat_ecg"],
        target_metric="ejection_fraction",
    )

    assert result["target_metric"] == "ejection_fraction"
    assert result["declared_covered_parameters"] == ["heart_rate_bpm", "preload_index"]
    assert result["uncovered_parameters"] == ["unknown_proxy"]
    assert result["declared_coverage_fraction"] == 2 / 3
    assert result["available_covered_parameters"] == ["heart_rate_bpm"]
    assert result["unavailable_evidence_parameters"] == ["preload_index"]
    assert result["complete"] is False
    assert result["declared_complete"] is False


def test_empty_target_parameter_set_is_explicitly_incomplete() -> None:
    result = assess_completeness([], evidence_constraints())

    assert result["parameter_count"] == 0
    assert result["coverage_fraction"] == 0.0
    assert result["uncovered_parameters"] == []
    assert result["complete"] is False
    limitations = " ".join(result["limitations"])
    assert "identifiability" in limitations
    assert "clinical utility" in limitations


def test_duplicate_declarations_are_deterministic_and_not_double_counted() -> None:
    constraints = list(evidence_constraints())
    result = assess_completeness(
        ["heart_rate_bpm", "heart_rate_bpm"],
        [constraints[-1], constraints[-1]],
        available_evidence_types=["repeat_ecg", "repeat_ecg"],
    )

    assert result["parameter_ids"] == ["heart_rate_bpm"]
    assert result["mapped_evidence"] == {"heart_rate_bpm": ["repeat_ecg"]}
    assert result["available_evidence"] == {"heart_rate_bpm": ["repeat_ecg"]}
    assert result["complete"] is True
