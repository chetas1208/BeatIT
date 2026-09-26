"""Focused tests for deterministic M8 freshness metadata."""

from datetime import UTC, datetime

from python.hearttwin.missing_piece.freshness import freshness_metadata, freshness_score


def test_half_life_is_explicit_and_deterministic() -> None:
    result = freshness_metadata(
        "2026-01-01T00:00:00+00:00",
        reference_at="2026-01-11T00:00:00+00:00",
        half_life_days=10,
        modality="repeat_ecg",
    )

    assert result["available"] is True
    assert result["score"] == 0.5
    assert result["age_days"] == 10.0
    assert result["half_life_days"] == 10.0
    assert result["modality"] == "repeat_ecg"
    assert result["method"] == "exponential_recency_by_explicit_half_life_v1"


def test_same_inputs_produce_same_metadata_without_a_live_clock() -> None:
    inputs = {
        "observed_at": datetime(2026, 1, 1, tzinfo=UTC),
        "reference_at": datetime(2026, 1, 2, tzinfo=UTC),
        "half_life_days": 30,
    }

    assert freshness_metadata(**inputs) == freshness_metadata(**inputs)
    score_inputs = {"observed_at": inputs["observed_at"], "now": inputs["reference_at"], "half_life_days": 30}
    assert freshness_score(**score_inputs) == freshness_score(**score_inputs)


def test_missing_or_invalid_metadata_is_unavailable_not_zero() -> None:
    cases = [
        freshness_metadata(None, reference_at="2026-01-02", half_life_days=30),
        freshness_metadata("2026-01-01", reference_at=None, half_life_days=30),
        freshness_metadata("2026-01-01", reference_at="2026-01-02", half_life_days=None),
        freshness_metadata("2026-01-01", reference_at="2026-01-02", half_life_days=0),
        freshness_metadata("2026-01-03", reference_at="2026-01-02", half_life_days=30),
        freshness_metadata(
            "2026-01-01T00:00:00",
            reference_at="2026-01-02T00:00:00+00:00",
            half_life_days=30,
        ),
    ]

    assert all(item["available"] is False for item in cases)
    assert all(item["score"] is None for item in cases)


def test_score_wrapper_returns_none_without_explicit_reference_or_policy() -> None:
    assert freshness_score("2026-01-01") is None
    assert freshness_score("2026-01-01", now="2026-01-02") is None
