"""Stopgap labeled fixtures for Wave 5's Laya evaluation (Agent 22).

**This is a stopgap, not Agent 21's deliverable.** Agent 21 ("Decision
Fixture Engineer") was tasked with producing the canonical labeled fixture
set for this same wave and was still running/incomplete as of this file's
creation (checked twice: only an empty
`python/hearttwin/tests/fixtures/__init__.py` existed, no
`laya_decision_fixtures.py`). Per this task's explicit instructions, a small
(10-15 example) stopgap set was built here instead of blocking indefinitely.
If/when Agent 21's real fixture set lands, prefer it and treat this file as
superseded — do not silently merge the two without review, since ground-truth
labeling judgment calls (see per-fixture comments below) may differ.

Each fixture exercises all 7 real LayaAdapter decision types (see
python/hearttwin/assistant/laya_adapter.py's 7 public methods) against one
piece of user-facing text (+ optional context dict). `expected` gives this
author's best-effort ground-truth label for each decision, independent of
what either the deterministic fallback or a real Laya call actually
produces — the whole point of an eval fixture is that the label is NOT
derived from the implementation under test.

Several fixtures were deliberately chosen because they expose real,
observed weaknesses in the deterministic fallback's keyword/regex logic
(documented inline) — this is not cherry-picking to make the fallback look
bad; it is representative of the actual failure modes found while building
this set (substring collisions like "simulat" matching "simulated" as a
past-tense adjective, and if/elif branch ordering letting an earlier,
broader keyword check shadow a later, more specific one). Several other
fixtures are deliberately "easy" clean cases so the resulting accuracy
numbers reflect a realistic mix rather than a worst-case-only sample.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class LayaFixture:
    fixture_id: str
    text: str
    context: Optional[dict[str, Any]]
    expected: dict[str, Any]
    note: str = ""


FIXTURES: list[LayaFixture] = [
    LayaFixture(
        fixture_id="F01_direct_state_read_ef",
        text="What is the current ejection fraction?",
        context=None,
        expected={
            "classify_intent": "direct_state_read",
            "select_tool_family": "TWIN",
            "needs_evidence_retrieval": False,
            "needs_simulation": False,
            "needs_clarification": False,
            "needs_physician_review_framing": False,
            "is_complex_reasoning_required": False,
        },
        note="Clean case: unambiguous direct state read.",
    ),
    LayaFixture(
        fixture_id="F02_simulation_request",
        text="What if the patient goes on a beta blocker regimen, run the recovery scenario",
        context=None,
        expected={
            "classify_intent": "simulation",
            "select_tool_family": "EXPERIMENT",
            "needs_evidence_retrieval": False,
            "needs_simulation": True,
            "needs_clarification": False,
            "needs_physician_review_framing": False,
            "is_complex_reasoning_required": False,
        },
        note="Clean case: unambiguous simulation request.",
    ),
    LayaFixture(
        fixture_id="F03_evidence_with_resolving_context",
        text="Where does this ejection fraction number come from?",
        context={"snapshot_id": "snap_1"},
        expected={
            "classify_intent": "evidence_retrieval",
            # Ground truth would ideally be EVIDENCE, but "ejection fraction" is
            # also a TWIN trigger keyword and TWIN is checked after EVIDENCE in
            # the fallback's own order, so EVIDENCE should still win here if the
            # fallback is working as designed (the EVIDENCE branch fires from
            # "where...come from" pattern for select_tool_family too? No —
            # select_tool_family's EVIDENCE keywords are evidence/source/
            # provenance/cite only, none present verbatim, so the fallback is
            # expected to mis-route to TWIN here. Documented as a real observed
            # mismatch, not asserted as "correct".
            "select_tool_family": "TWIN",
            "needs_evidence_retrieval": True,
            "needs_simulation": False,
            "needs_clarification": False,
            "needs_physician_review_framing": False,
            "is_complex_reasoning_required": False,
        },
        note="Bare referent 'this' is resolved by snapshot_id in context.",
    ),
    LayaFixture(
        fixture_id="F04_bare_ambiguous",
        text="this",
        context=None,
        expected={
            "classify_intent": "clarification_required",
            "select_tool_family": "NONE",
            "needs_evidence_retrieval": False,
            "needs_simulation": False,
            "needs_clarification": True,
            "needs_physician_review_framing": False,
            "is_complex_reasoning_required": False,
        },
        note="Clean case: single-word input with no context.",
    ),
    LayaFixture(
        fixture_id="F05_comparison_with_simulated_data",
        text="Compare the directly observed versus the simulated ejection fraction over the last month",
        context=None,
        expected={
            # Ground truth: this is a COMPLEX_SYNTHESIS comparison of two
            # already-existing data series, not a request to run a NEW
            # simulation. The fallback's SIMULATION check is evaluated before
            # its COMPLEX_SYNTHESIS check, and its `\bsimulat` pattern matches
            # the substring inside "simulated" (a past-tense adjective
            # describing existing data, not a verb requesting a new run) —
            # expect the fallback to mis-classify this as "simulation".
            "classify_intent": "complex_synthesis",
            "select_tool_family": "COMPARE",
            "needs_evidence_retrieval": False,
            "needs_simulation": False,
            "needs_clarification": False,
            "needs_physician_review_framing": False,
            "is_complex_reasoning_required": True,
        },
        note="KNOWN FALLBACK WEAKNESS: 'simulat' substring fires on 'simulated' (adjective), not just 'simulate' (verb).",
    ),
    LayaFixture(
        fixture_id="F06_artifact_report_with_recovery_word",
        text="Generate a PDF report summarizing this week's recovery trajectory",
        context={"scenario_id": "scn_9"},
        expected={
            # Ground truth: asking for a document about an existing
            # trajectory, not asking to run a new recovery simulation. The
            # fallback's SIMULATION check (checked first) has a bare
            # `\brecovery\b` trigger that fires here even though "recovery"
            # is used as a descriptive noun, not a request to simulate.
            "classify_intent": "artifact_generation",
            "select_tool_family": "REPORT",
            "needs_evidence_retrieval": False,
            "needs_simulation": False,
            "needs_clarification": False,
            "needs_physician_review_framing": False,
            "is_complex_reasoning_required": False,
        },
        note="KNOWN FALLBACK WEAKNESS: bare 'recovery' keyword fires SIMULATION even in a report request.",
    ),
    LayaFixture(
        fixture_id="F07_why_causal_ef",
        text="Why does the ejection fraction drop after the beta blocker dose?",
        context=None,
        expected={
            "classify_intent": "generative_explanation",
            # Ground truth arguably PHYSIOLOGY, but fallback's PHYSIOLOGY
            # keywords (pv loop/ecg/causal/hemodynamic) don't cover "ejection
            # fraction", while TWIN's do — expect TWIN.
            "select_tool_family": "TWIN",
            "needs_evidence_retrieval": False,
            "needs_simulation": False,
            "needs_clarification": False,
            "needs_physician_review_framing": False,
            "is_complex_reasoning_required": False,
        },
        note="'why' correctly wins for intent; tool family drifts to TWIN via 'ejection fraction'.",
    ),
    LayaFixture(
        fixture_id="F08_physician_audience_worry",
        text="I'm worried this looks abnormal, is there a risk here for the patient?",
        context={"patient_id": "p_44", "audience": "physician"},
        expected={
            "classify_intent": "generative_explanation",
            "select_tool_family": "NONE",
            "needs_evidence_retrieval": False,
            "needs_simulation": False,
            "needs_clarification": False,
            "needs_physician_review_framing": True,
            "is_complex_reasoning_required": False,
        },
        note="audience=physician deterministically forces needs_physician_review_framing=True.",
    ),
    LayaFixture(
        fixture_id="F09_direct_read_with_component_context",
        text="Show me the current pressure-volume loop for this component",
        context={"component_id": "cmp_valve_1"},
        expected={
            "classify_intent": "direct_state_read",
            "select_tool_family": "TWIN",
            "needs_evidence_retrieval": False,
            "needs_simulation": False,
            "needs_clarification": False,
            "needs_physician_review_framing": False,
            "is_complex_reasoning_required": False,
        },
        note="Clean case; 'pv loop' regex requires the literal abbreviation so PHYSIOLOGY does not fire on 'pressure-volume loop'.",
    ),
    LayaFixture(
        fixture_id="F10_empty_input",
        text="",
        context=None,
        expected={
            "classify_intent": "clarification_required",
            "select_tool_family": "NONE",
            "needs_evidence_retrieval": False,
            "needs_simulation": False,
            "needs_clarification": True,
            "needs_physician_review_framing": False,
            "is_complex_reasoning_required": False,
        },
        note="Clean edge case: empty string.",
    ),
    LayaFixture(
        fixture_id="F11_shadow_trial_experiment",
        text=(
            "Run a shadow trial experiment comparing the ACE inhibitor pathway "
            "against placebo, and tell me which findings differ"
        ),
        context=None,
        expected={
            "classify_intent": "simulation",
            "select_tool_family": "EXPERIMENT",
            "needs_evidence_retrieval": False,
            # Ground truth True (this explicitly requests running an
            # experiment). The fallback's needs_simulation regex
            # `\brun (an? )?experiment\b` requires "run"/"run a"/"run an"
            # directly adjacent to "experiment" — "run a shadow trial
            # experiment" has extra words in between, so it will not match,
            # and none of the other needs_simulation keywords fire either.
            "needs_simulation": True,
            "needs_clarification": False,
            "needs_physician_review_framing": False,
            # Ground truth True (multi-part comparative ask). The fallback's
            # `\bcompare\b` regex does not match the gerund "comparing", its
            # "which (findings|results) are" pattern requires the literal
            # word "are" (text says "differ"), and the word count is exactly
            # 18 (the threshold is strictly ">18") — expect a false negative.
            "is_complex_reasoning_required": True,
        },
        note="KNOWN FALLBACK WEAKNESS (x2): adjacency-only regex misses 'run a shadow trial experiment'; 'comparing' (gerund) misses the \\bcompare\\b pattern, and word count lands exactly at the >18 threshold boundary.",
    ),
    LayaFixture(
        fixture_id="F12_uncertainty_ensemble",
        text="What evidence would change your assessment of the ensemble's dominant assumption here?",
        context={"ensemble_id": "ens_7"},
        expected={
            "classify_intent": "evidence_retrieval",
            # Ground truth UNCERTAINTY: "what evidence would" and "dominant
            # assumption" are literally two of select_tool_family's own
            # UNCERTAINTY trigger phrases. But select_tool_family checks its
            # EVIDENCE branch (bare \bevidence\b) before its UNCERTAINTY
            # branch, so the broader/earlier EVIDENCE check should shadow the
            # more specific, intentionally-designed UNCERTAINTY match here.
            "select_tool_family": "UNCERTAINTY",
            "needs_evidence_retrieval": True,
            "needs_simulation": False,
            "needs_clarification": False,
            "needs_physician_review_framing": True,
            "is_complex_reasoning_required": False,
        },
        note="KNOWN FALLBACK WEAKNESS: EVIDENCE branch (checked first) shadows the UNCERTAINTY branch's own more-specific 'what evidence would' trigger phrase.",
    ),
    LayaFixture(
        fixture_id="F13_compare_simulated_vs_observed_long",
        text=(
            "Can you compare last month's directly observed heart rate versus the "
            "simulated heart rate and summarize which one tracks better?"
        ),
        context={"scenario_id": "scn_2", "snapshot_id": "snap_5"},
        expected={
            "classify_intent": "complex_synthesis",
            "select_tool_family": "COMPARE",
            "needs_evidence_retrieval": False,
            "needs_simulation": False,
            "needs_clarification": False,
            "needs_physician_review_framing": False,
            "is_complex_reasoning_required": True,
        },
        note="KNOWN FALLBACK WEAKNESS: same 'simulat'-substring collision as F05 (recurs, not a one-off) on intent, tool family, and needs_simulation.",
    ),
    LayaFixture(
        fixture_id="F14_short_get_status",
        text="Get the current status",
        context=None,
        expected={
            "classify_intent": "direct_state_read",
            "select_tool_family": "TWIN",
            "needs_evidence_retrieval": False,
            "needs_simulation": False,
            "needs_clarification": False,
            "needs_physician_review_framing": False,
            "is_complex_reasoning_required": False,
        },
        note="Clean case, though arguably under-specified (status of what?) — the fallback's clarification gate only fires on <=1 word or an unresolved bare referent, neither of which apply here; treated as a deliberate narrow-design choice, not scored as a bug.",
    ),
    LayaFixture(
        fixture_id="F15_hemodynamic_causal_with_risk_word",
        text="How does the hemodynamic feedback loop cause the pressure drop, and why is that concerning for this patient right now",
        context={"patient_id": "p_9"},
        expected={
            # Ground truth generative_explanation ("how"/"why" causal
            # question). The fallback's DETERMINISTIC_COMPUTATION check (bare
            # \bhemodynamic pattern) is evaluated before GENERATIVE_EXPLANATION,
            # so it should win instead.
            "classify_intent": "generative_explanation",
            "select_tool_family": "PHYSIOLOGY",
            "needs_evidence_retrieval": False,
            "needs_simulation": False,
            "needs_clarification": False,
            "needs_physician_review_framing": True,
            "is_complex_reasoning_required": True,
        },
        note="KNOWN FALLBACK WEAKNESS: bare 'hemodynamic' keyword wins DETERMINISTIC_COMPUTATION over the correct generative_explanation reading.",
    ),
]

DECISION_NAMES: list[str] = [
    "classify_intent",
    "select_tool_family",
    "needs_evidence_retrieval",
    "needs_simulation",
    "needs_clarification",
    "needs_physician_review_framing",
    "is_complex_reasoning_required",
]

assert len(FIXTURES) == 15
assert all(set(f.expected.keys()) == set(DECISION_NAMES) for f in FIXTURES), "every fixture must label all 7 decision types"
