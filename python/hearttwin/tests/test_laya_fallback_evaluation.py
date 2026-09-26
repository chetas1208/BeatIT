"""Regression-guard evaluation of the deterministic Laya fallback heuristics
(python/hearttwin/assistant/laya_adapter.py's `_fallback_*` functions)
against Agent 21's real labeled fixture set
(python/hearttwin/tests/fixtures/laya_decision_fixtures.py, 160 examples
across the 7 real LayaAdapter decision types).

Wave 5, Agent 22 ("Laya Evaluation Engineer"), retry. Full methodology and
per-decision confusion matrices/worst-failure writeup:
docs/assistant/wave5/laya-evaluation.md. Raw per-fixture predictions and the
real-Laya-server head-to-head comparison this test does NOT re-run (it needs
a live `laya-serve` instance, unavailable in normal CI) are preserved under
docs/assistant/wave5/artifacts/ for reproducibility.

**Why these specific floor numbers:** each `_FLOOR` below is the *measured*
accuracy on the 160-fixture set (see laya-evaluation.md's metrics tables),
minus a margin (roughly 10-15 percentage points, more for the noisier/lower-n
decision types). These are NOT arbitrary targets and NOT 100% — they are a
regression guard: if a future change to the fallback's keyword/regex logic
drops a decision type's accuracy on this fixture set below its floor, that is
a real, measured quality regression worth investigating, not a false alarm
from an unrealistic target. Raising a floor after a genuine heuristic
improvement is expected and good; do not silently lower a floor to make a
regression pass.

Brier score and ECE are intentionally NOT computed here (and are not asserted
against): the deterministic fallback returns no probability, so "Brier
score"/"ECE" against it would require fabricating a fake confidence value,
which this campaign's own rules forbid. See laya-evaluation.md for why those
metrics only apply to the real (probabilistic) Laya server results.
"""

from __future__ import annotations

from python.hearttwin.assistant import laya_adapter as la
from python.hearttwin.tests.fixtures.laya_decision_fixtures import DECISION_NAMES, load_fixtures

_FALLBACK_FN = {
    "classify_intent": la._fallback_classify_intent,
    "select_tool_family": la._fallback_select_tool_family,
    "needs_evidence_retrieval": la._fallback_needs_evidence_retrieval,
    "needs_simulation": la._fallback_needs_simulation,
    "needs_clarification": la._fallback_needs_clarification,
    "needs_physician_review_framing": la._fallback_needs_physician_review_framing,
    "is_complex_reasoning_required": la._fallback_is_complex_reasoning_required,
}

# Measured accuracy on the 160-fixture set (see laya-evaluation.md): 0.586,
# 0.733, 0.850, 0.900, 0.952, 0.900, 0.850 respectively. Floors below are
# measured minus ~10-15pp margin, not aspirational targets.
_FLOORS: dict[str, float] = {
    "classify_intent": 0.45,
    "select_tool_family": 0.60,
    "needs_evidence_retrieval": 0.70,
    "needs_simulation": 0.75,
    "needs_clarification": 0.80,
    "needs_physician_review_framing": 0.75,
    "is_complex_reasoning_required": 0.70,
}

assert set(_FLOORS) == set(DECISION_NAMES), "floor table drifted from the 7 real decision names"


def _accuracy(decision_name: str) -> tuple[float, int, int, list[str]]:
    fn = _FALLBACK_FN[decision_name]
    cases = load_fixtures(decision_name)
    correct = 0
    failures: list[str] = []
    for case in cases:
        out = fn(case.text, case.context)
        predicted = out.chosen if hasattr(out, "chosen") else out.answer
        if predicted == case.expected:
            correct += 1
        else:
            failures.append(f"text={case.text!r} context={case.context} expected={case.expected!r} predicted={predicted!r}")
    return correct / len(cases), correct, len(cases), failures


def test_all_seven_decision_types_have_a_floor() -> None:
    assert set(_FLOORS) == set(DECISION_NAMES)


def test_classify_intent_meets_measured_floor() -> None:
    acc, correct, total, failures = _accuracy("classify_intent")
    assert acc >= _FLOORS["classify_intent"], f"classify_intent accuracy {acc:.3f} ({correct}/{total}) below floor {_FLOORS['classify_intent']}; failures: {failures}"


def test_select_tool_family_meets_measured_floor() -> None:
    acc, correct, total, failures = _accuracy("select_tool_family")
    assert acc >= _FLOORS["select_tool_family"], f"select_tool_family accuracy {acc:.3f} ({correct}/{total}) below floor {_FLOORS['select_tool_family']}; failures: {failures}"


def test_needs_evidence_retrieval_meets_measured_floor() -> None:
    acc, correct, total, failures = _accuracy("needs_evidence_retrieval")
    assert acc >= _FLOORS["needs_evidence_retrieval"], f"needs_evidence_retrieval accuracy {acc:.3f} ({correct}/{total}) below floor; failures: {failures}"


def test_needs_simulation_meets_measured_floor() -> None:
    acc, correct, total, failures = _accuracy("needs_simulation")
    assert acc >= _FLOORS["needs_simulation"], f"needs_simulation accuracy {acc:.3f} ({correct}/{total}) below floor; failures: {failures}"


def test_needs_clarification_meets_measured_floor() -> None:
    acc, correct, total, failures = _accuracy("needs_clarification")
    assert acc >= _FLOORS["needs_clarification"], f"needs_clarification accuracy {acc:.3f} ({correct}/{total}) below floor; failures: {failures}"


def test_needs_physician_review_framing_meets_measured_floor() -> None:
    acc, correct, total, failures = _accuracy("needs_physician_review_framing")
    assert acc >= _FLOORS["needs_physician_review_framing"], f"needs_physician_review_framing accuracy {acc:.3f} ({correct}/{total}) below floor; failures: {failures}"


def test_is_complex_reasoning_required_meets_measured_floor() -> None:
    acc, correct, total, failures = _accuracy("is_complex_reasoning_required")
    assert acc >= _FLOORS["is_complex_reasoning_required"], f"is_complex_reasoning_required accuracy {acc:.3f} ({correct}/{total}) below floor; failures: {failures}"


def test_overall_fallback_accuracy_does_not_collapse() -> None:
    """A coarse aggregate guard on top of the 7 per-type floors above: total
    correct/total across all 160 fixtures should not fall far below the
    measured 129/160 (0.806) baseline. Set loosely (0.65) since the 7
    per-type tests above are the real per-decision regression guards; this
    just catches a broad, cross-cutting regression (e.g. an import error
    silently making every call fall through to one default value)."""
    total_correct = 0
    total_count = 0
    for name in DECISION_NAMES:
        _, correct, total, _ = _accuracy(name)
        total_correct += correct
        total_count += total
    overall = total_correct / total_count
    assert overall >= 0.65, f"overall fallback accuracy collapsed to {overall:.3f} ({total_correct}/{total_count})"
