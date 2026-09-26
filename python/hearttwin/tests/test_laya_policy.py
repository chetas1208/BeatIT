"""Tests for python/hearttwin/assistant/laya_policy.py.

Covers: (a) per-decision-type threshold logic (trustworthy vs. defer) for
every one of the 7 real LayaAdapter decision names, including both "laya"
and "fallback" sources gating identically; (b) an unrecognized decision_name
fails toward clarification rather than toward trust; (c) the
clinical-authority structural guard actually raising for a variety of
misuse attempts, and NOT raising for any real decision name; (d)
get_policy_summary()'s output shape and its "all_measured" rollup;
(e) DecisionAccuracy validates its own bounds and `with_measured_accuracy`
correctly flips source to MEASURED.
"""

from __future__ import annotations

import pytest

from python.hearttwin.assistant.laya_policy import (
    DEFAULT_POLICY,
    AccuracySource,
    ClinicalAuthorityRefused,
    DecisionAccuracy,
    DecisionPolicy,
    DecisionType,
    get_policy_summary,
    should_defer_to_clarification,
)

ALL_DECISION_NAMES = [dt.value for dt in DecisionType]


def test_all_seven_laya_adapter_decision_names_are_covered() -> None:
    # Mirrors laya_adapter.py's real public method names exactly (see
    # test_laya_adapter.py's ALL_METHOD_NAMES) — a mismatch here means this
    # policy module has drifted from the adapter it's meant to gate.
    assert ALL_DECISION_NAMES == [
        "classify_intent",
        "select_tool_family",
        "needs_evidence_retrieval",
        "needs_simulation",
        "needs_clarification",
        "needs_physician_review_framing",
        "is_complex_reasoning_required",
    ]


@pytest.mark.parametrize("decision_name", ALL_DECISION_NAMES)
@pytest.mark.parametrize("source", ["laya", "fallback"])
def test_default_provisional_policy_is_at_its_own_threshold_for_every_decision(decision_name: str, source: str) -> None:
    # Every DEFAULT_POLICY entry is provisional with accuracy == its own
    # defer_threshold (both pinned to the provisional floor), so it should
    # currently read as trustworthy (>=) — i.e. not yet deferring — for both
    # sources, since source doesn't change the type-level gate today.
    assert should_defer_to_clarification(decision_name, source) is False


def test_source_does_not_change_the_outcome_for_a_given_decision_type() -> None:
    for name in ALL_DECISION_NAMES:
        assert should_defer_to_clarification(name, "laya") == should_defer_to_clarification(name, "fallback")


def test_low_accuracy_decision_type_defers_to_clarification() -> None:
    low_accuracy = DecisionAccuracy(
        decision_type=DecisionType.NEEDS_CLARIFICATION,
        accuracy=0.55,
        defer_threshold=0.70,
        source=AccuracySource.MEASURED,
        reference="docs/assistant/wave5/laya-evaluation.md#needs_clarification",
        note="worked example from the task brief",
    )
    policy = DecisionPolicy(needs_clarification=low_accuracy)
    assert should_defer_to_clarification("needs_clarification", "laya", policy=policy) is True
    assert should_defer_to_clarification("needs_clarification", "fallback", policy=policy) is True


def test_high_accuracy_decision_type_is_trusted() -> None:
    high_accuracy = DecisionAccuracy(
        decision_type=DecisionType.SELECT_TOOL_FAMILY,
        accuracy=0.82,
        defer_threshold=0.70,
        source=AccuracySource.MEASURED,
        reference="docs/assistant/wave5/laya-evaluation.md#select_tool_family",
    )
    policy = DecisionPolicy(select_tool_family=high_accuracy)
    assert should_defer_to_clarification("select_tool_family", "laya", policy=policy) is False


def test_accuracy_exactly_at_threshold_is_trusted_not_deferred() -> None:
    # is_trustworthy uses >=, so a decision type measured exactly at its own
    # threshold should read as trustworthy, not as a boundary failure.
    at_threshold = DecisionAccuracy(
        decision_type=DecisionType.NEEDS_SIMULATION,
        accuracy=0.70,
        defer_threshold=0.70,
        source=AccuracySource.MEASURED,
        reference="docs/assistant/wave5/laya-evaluation.md#needs_simulation",
    )
    policy = DecisionPolicy(needs_simulation=at_threshold)
    assert should_defer_to_clarification("needs_simulation", "laya", policy=policy) is False


def test_unrecognized_decision_name_defers_rather_than_trusts() -> None:
    # A caller bug (typo, or a new LayaAdapter method this policy hasn't
    # been updated for yet) must fail toward the conservative product
    # outcome, not toward silently trusting an unknown decision.
    assert should_defer_to_clarification("some_future_decision_nobody_registered", "laya") is True


