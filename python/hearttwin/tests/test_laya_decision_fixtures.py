"""Sanity tests for the Wave 5 Laya decision fixture set
(python/hearttwin/tests/fixtures/laya_decision_fixtures.py).

This is deliberately NOT an accuracy evaluation of laya_adapter.py — it only
proves the fixture set itself is well-formed: it loads, every decision type
meets the minimum count the task required, every fixture has non-empty text,
and every `expected` label is one of the real enum/boolean options (not a
typo that would silently make an evaluator's "correct" check vacuous). A
real accuracy evaluation against `LayaAdapter` is a separate wave deliverable
(the "Laya Evaluation Engineer" task) that imports `load_fixtures` from here.
"""

from __future__ import annotations

import pytest

from python.hearttwin.assistant import laya_adapter
from python.hearttwin.assistant.schemas import ExecutionClass
from python.hearttwin.tests.fixtures.laya_decision_fixtures import (
    DECISION_NAMES,
    TOOL_FAMILY_OPTIONS,
    FixtureCase,
    load_all_fixtures,
    load_fixtures,
    total_fixture_count,
    valid_labels,
)

_MIN_PER_DECISION = 15
_MIN_TOTAL = 105

_VALID_CATEGORIES = {"clear", "ambiguous", "jargon", "shorthand", "multi_intent", "nonsense"}


def test_decision_names_match_the_real_laya_adapter_public_methods() -> None:
    # Mirrors test_laya_adapter.py's own ALL_METHOD_NAMES and
    # test_laya_policy.py's ALL_DECISION_NAMES — if this drifts, the fixture
    # set no longer covers the adapter's real decision surface.
    assert set(DECISION_NAMES) == {
        "classify_intent",
        "select_tool_family",
        "needs_evidence_retrieval",
        "needs_simulation",
        "needs_clarification",
        "needs_physician_review_framing",
        "is_complex_reasoning_required",
    }


def test_tool_family_options_matches_the_real_adapter_vocabulary() -> None:
    # This fixture module deliberately keeps its own copy of the tool-family
    # vocabulary rather than importing laya_adapter's private
    # `_TOOL_FAMILY_OPTIONS` (see module docstring) — this test is what keeps
    # the copy from silently drifting out of sync with the real adapter.
    assert list(TOOL_FAMILY_OPTIONS) == laya_adapter._TOOL_FAMILY_OPTIONS


def test_load_fixtures_rejects_unknown_decision_name() -> None:
    with pytest.raises(KeyError):
        load_fixtures("not_a_real_decision")


def test_valid_labels_rejects_unknown_decision_name() -> None:
    with pytest.raises(KeyError):
        valid_labels("not_a_real_decision")


@pytest.mark.parametrize("decision_name", DECISION_NAMES)
def test_every_decision_has_the_minimum_required_fixture_count(decision_name: str) -> None:
    cases = load_fixtures(decision_name)
    assert len(cases) >= _MIN_PER_DECISION, (
        f"{decision_name} has only {len(cases)} fixtures, need >= {_MIN_PER_DECISION}"
    )


def test_total_fixture_count_meets_the_wave_5_task_floor() -> None:
    assert total_fixture_count() >= _MIN_TOTAL
    assert total_fixture_count() == sum(len(v) for v in load_all_fixtures().values())


@pytest.mark.parametrize("decision_name", DECISION_NAMES)
def test_every_fixture_has_non_empty_text_and_a_dict_context(decision_name: str) -> None:
    for case in load_fixtures(decision_name):
        assert isinstance(case, FixtureCase)
        assert isinstance(case.text, str)
        assert case.text.strip() != "", f"{decision_name} has a fixture with blank text"
        assert isinstance(case.context, dict)


@pytest.mark.parametrize("decision_name", DECISION_NAMES)
def test_every_fixture_category_is_a_recognized_value(decision_name: str) -> None:
    for case in load_fixtures(decision_name):
        assert case.category in _VALID_CATEGORIES, (
            f"{decision_name} fixture {case.text!r} has unrecognized category {case.category!r}"
        )


def test_classify_intent_labels_are_real_execution_class_values() -> None:
    valid = valid_labels("classify_intent")
    assert valid == {item.value for item in ExecutionClass}
    for case in load_fixtures("classify_intent"):
        assert case.expected in valid, f"{case.text!r} has invalid expected label {case.expected!r}"
        assert isinstance(case.expected, str)


def test_select_tool_family_labels_are_real_tool_family_values() -> None:
    valid = valid_labels("select_tool_family")
    assert valid == set(TOOL_FAMILY_OPTIONS)
    for case in load_fixtures("select_tool_family"):
        assert case.expected in valid, f"{case.text!r} has invalid expected label {case.expected!r}"


@pytest.mark.parametrize(
    "decision_name",
    [
        "needs_evidence_retrieval",
        "needs_simulation",
        "needs_clarification",
        "needs_physician_review_framing",
        "is_complex_reasoning_required",
    ],
)
def test_yes_no_decision_labels_are_actual_booleans(decision_name: str) -> None:
    assert valid_labels(decision_name) == {True, False}
    for case in load_fixtures(decision_name):
        assert isinstance(case.expected, bool), (
            f"{decision_name} fixture {case.text!r} has non-bool expected {case.expected!r}"
        )


@pytest.mark.parametrize("decision_name", DECISION_NAMES)
def test_every_label_option_is_covered_by_at_least_one_fixture(decision_name: str) -> None:
    # A weak completeness check: for the 2 choice decisions, every one of the
    # real enum/vocabulary options should appear as an `expected` value at
    # least once, so the fixture set isn't silently missing entire classes
    # (e.g. the rare ExecutionClass values the current fallback can never
    # even produce, like INSUFFICIENT_EVIDENCE / HUMAN_DECISION_REQUIRED /
    # UNSUPPORTED, are exactly the ones worth catching).
    cases = load_fixtures(decision_name)
    covered = {case.expected for case in cases}
    assert covered == valid_labels(decision_name), (
        f"{decision_name} fixtures don't cover every valid label: "
        f"missing {valid_labels(decision_name) - covered}"
    )


def test_load_fixtures_returns_independent_copies() -> None:
    # Mutating the returned list must not corrupt the module's own registry.
    first = load_fixtures("needs_simulation")
    first.append(FixtureCase(text="mutated", expected=True))
    second = load_fixtures("needs_simulation")
    assert len(second) == len(first) - 1
    assert all(case.text != "mutated" for case in second)


def test_at_least_one_ambiguous_hard_case_exists_per_decision() -> None:
    # Part of this task's brief: the set must deliberately include ambiguous/
    # near-tie cases designed to catch the current fallback heuristic being
    # wrong, not just cases that rubber-stamp its existing behavior.
    for decision_name in DECISION_NAMES:
        cases = load_fixtures(decision_name)
        assert any(case.category == "ambiguous" for case in cases), (
            f"{decision_name} has no ambiguous/hard fixtures"
        )
