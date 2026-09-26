"""Labeled evaluation fixtures for the 7 bounded Laya System-1 decisions.

Wave 5, Agent 21 ("Decision Fixture Engineer"), retry after a prior attempt
was interrupted by an account rate limit (see docs/assistant/WAVE_5_HANDOFF.md
and docs/assistant/wave5/decision-fixtures.md for full methodology).

Purpose: give later Wave 5 agents (in particular the "Laya Evaluation
Engineer") an independently-labeled ground truth to measure real accuracy of
`python/hearttwin/assistant/laya_adapter.py`'s 7 named decision methods
against, instead of guessing or (worse) treating the current deterministic
fallback's own output as if it were correct. Labels here were derived by
reading `docs/assistant/GLOBAL_ARCHITECTURE.md`'s decision definitions
("EXECUTION CLASSES", "SINGLE TOOL REGISTRY", "SYSTEM-1 (Laya) VS SYSTEM-2")
directly, NOT by running the fallback and copying its answer — several
fixtures below are deliberately chosen because a careful human reading of
those definitions disagrees with what the current keyword-cascade fallback
in laya_adapter.py would actually output. Every such case is tagged
`category="ambiguous"` or `"nonsense"` and carries a `notes` string
explaining the specific disagreement; see decision-fixtures.md for the full
methodology writeup and known limitations (single-annotator bias, small
sample size, etc.).

Do NOT import anything from `laya_adapter.py` other than reading its module
docstring/behavior for reference — this file must stay an independent
oracle. `TOOL_FAMILY_OPTIONS` below is a deliberate second copy of the
adapter's private `_TOOL_FAMILY_OPTIONS` vocabulary (not an import of it),
with `test_laya_decision_fixtures.py` asserting the two stay identical so
this file can't silently drift from the real registry categories in
GLOBAL_ARCHITECTURE.md's "SINGLE TOOL REGISTRY" section without a test
failure flagging it.

Usage for other agents:

    from python.hearttwin.tests.fixtures.laya_decision_fixtures import (
        DECISION_NAMES, load_fixtures, load_all_fixtures, valid_labels,
    )

    for case in load_fixtures("classify_intent"):
        result = await adapter.classify_intent(case.text, case.context)
        is_correct = result.chosen == case.expected
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from python.hearttwin.assistant.schemas import ExecutionClass

# ---------------------------------------------------------------------------
# Vocabularies (kept as independent copies of laya_adapter.py's real
# vocabularies, not imports — see module docstring)
# ---------------------------------------------------------------------------

TOOL_FAMILY_OPTIONS: tuple[str, ...] = (
    "TWIN",
    "EVIDENCE",
    "PHYSIOLOGY",
    "EXPERIMENT",
    "COMPARE",
    "UNCERTAINTY",
    "REPORT",
    "NONE",
)

DECISION_NAMES: tuple[str, ...] = (
    "classify_intent",
    "select_tool_family",
    "needs_evidence_retrieval",
    "needs_simulation",
    "needs_clarification",
    "needs_physician_review_framing",
    "is_complex_reasoning_required",
)

_CHOICE_DECISIONS = {"classify_intent", "select_tool_family"}
_YES_NO_DECISIONS = set(DECISION_NAMES) - _CHOICE_DECISIONS


@dataclass(frozen=True)
class FixtureCase:
    """One labeled example for one decision type.

    `expected` is a `str` (an `ExecutionClass` value or a `TOOL_FAMILY_OPTIONS`
    entry) for the 2 choice decisions, or a `bool` for the 5 yes/no decisions.
    `context` mirrors the `context` dict `LayaAdapter` methods accept (e.g.
    `component_id`, `ensemble_id`, `audience`) — required for
    `needs_clarification` (referent resolution) and
    `needs_physician_review_framing` (`audience` short-circuit).
    `category` is one of: clear | ambiguous | jargon | shorthand |
    multi_intent | nonsense — see decision-fixtures.md for definitions.
    `notes` explains the labeling judgment call, especially for ambiguous/
    hard cases and cases where the current fallback heuristic is believed
    (not merely assumed) to disagree with this label.
    """

    text: str
    expected: Any
    context: dict[str, Any] = field(default_factory=dict)
    category: str = "clear"
    notes: str = ""


def _c(text: str, expected: Any, context: dict[str, Any] | None = None, category: str = "clear", notes: str = "") -> FixtureCase:
    return FixtureCase(text=text, expected=expected, context=dict(context or {}), category=category, notes=notes)


# ---------------------------------------------------------------------------
# 1. classify_intent — 11 ExecutionClass options
# ---------------------------------------------------------------------------

_EC = ExecutionClass

_CLASSIFY_INTENT: list[FixtureCase] = [
    # -- direct_state_read (3) --
    _c("What is the current EF?", _EC.DIRECT_STATE_READ.value,
       notes="Verbatim GLOBAL_ARCHITECTURE.md fast-path example."),
    _c("Show me the LV ejection fraction right now.", _EC.DIRECT_STATE_READ.value,
       category="jargon", notes="No 'current'/'what is' keywords; tests recall beyond the literal fallback trigger words."),
    _c("whats the ef", _EC.DIRECT_STATE_READ.value,
       category="shorthand", notes="Lowercase, no apostrophe, no punctuation — realistic chat shorthand."),

    # -- evidence_retrieval (3) --
    _c("Where did this EF value come from?", _EC.EVIDENCE_RETRIEVAL.value,
       notes="Verbatim GLOBAL_ARCHITECTURE.md-style evidence ask."),
    _c("Can you cite the source for the QTc measurement?", _EC.EVIDENCE_RETRIEVAL.value),
    _c("What's the provenance of the echo-derived stroke volume?", _EC.EVIDENCE_RETRIEVAL.value,
       category="jargon", notes="Physician-register phrasing ('provenance', 'echo-derived')."),

    # -- deterministic_computation (3) --
    _c("Calculate the cardiac output from HR and stroke volume.", _EC.DETERMINISTIC_COMPUTATION.value),
    _c("Compute the PV loop for the current snapshot.", _EC.DETERMINISTIC_COMPUTATION.value,
       notes="Also contains 'current', but 'compute'/'pv loop' correctly dominate for a pure computation ask."),
    _c("Give me the hemodynamic numbers for this component.", _EC.DETERMINISTIC_COMPUTATION.value,
       category="jargon"),

    # -- simulation (3) --
    _c("What if we reduce afterload by 20%?", _EC.SIMULATION.value),
    _c("Run a recovery scenario for this patient.", _EC.SIMULATION.value),
    _c("Rerun the ensemble with updated priors.", _EC.SIMULATION.value,
       category="ambiguous",
       notes="Fallback-miss hypothesis: classify_intent's SIMULATION bucket keyword list "
             "(what if/scenario/simulat/recovery/run.*experiment) contains none of "
             "'rerun'/'ensemble', so the cascade falls through to the final "
             "GENERATIVE_EXPLANATION else-branch. Human ground truth: re-running an "
             "ensemble is unambiguously a simulation request (EXPERIMENT tool family, "
             "run_ensemble). Contrast with needs_simulation's fallback, whose keyword "
             "list DOES include 'rerun' and would get this one right — an inconsistency "
             "between the two fallback heuristics worth noting."),

    # -- artifact_generation (3) --
    _c("Generate a PDF report of this patient's twin.", _EC.ARTIFACT_GENERATION.value),
    _c("Create a physician brief for this case.", _EC.ARTIFACT_GENERATION.value, category="jargon"),
    _c("Draft a computational report artifact for the ensemble run.", _EC.ARTIFACT_GENERATION.value),

    # -- complex_synthesis (3) --
    _c("Summarize what changed over the last month and explain which findings are "
       "directly observed versus model-derived.", _EC.COMPLEX_SYNTHESIS.value,
       notes="Verbatim GLOBAL_ARCHITECTURE.md 'complex physician path' example."),
    _c("Compare the current PV loop directly observed versus the model-derived one.", _EC.COMPLEX_SYNTHESIS.value,
       category="ambiguous",
       notes="Fallback-miss hypothesis: the cascade checks DETERMINISTIC_COMPUTATION's "
             "'\\bpv loop\\b' pattern (bucket 4) before COMPLEX_SYNTHESIS's "
             "'\\bdirectly observed versus\\b' pattern (bucket 6), so 'pv loop' wins "
             "first even though this sentence is near-verbatim GLOBAL_ARCHITECTURE.md's "
             "own COMPLEX_SYNTHESIS example phrasing ('directly observed versus "
             "model-derived'). Human ground truth follows the doc's own example, not "
             "the cascade order."),
    _c("Compare recovery outcomes across the last three scenarios.", _EC.COMPLEX_SYNTHESIS.value,
       category="ambiguous",
       notes="Tests Agent 23's flagged hypothesis directly: 'recovery' is a SIMULATION "
             "cue checked (bucket 2) before COMPLEX_SYNTHESIS's 'compare' cue (bucket 6), "
             "so a retrospective, already-run comparison across scenarios plausibly gets "
             "misrouted to SIMULATION by the fallback. Human ground truth: this asks to "
             "compare/synthesize outcomes that already exist, not to run a new one."),

    # -- generative_explanation (3) --
    _c("Why did stroke volume fall in the experiment?", _EC.GENERATIVE_EXPLANATION.value,
       notes="Verbatim GLOBAL_ARCHITECTURE.md 'grounded explanation path' example."),
    _c("How does afterload reduction affect ejection fraction?", _EC.GENERATIVE_EXPLANATION.value),
    _c("Explain the drop in cardiac output after the last scenario.", _EC.GENERATIVE_EXPLANATION.value,
       category="ambiguous",
       notes="Fallback-miss hypothesis: contains 'scenario', a SIMULATION cue (bucket 2, "
             "checked before GENERATIVE_EXPLANATION's why/explain cue at bucket 7), so "
             "the cascade would likely misroute this to SIMULATION even though the verb "
             "is 'explain' (a request to explain something that already happened, not to "
             "run a new one)."),

    # -- clarification_required (2) --
    _c("this", _EC.CLARIFICATION_REQUIRED.value,
       notes="Single word; unambiguously too little information to route."),
    _c("what about it?", _EC.CLARIFICATION_REQUIRED.value,
       category="ambiguous",
       notes="Fallback-miss hypothesis: 3 words (len<=1 rule doesn't fire), and no other "
             "bucket's keyword list matches 'what about it' (it is not '\\bwhat is\\b'), "
             "so the cascade falls through to the GENERATIVE_EXPLANATION else-branch. "
             "Human ground truth: a bare referent with no resolvable antecedent needs "
             "clarification regardless of word count."),

    # -- insufficient_evidence (2) --
    _c("What was the ejection fraction three years before this patient's first visit?",
       _EC.INSUFFICIENT_EVIDENCE.value, context={"available_history_days": 30},
       category="ambiguous",
       notes="Judgment call, flagged explicitly: classify_intent routes from text alone, "
             "and text alone can't strictly prove data is missing — we label this "
             "INSUFFICIENT_EVIDENCE because the context makes clear no such historical "
             "record exists, on the reading that a real System-1 router would have "
             "access to the same context object the adapter methods accept. A stricter "
             "reading could instead call this DIRECT_STATE_READ that later fails "
             "downstream; noted as a limitation in decision-fixtures.md. The current "
             "fallback structurally CANNOT ever choose INSUFFICIENT_EVIDENCE — it does "
             "not appear anywhere in the cascade's elif chain — so this is guaranteed "
             "fallback-wrong by construction, independent of the judgment call above."),
    _c("What does the biopsy report say about interstitial fibrosis for this component?",
       _EC.INSUFFICIENT_EVIDENCE.value, context={"component_id": "septum", "has_biopsy_data": False},
       category="ambiguous",
       notes="Same structural fallback gap as above (INSUFFICIENT_EVIDENCE is unreachable "
             "by the current keyword cascade)."),

    # -- human_decision_required (2) --
    _c("Should we switch this patient from warfarin to a DOAC?", _EC.HUMAN_DECISION_REQUIRED.value,
       notes="A therapy choice — must never be answered by System-1 routing content, only "
             "routed to a human-decision-required path. Fallback cannot reach this class "
             "(not in the cascade); it would likely land on GENERATIVE_EXPLANATION or "
             "DIRECT_STATE_READ ('current'-free though, so probably the final else "
             "GENERATIVE_EXPLANATION), which is a real, structural miss."),
    _c("Which of these two ablation strategies should we pursue for this patient?",
       _EC.HUMAN_DECISION_REQUIRED.value,
       notes="Same structural fallback gap as above."),

    # -- unsupported (2) --
    _c("Export this twin as a DICOM file and fax it to the cath lab.", _EC.UNSUPPORTED.value,
       category="nonsense",
       notes="Not a capability BeatIT's tool registry exposes (no fax/DICOM-export tool). "
             "Fallback cannot reach UNSUPPORTED (not in the cascade)."),
    _c("What's the weather forecast for tomorrow?", _EC.UNSUPPORTED.value,
       category="nonsense",
       notes="Out-of-domain nonsense relative to a cardiac digital twin app. Fallback's "
             "cascade has no bucket for this and no final catch-all for out-of-domain "
             "text, so it falls to the GENERATIVE_EXPLANATION else-branch — a clear miss."),
]


# ---------------------------------------------------------------------------
# 2. select_tool_family — 8 TOOL_FAMILY_OPTIONS
# ---------------------------------------------------------------------------

_SELECT_TOOL_FAMILY: list[FixtureCase] = [
    # -- TWIN (4) --
    _c("What is the current ejection fraction for this component?", "TWIN",
       context={"component_id": "lv_free_wall"}),
    _c("Show me the latest snapshot of the twin.", "TWIN"),
    _c("Get the component report for the LV free wall.", "TWIN",
       context={"component_id": "lv_free_wall"}, category="ambiguous",
       notes="Structural fallback bug, not just a hypothesis: GLOBAL_ARCHITECTURE.md's "
             "'SINGLE TOOL REGISTRY' section lists `get_component_report` under the TWIN "
             "category explicitly. But select_tool_family's REPORT bucket ('\\breport\\b', "
             "bucket 6) is checked before the TWIN bucket (bucket 7), so any text "
             "containing the literal word 'report' about a component's own twin state "
             "gets misrouted to REPORT instead of TWIN."),
    _c("What's the ejection fraction on the current twin snapshot?", "TWIN"),

    # -- EVIDENCE (3) --
    _c("What's the source for this measurement?", "EVIDENCE"),
    _c("Show me the provenance of the ECG-derived HR.", "EVIDENCE"),
    _c("Cite where the EDV value came from.", "EVIDENCE"),

    # -- PHYSIOLOGY (3) --
    _c("Show me the PV loop for this component.", "PHYSIOLOGY", context={"component_id": "lv_free_wall"}),
    _c("What's the ECG state right now?", "PHYSIOLOGY",
       notes="'right now' avoids the literal 'current' keyword on purpose, to test "
             "whether ECG-state recall depends on that one word."),
    _c("Get the causal trace for the stroke volume drop.", "PHYSIOLOGY"),

    # -- EXPERIMENT (3) --
    _c("Run a scenario with reduced afterload.", "EXPERIMENT"),
    _c("Create a new shadow trial for this patient.", "EXPERIMENT"),
    _c("What if we increase preload by 15%?", "EXPERIMENT"),

    # -- COMPARE (3) --
    _c("Compare this snapshot to last week's.", "COMPARE", context={"snapshot_id": "snap-7"}),
    _c("Show me the pair comparison between scenario A and B.", "COMPARE"),
    _c("How does this component compare versus the baseline?", "COMPARE", context={"component_id": "septum"}),

    # -- UNCERTAINTY (3) --
    _c("What's the dominant assumption behind this ensemble?", "UNCERTAINTY", context={"ensemble_id": "ens-3"}),
    _c("Run the missing piece analysis for this case.", "UNCERTAINTY"),
    _c("What evidence would change this result the most?", "UNCERTAINTY"),

    # -- REPORT (3) --
    _c("Generate a physician brief for this case.", "REPORT"),
    _c("Create a computational report summarizing this run.", "REPORT"),
    _c("Give me a summary of this session.", "REPORT"),

    # -- NONE (3) --
    _c("Thanks, that's helpful!", "NONE"),
    _c("Hello, can you help me understand this app?", "NONE"),
    _c("Okay, got it.", "NONE"),

    # -- extra hard/hypothesis-targeted cases (5) --
    _c("What is the current guideline for anticoagulation after ablation?", "EVIDENCE",
       category="ambiguous",
       notes="Agent 23 hypothesis test (fallback-specialization doc, item 2): the word "
             "'current' is not exclusively a twin-state cue — this text asks about "
             "medical-literature guidance, not this patient's twin. No EVIDENCE keyword "
             "('evidence'/'source'/'provenance'/'cite') literally appears, so the "
             "fallback cascade falls through every bucket until 'current' fires the TWIN "
             "bucket (checked second-to-last) — a plausible over-routing to TWIN."),
    _c("What's the current time in UTC?", "NONE",
       category="nonsense",
       notes="Agent 23 hypothesis test: out-of-domain nonsense containing 'current'. "
             "Fallback almost certainly over-routes to TWIN via the bare '\\bcurrent\\b' "
             "pattern, since no other bucket matches and NONE is only the final else."),
    _c("Is the current build passing CI?", "NONE",
       category="nonsense",
       notes="Same 'current'-without-twin-meaning hypothesis, different out-of-domain "
             "(software engineering, not cardiology) framing."),
    _c("Compare the current PV loop directly observed versus the model-derived one.", "COMPARE",
       category="ambiguous",
       notes="Judgment call, flagged explicitly: PHYSIOLOGY (get_pv_loop) and COMPARE "
             "(get_comparison) are both defensible tool families for this text. We label "
             "COMPARE because the primary verb/action is 'compare X versus Y', which is "
             "exactly what the COMPARE category exists for per the registry description; "
             "PHYSIOLOGY is for reading a single state, not comparing two. Fallback likely "
             "picks PHYSIOLOGY instead, since '\\bpv loop\\b' (bucket 2) is checked before "
             "COMPARE (bucket 4)."),
    _c("Compare what the simulation predicts against the evidence for last month.", "COMPARE",
       category="ambiguous",
       notes="Judgment call: this text plausibly triggers EVIDENCE ('evidence' keyword, "
             "bucket 1, checked first), EXPERIMENT ('simulation' matches '\\bsimulat', "
             "bucket 3), and COMPARE ('compare', bucket 4) all at once. We label COMPARE "
             "because the sentence's main verb is 'compare' — the ask is fundamentally a "
             "cross-source comparison, not a request for either source alone. Fallback "
             "likely returns EVIDENCE since that bucket is checked first. See the matching "
             "needs_simulation/needs_evidence_retrieval fixtures below using this same "
             "text, which legitimately expect BOTH to be True — a case the two "
             "independent yes/no decisions handle fine even though select_tool_family, a "
             "single-choice decision, cannot pick two families at once."),
]


# ---------------------------------------------------------------------------
# 3. needs_evidence_retrieval — bool
# ---------------------------------------------------------------------------

_NEEDS_EVIDENCE_RETRIEVAL: list[FixtureCase] = [
    _c("Where did this EF value come from?", True),
    _c("Can you cite the source for the QTc measurement?", True),
    _c("What's the provenance of the echo-derived stroke volume?", True, category="jargon"),
    _c("Based on what data was this derived?", True),
    _c("Is this number directly observed or model-derived?", True, category="ambiguous",
       notes="Fallback-miss hypothesis: asks to distinguish observed-vs-derived, which is "
             "an evidence/provenance question in substance, but the fallback's keyword "
             "list (evidence/source/provenance/cite/citation/'where did...come from'/"
             "'based on what') has no match for 'directly observed or model-derived'."),
    _c("What's backing up this claim about reduced contractility?", True, category="ambiguous",
       notes="Fallback-miss hypothesis: 'backing up' is a natural-language paraphrase of "
             "'evidence for' with no literal keyword match."),
    _c("Show me the citation for this guideline recommendation.", True),
    _c("I want to see the raw echo report this was extracted from.", True, category="ambiguous",
       notes="Fallback-miss hypothesis: 'extracted from' implies provenance but doesn't "
             "match any literal keyword in the fallback's list."),
    _c("provenance pls", True, category="shorthand"),
    _c("evidence?", True, category="shorthand"),
    _c("What is the current EF?", False),
    _c("Run a recovery scenario.", False),
    _c("Thanks, got it!", False),
    _c("Compare this snapshot to last week's.", False, context={"snapshot_id": "snap-7"}),
    _c("Generate a physician brief.", False),
    _c("Why did stroke volume fall?", False, category="ambiguous",
       notes="Judgment call: an explanation draws on internal causal-trace data, but the "
             "direct ask here is 'why', not 'show me the source/provenance' — labeled "
             "False on the reading that GENERATIVE_EXPLANATION and EVIDENCE_RETRIEVAL are "
             "meant to be distinct paths per GLOBAL_ARCHITECTURE.md."),
    _c("What if we double the afterload?", False),
    _c("Calculate the cardiac output.", False),
    _c("This is concerning, is it dangerous?", False,
       notes="Triggers needs_physician_review_framing, not evidence retrieval — kept as a "
             "negative control to make sure the two decisions aren't conflated."),
    _c("current", False, category="nonsense"),
]


# ---------------------------------------------------------------------------
# 4. needs_simulation — bool
# ---------------------------------------------------------------------------

_NEEDS_SIMULATION: list[FixtureCase] = [
    _c("What if we reduce afterload by 20%?", True),
    _c("Run a recovery scenario for this patient.", True),
    _c("Simulate increased preload.", True),
    _c("Rerun the ensemble with updated priors.", True,
       notes="Unlike classify_intent's SIMULATION bucket, needs_simulation's fallback "
             "keyword list DOES include '\\brerun\\b', so the fallback is expected to get "
             "this one right — kept as a positive control / cross-check against the "
             "classify_intent fixture using the same text (which is expected to be a "
             "fallback miss there)."),
    _c("Start a shadow trial with these parameters.", True, category="ambiguous",
       notes="Fallback-miss hypothesis: 'shadow trial' is a real EXPERIMENT-category tool "
             "(run_shadow_trial) but is not in needs_simulation's fallback keyword list "
             "(what if/scenario/simulat/recovery/rerun/run experiment)."),
    _c("Run an experiment varying contractility.", True),
    _c("Project how this patient's numbers would look after 6 weeks of recovery.", True),
    _c("Model what happens if we halve the vessel resistance.", True, category="ambiguous",
       notes="Fallback-miss hypothesis: 'what happens if' is semantically identical to "
             "'what if' but does not match the fallback's literal '\\bwhat if\\b' pattern."),
    _c("Kick off a scenario run with the new baseline.", True),
    _c("Predict the outcome for a hypothetical medication-free recovery trajectory.", True,
       notes="'hypothetical' isn't a fallback keyword, but 'recovery' is, so the fallback "
             "is expected to get this right for the wrong/incomplete reason — worth noting "
             "in the evaluation as a right-answer-fragile-heuristic case, not a clean pass."),
    _c("What is the current EF?", False),
    _c("Where did this value come from?", False),
    _c("Compare this snapshot to last week's.", False, context={"snapshot_id": "snap-7"}),
    _c("Generate a report.", False),
    _c("Why did the ejection fraction change?", False),
    _c("Show me the ECG right now.", False),
    _c("I'm worried this looks abnormal.", False),
    _c("This is great, thanks!", False),
    _c("current", False, category="nonsense"),
    _c("What's the causal trace for the stroke volume drop that already happened?", False,
       category="ambiguous",
       notes="Explicitly distinguishes a request about an already-observed event from a "
             "request to run a new simulation; the word 'happened' signals past tense."),
]


# ---------------------------------------------------------------------------
# 5. needs_clarification — bool (context matters: referent-resolving ids)
# ---------------------------------------------------------------------------

_NEEDS_CLARIFICATION: list[FixtureCase] = [
    _c("this", True),
    _c("that", True),
    _c("what about it?", True, notes="Bare referent 'it', no resolving context id."),
    _c("fix this", True, context={}, notes="Bare referent 'this', no resolving context id."),
    _c("huh?", True, category="nonsense"),
    _c("can you look at that component here?", True,
       notes="Two bare referents ('that', 'here'), no resolving context id."),
    _c("update it please", True),
    _c("what does this mean", True, context={"snapshot_id": None},
       category="ambiguous",
       notes="Edge case: a referent-resolving key is present in context but its value is "
             "falsy (None) — `bool(context.get(key))` is False, so this should NOT count "
             "as a resolving context. Tests that the resolver checks truthiness, not just "
             "key presence."),
    _c("show me that one again", True),
    _c("hmm", True, category="nonsense"),
    _c("this", True, context={"component_id": "lv_free_wall"}, category="ambiguous",
       notes="Judgment call: even with a resolving component_id in context, a single "
             "BARE word still doesn't specify WHAT information is wanted (EF? PV loop? "
             "report?). Labeled True (needs_clarification) on the reasoning that "
             "word-count ambiguity about intent is independent of, and not resolved by, "
             "referent resolution. This matches the fallback's own unconditional "
             "single-word rule, so it is NOT a fallback-disagreement case — included to "
             "make that judgment call explicit rather than silently assumed."),
    _c("what is the ejection fraction for this component?", False,
       context={"component_id": "lv_free_wall"},
       notes="Bare referent 'this', but multi-word and a resolving component_id is set."),
    _c("show me the report for that scenario", False, context={"scenario_id": "scn-042"}),
    _c("compare this to the baseline", False, context={"snapshot_id": "snap-7"}),
    _c("what does this mean for the ensemble", False, context={"ensemble_id": "ens-3"}),
    _c("run it again with the same parameters", False, context={"scenario_id": "scn-9"}),
    _c("what is the current ejection fraction?", False, notes="No bare referent at all."),
    _c("calculate the cardiac output from HR and stroke volume", False),
    _c("generate a physician brief for this case", False, context={"patient_id": "pt-1"}),
    _c("why did stroke volume fall in the experiment", False),
    _c("that's helpful, thank you", False, category="ambiguous",
       notes="Fallback false-positive hypothesis: the regex '\\bthat\\b' matches the "
             "substring 'that' inside \"that's\" (word boundary falls on the apostrophe), "
             "so the fallback likely flags this pure pleasantry as needing clarification "
             "even though it plainly does not."),
]


# ---------------------------------------------------------------------------
# 6. needs_physician_review_framing — bool (context: audience short-circuit)
# ---------------------------------------------------------------------------

_NEEDS_PHYSICIAN_REVIEW_FRAMING: list[FixtureCase] = [
    _c("What is the current EF?", True, context={"audience": "physician"},
       notes="audience=='physician' short-circuits True regardless of text content."),
    _c("Show me the PV loop.", True, context={"audience": "physician"}),
    _c("This looks concerning, should I be worried?", True),
    _c("Is this ejection fraction abnormal?", True),
    _c("What's the risk here?", True),
    _c("What assumptions were made in this simulation?", True),
    _c("How uncertain is this estimate?", True),
    _c("Walk me through the evidence and assumptions behind this recommendation.", True,
       context={"audience": "physician"}, notes="Both the audience short-circuit and the keyword trigger fire."),
    _c("Should I be worried about this trend?", True),
    _c("This finding seems inconsistent with the guideline — how confident are we?", True,
       category="ambiguous",
       notes="Fallback-miss hypothesis: 'inconsistent'/'confident' aren't literal keyword "
             "matches (concerning/abnormal/should i be worried/risk/uncertain/assumption), "
             "but the text is clearly raising doubt about a finding and asking for "
             "confidence framing, which is exactly what this decision exists to gate."),
    _c("What is the current EF?", False, context={}),
    _c("Thanks, thats helpful!", False),
    _c("Run a recovery scenario.", False),
    _c("Generate a report.", False),
    _c("Compare this to last week.", False, context={"snapshot_id": "snap-1"}),
    _c("What if we reduce afterload?", False, context={"audience": "patient"},
       notes="audience is set but not 'physician' — should NOT short-circuit."),
    _c("Calculate the cardiac output.", False),
    _c("What's the causal trace for this?", False, context={"component_id": "septum"}),
    _c("hello", False, category="nonsense"),
    _c("Show me the ensemble result.", False, context={"audience": "general"}),
]


# ---------------------------------------------------------------------------
# 7. is_complex_reasoning_required — bool (word count > 18 OR synthesis cues)
# ---------------------------------------------------------------------------

_IS_COMPLEX_REASONING_REQUIRED: list[FixtureCase] = [
    _c("Summarize what changed over the last month and explain which findings are "
       "directly observed versus model-derived.", True,
       notes="Verbatim GLOBAL_ARCHITECTURE.md complex-synthesis example; long AND keyword match."),
    _c("Compare the current twin state to the baseline and identify which changes are "
       "clinically meaningful.", True,
       notes="'compare' plus an explicit additional synthesis ask ('identify which changes')."),
    _c("Which findings are directly attributable to the intervention versus natural "
       "variation over time?", True),
    _c("What's the trade-off between reducing afterload aggressively versus a more "
       "conservative titration approach?", True),
    _c("Directly observed versus model-derived: which values in this report should I "
       "trust more?", True),
    _c("Summarize the ensemble results and explain which assumptions drove the biggest "
       "spread in outcomes.", True),
    _c("Can you walk me through how the reduced afterload scenario compares to the "
       "baseline, which assumptions were used for both runs, and whether the resulting "
       "stroke volume change is clinically significant?", True,
       notes="Long AND contains compare/which — unambiguous multi-part synthesis ask."),
    _c("Explain whether these values are directly observed versus extrapolated by the "
       "ensemble model, and why the two might disagree.", True),
    _c("I noticed the stroke volume, ejection fraction, and cardiac output all shifted "
       "after the last two scenarios and the recovery run — can you help me understand "
       "which of those changes are related versus independent, and what's driving the "
       "biggest one?", True, notes="Long and genuinely multi-source synthesis; clean agreement case."),
    _c("What trade-offs should I weigh between running another ensemble now versus "
       "waiting for more evidence?", True),
    _c("Compare this scenario to the baseline.", False, context={"scenario_id": "scn-1"},
       category="ambiguous",
       notes="Fallback false-positive hypothesis: the bare '\\bcompare\\b' keyword fires "
             "regardless of sentence complexity, but a short, simple two-way compare "
             "answerable directly by the COMPARE tool is not 'complex reasoning' in the "
             "sense GLOBAL_ARCHITECTURE.md means (deep multi-source synthesis needing the "
             "NVIDIA LLM System-2 path) — contrast with the longer, genuinely synthetic "
             "'compare' fixtures above, which are labeled True."),
    _c("Could you please go ahead and just quickly tell me one more time what the "
       "current ejection fraction value is for this particular patient right now?", False,
       category="ambiguous",
       notes="Fallback false-positive hypothesis: word count is 26 (>18), so the "
             "fallback's length heuristic alone would flag this True, but this is a "
             "single simple direct-state-read question padded with filler/polite words "
             "('could you please', 'just quickly', 'one more time') — no multi-source "
             "synthesis is needed at all. This is the clearest length-heuristic false "
             "positive in the set."),
    _c("What is the current EF?", False),
    _c("Run a recovery scenario.", False),
    _c("Why did stroke volume fall?", False),
    _c("Generate a report.", False),
    _c("Thanks, that's helpful!", False),
    _c("Show me the PV loop.", False),
    _c("What's the causal trace for this component?", False, context={"component_id": "septum"}),
    _c("This is concerning, is it dangerous?", False,
       notes="Triggers needs_physician_review_framing, not complex reasoning — negative "
             "control to keep the two decisions distinct."),
]


# ---------------------------------------------------------------------------
# Registry + public loader API
# ---------------------------------------------------------------------------

_FIXTURES: dict[str, list[FixtureCase]] = {
    "classify_intent": _CLASSIFY_INTENT,
    "select_tool_family": _SELECT_TOOL_FAMILY,
    "needs_evidence_retrieval": _NEEDS_EVIDENCE_RETRIEVAL,
    "needs_simulation": _NEEDS_SIMULATION,
    "needs_clarification": _NEEDS_CLARIFICATION,
    "needs_physician_review_framing": _NEEDS_PHYSICIAN_REVIEW_FRAMING,
    "is_complex_reasoning_required": _IS_COMPLEX_REASONING_REQUIRED,
}

assert set(_FIXTURES) == set(DECISION_NAMES), "fixture registry drifted from DECISION_NAMES"


def load_fixtures(decision_name: str) -> list[FixtureCase]:
    """Return a fresh list copy of the labeled fixtures for one decision.

    Raises KeyError with the valid decision names listed if `decision_name`
    isn't one of `laya_adapter.LayaAdapter`'s 7 real public methods.
    """
    if decision_name not in _FIXTURES:
        raise KeyError(f"Unknown decision_name {decision_name!r}; valid names: {sorted(_FIXTURES)}")
    return list(_FIXTURES[decision_name])


def load_all_fixtures() -> dict[str, list[FixtureCase]]:
    """Return {decision_name: [FixtureCase, ...]} for all 7 decisions."""
    return {name: list(cases) for name, cases in _FIXTURES.items()}


def valid_labels(decision_name: str) -> set[Any]:
    """The set of valid `expected` values for a given decision's label space.

    `{True, False}` for the 5 yes/no decisions; the real enum/vocabulary
    values for the 2 choice decisions.
    """
    if decision_name == "classify_intent":
        return {item.value for item in ExecutionClass}
    if decision_name == "select_tool_family":
        return set(TOOL_FAMILY_OPTIONS)
    if decision_name in _YES_NO_DECISIONS:
        return {True, False}
    raise KeyError(f"Unknown decision_name {decision_name!r}; valid names: {sorted(_FIXTURES)}")


def total_fixture_count() -> int:
    return sum(len(cases) for cases in _FIXTURES.values())