# ---------------------------------------------------------------------------
# Clinical-authority structural guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "misused_name",
    [
        "diagnose_condition",
        "recommend_treatment",
        "select_medication",
        "adjust_dosage",
        "determine_emergency_disposition",
        "triage_level",
        "DIAGNOSE",  # case-insensitivity
        "should_treat_with_beta_blocker",
    ],
)
def test_clinical_authority_guard_raises_loudly_for_misuse(misused_name: str) -> None:
    with pytest.raises(ClinicalAuthorityRefused):
        should_defer_to_clarification(misused_name, "laya")


@pytest.mark.parametrize("decision_name", ALL_DECISION_NAMES)
def test_clinical_authority_guard_never_fires_on_a_real_decision_name(decision_name: str) -> None:
    # No false positives: none of the 7 real LayaAdapter decision names
    # should ever trip the clinical-term substring guard.
    should_defer_to_clarification(decision_name, "laya")  # must not raise


def test_clinical_authority_guard_checked_before_unknown_name_fallback() -> None:
    # A clinical-sounding AND unrecognized name must still raise, not
    # silently resolve via the "unknown -> defer" path.
    with pytest.raises(ClinicalAuthorityRefused):
        should_defer_to_clarification("emergency_triage_priority", "fallback")


# ---------------------------------------------------------------------------
# get_policy_summary()
# ---------------------------------------------------------------------------


def test_policy_summary_shape() -> None:
    summary = get_policy_summary()
    assert set(summary.keys()) == {"decisions", "all_measured", "pending_evaluation_doc"}
    assert set(summary["decisions"].keys()) == set(ALL_DECISION_NAMES)
    for name, entry in summary["decisions"].items():
        assert set(entry.keys()) == {"accuracy", "defer_threshold", "is_trustworthy", "source", "reference", "note"}
        assert isinstance(entry["accuracy"], float)
        assert isinstance(entry["defer_threshold"], float)
        assert isinstance(entry["is_trustworthy"], bool)
        assert entry["source"] in ("measured", "provisional-default")


def test_default_policy_summary_is_all_provisional() -> None:
    summary = get_policy_summary()
    assert summary["all_measured"] is False
    for entry in summary["decisions"].values():
        assert entry["source"] == "provisional-default"
        assert "PENDING" in entry["reference"]


def test_all_measured_flips_true_once_every_entry_is_measured() -> None:
    measured_entries = {
        dt.value: DEFAULT_POLICY.get(dt).with_measured_accuracy(0.9, reference="docs/assistant/wave5/laya-evaluation.md")
        for dt in DecisionType
    }
    fully_measured_policy = DecisionPolicy(**measured_entries)
    summary = get_policy_summary(policy=fully_measured_policy)
    assert summary["all_measured"] is True
    for entry in summary["decisions"].values():
        assert entry["source"] == "measured"


# ---------------------------------------------------------------------------
# DecisionAccuracy validation + with_measured_accuracy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_accuracy", [-0.01, 1.01])
def test_decision_accuracy_rejects_out_of_bounds_accuracy(bad_accuracy: float) -> None:
    with pytest.raises(ValueError):
        DecisionAccuracy(
            decision_type=DecisionType.CLASSIFY_INTENT,
            accuracy=bad_accuracy,
            defer_threshold=0.7,
            source=AccuracySource.PROVISIONAL_DEFAULT,
            reference="test",
        )


@pytest.mark.parametrize("bad_threshold", [-0.5, 1.5])
def test_decision_accuracy_rejects_out_of_bounds_threshold(bad_threshold: float) -> None:
    with pytest.raises(ValueError):
        DecisionAccuracy(
            decision_type=DecisionType.CLASSIFY_INTENT,
            accuracy=0.7,
            defer_threshold=bad_threshold,
            source=AccuracySource.PROVISIONAL_DEFAULT,
            reference="test",
        )


def test_with_measured_accuracy_flips_source_and_keeps_type() -> None:
    provisional = DEFAULT_POLICY.get(DecisionType.NEEDS_EVIDENCE_RETRIEVAL)
    assert provisional.source is AccuracySource.PROVISIONAL_DEFAULT

    measured = provisional.with_measured_accuracy(
        0.88, reference="docs/assistant/wave5/laya-evaluation.md#needs_evidence_retrieval"
    )
    assert measured.source is AccuracySource.MEASURED
    assert measured.accuracy == 0.88
    assert measured.decision_type == DecisionType.NEEDS_EVIDENCE_RETRIEVAL
    # defer_threshold is untouched by a measurement update — only the
    # observed accuracy and its provenance change.
    assert measured.defer_threshold == provisional.defer_threshold


def test_decision_policy_get_and_as_dict_cover_every_type() -> None:
    as_dict = DEFAULT_POLICY.as_dict()
    assert set(as_dict.keys()) == set(DecisionType)
    for dt in DecisionType:
        assert DEFAULT_POLICY.get(dt) is as_dict[dt]
