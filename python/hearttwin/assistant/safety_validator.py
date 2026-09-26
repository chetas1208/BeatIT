"""Unified pre/post safety validation for the BeatIT conversation assistant (Wave 2).

Implements the three GLOBAL_ARCHITECTURE.md guardrail-layer gates the future
unified assistant needs (see docs/assistant/GLOBAL_ARCHITECTURE.md "GUARDRAIL
LAYERS", "NUMERICAL CLAIM GATE"):

  * PRE_REQUEST  — ``classify_request_safety``: input-rail intent classification.
  * POST_RESPONSE — ``validate_numeric_claims``: output-rail numerical claim gate.
  * POST_RESPONSE — ``check_output_safety``: output-rail clinical-boundary gate.

This module does NOT replace either existing safety system. It is additive:

  * ``classify_request_safety`` calls the REAL rule-based classifier,
    ``_classify_intent_with_rules`` in
    python/hearttwin/agents/intake_agent.py:284-392, directly — it is
    imported, not reimplemented, so a fix or a new pattern added there is
    picked up here automatically. ``_merge_decisions``
    (intake_agent.py:395-413) already guarantees the LLM classifier can never
    soften a rule-based block; this module never calls the LLM classifier at
    all, so that guarantee is untouched. This module only ever *adds*
    detection for phrasings intake_agent's regexes miss (see
    ``_SUPPLEMENTAL_*_PATTERNS`` below) — it never narrows or skips a case
    intake_agent would already block.
  * ``check_output_safety`` is the UNION of the two independent output
    blocklists identified in docs/assistant/CHAT_SURFACE_AUDIT.md and
    docs/assistant/WAVE_1_HANDOFF.md:
      1. ``_OUTPUT_RED_FLAGS`` in python/hearttwin/copilot.py:59-74, plus the
         two other layers copilot.py's own ``_check_output_safety``
         (copilot.py:418-448) already runs on top of that list —
         ``check_request_safety``/``_BLOCKED_PATTERNS`` and
         ``validate_simulation_outputs``, both in python/hearttwin/safety.py.
      2. ``_BLOCK`` in python/hearttwin/careguard/copilot_agent.py:24-25.
    All four are imported live (no copy-pasted term lists) so this validator
    can never silently drift behind either source — see
    test_safety_validator.py's snapshot-count tripwire test for what happens
    if a source list grows without this file being reviewed.

See docs/assistant/wave2/safety-validation.md for the full design rationale,
the numeric-claim regex approach and its known gaps, and every place a
stricter-vs-permissive judgment call was made.
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from python.hearttwin.agents.intake_agent import IntentDecision, _classify_intent_with_rules
from python.hearttwin.careguard.copilot_agent import _BLOCK as _CAREGUARD_BLOCK
from python.hearttwin.copilot import _OUTPUT_RED_FLAGS
from python.hearttwin.safety import (
    DISCLAIMER,
    SafetyViolation,
    check_request_safety,
    strip_allowed_safety_phrases,
    validate_simulation_outputs,
)

# AGENTS.md SS1.4: "Every API response keeps the `safety_disclaimer`." This is
# the exact string copilot.py's `_with_disclaimer` stamps onto every action
# payload under the `safety_disclaimer` key — reused verbatim, never
# reworded. CareGuard uses a separate, shorter disclaimer
# ("Clinical decision support draft. Clinician review required.",
# careguard/copilot_agent.py:22) scoped to its own medication-safety domain;
# which of the two (or a merge) becomes canonical for the unified assistant
# is a later-wave decision per WAVE_1_HANDOFF.md item 4, not this module's call.
REQUIRED_SAFETY_DISCLAIMER = DISCLAIMER


# ---------------------------------------------------------------------------
# PRE_REQUEST: request-intent classification
# ---------------------------------------------------------------------------

RequestSafetyCategory = Literal["emergency", "diagnosis_request", "treatment_request", "normal"]


class RequestSafetyDecision(BaseModel):
    blocked: bool
    reason: Optional[str] = None
    category: RequestSafetyCategory
    requires_tool_grounding: bool


# Intents whose answer will normally contain canonical cardiac numbers/facts
# that should come from a deterministic tool call rather than free generation
# (feeds the NUMERICAL CLAIM GATE / provenance gate downstream). This is new
# classification, not present in intake_agent.py — intake_agent only decides
# allowed/blocked, not "should this be tool-grounded." Judgment call: kept
# conservative (only intents whose deterministic tool coverage is confirmed
# real per PHYSICIAN_WORKFLOWS.md) rather than defaulting every "normal"
# intent to tool-grounded, since forcing ungroundable intents through a tool
# gate would just produce spurious INSUFFICIENT_EVIDENCE results.
_GROUNDING_REQUIRED_INTENTS = {
    "physiology_explanation",
    "operation_simulation",
    "recovery_simulation",
    "educational_simulation",
    "report_structuring",
}

# --- Supplemental patterns -------------------------------------------------
# Everything below is ADDITIVE coverage for phrasings intake_agent.py's own
# regexes (intake_agent.py:289-350) do not match. Checked only when the real
# rule classifier did not already block the request, and only ever able to
# turn a "normal" classification into a blocked one — never the reverse.
# Ordered emergency > treatment > diagnosis, mirroring intake_agent.py's own
# check order (intake_agent.py:289,310,333).

# Judgment call (flagged for human review, see design note): intake_agent's
# emergency list requires an explicit "heart attack"/"emergency room"/"911"/
# "ambulance" phrase — a bare "I have crushing chest pain right now, can't
# breathe" would NOT match any of its patterns. Given AGENTS.md's instruction
# to err toward stricter/more-blocking on ambiguous cases, this list adds
# acute-symptom and self-harm phrasing that a cardiac-safety validator should
# treat as an emergency even without the word "emergency" itself.
_SUPPLEMENTAL_EMERGENCY_PATTERNS = [
    r"\bcan\'?t breathe\b",
    r"\bcant breathe\b",
    r"\bpassed out\b",
    r"\bfainted\b",
    r"\bcollapsed\b",
    r"\bsevere chest pain\b",
    r"\bcrushing chest pain\b",
    r"\bchest pain (?:right )?now\b",
    r"\bsuicidal\b",
    r"\b(?:want to|going to) (?:kill myself|end my life|end it all)\b",
    r"\bself[- ]harm\b",
]

# Judgment call: intake_agent's treatment list matches "medic(ine|ation)",
# "drug", "dose"/"dosage"/"dosing", "prescrib(e|ed|ing|tion)", but not the
# bare word "pill(s)" or common dose-adjustment phrasing ("skip a dose",
# "double my dose") that doesn't contain the literal string "dos".
_SUPPLEMENTAL_TREATMENT_PATTERNS = [
    r"\bpills?\b",
    r"\bskip (?:a |my )?dose\b",
    r"\bdouble (?:my |the )?dose\b",
    r"\bis it safe to take\b",
    r"\bcan i take\b",
    r"\bover[- ]the[- ]counter\b",
]

# Judgment call: intake_agent's diagnosis list requires "diagnos*", "do i
# have", "what do i have", "what disease", or "is this a condition/illness" —
# "what's wrong with me" and "am i sick" express the same request without
# matching any of those patterns.
_SUPPLEMENTAL_DIAGNOSIS_PATTERNS = [
    r"\bwhat\'?s wrong with me\b",
    r"\bwhats wrong with me\b",
    r"\bam i sick\b",
    r"\bwhat condition do i have\b",
    r"\bdo you think i have\b",
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _supplemental_category(normalized: str) -> tuple[RequestSafetyCategory, str] | None:
    if _contains_any(normalized, _SUPPLEMENTAL_EMERGENCY_PATTERNS):
        return "emergency", (
            "DualBeat cannot provide emergency triage. Use it only for educational "
            "cardiac simulation and report organization. If this is a real emergency, "
            "contact local emergency services."
        )
    if _contains_any(normalized, _SUPPLEMENTAL_TREATMENT_PATTERNS):
        return "treatment_request", (
            "DualBeat cannot provide medication or treatment guidance. Use it only "
            "for educational cardiac simulation and report organization."
        )
    if _contains_any(normalized, _SUPPLEMENTAL_DIAGNOSIS_PATTERNS):
        return "diagnosis_request", (
            "DualBeat cannot provide diagnostic interpretation. Use it only for "
            "educational cardiac simulation and report organization."
        )
    return None


_INTENT_TO_CATEGORY: dict[str, RequestSafetyCategory] = {
    "unsafe_emergency_triage": "emergency",
    "unsafe_treatment_request": "treatment_request",
    "unsafe_diagnosis_request": "diagnosis_request",
}


def classify_request_safety(text: str) -> RequestSafetyDecision:
    """PRE_REQUEST gate: classify + (only ever additively) block a request.

    Base decision comes straight from intake_agent.py's real, tested
    rule-based classifier (never copied/reimplemented). Supplemental regex
    coverage above can only turn an unblocked rule decision into a blocked
    one — it can never soften or skip a rule-based block, preserving the
    exact guarantee ``_merge_decisions`` gives intake_agent.py itself.
    """
    rule_decision: IntentDecision = _classify_intent_with_rules(text or "")

    if rule_decision.safety_level == "blocked":
        category = _INTENT_TO_CATEGORY.get(rule_decision.intent_class, "normal")
        return RequestSafetyDecision(
            blocked=True,
            reason=rule_decision.blocked_reason,
            category=category,
            requires_tool_grounding=False,
        )

    supplemental = _supplemental_category(_normalize(text))
    if supplemental is not None:
        category, reason = supplemental
        return RequestSafetyDecision(
            blocked=True,
            reason=reason,
            category=category,
            requires_tool_grounding=False,
        )

    requires_tool_grounding = rule_decision.intent_class in _GROUNDING_REQUIRED_INTENTS
    return RequestSafetyDecision(
        blocked=False,
        reason=None,
        category="normal",
        requires_tool_grounding=requires_tool_grounding,
    )


# ---------------------------------------------------------------------------
# POST_RESPONSE: numerical claim gate
# ---------------------------------------------------------------------------


class NumericMismatch(BaseModel):
    metric: str
    claimed_value: float
    field: Optional[str] = None
    canonical_value: Optional[float] = None


class NumericValidationResult(BaseModel):
    valid: bool
    mismatches: list[NumericMismatch] = Field(default_factory=list)


# Canonical field-name aliases per metric. copilot.py's own state snapshot
# (copilot.py:368-415, `_build_state_snapshot`) uses the *_pct/*_ml/*_l_min/
# *_mmhg/*_bpm/*_ms suffix convention; other Wave 2 tool results may flatten
# differently (e.g. bare "ef"), so each metric accepts a small alias set,
# matched after stripping non-alphanumeric characters and lowercasing.
_METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "EF": ("ejection_fraction_pct", "ef_pct", "ejection_fraction", "ef"),
    "SV": ("stroke_volume_ml", "sv_ml", "stroke_volume", "sv"),
    "CO": ("cardiac_output_l_min", "co_l_min", "cardiac_output", "co"),
    "MAP": ("map_mmhg", "mean_arterial_pressure_mmhg", "mean_arterial_pressure", "map"),
    "HR": ("heart_rate_bpm", "hr_bpm", "heart_rate", "hr"),
    "EDV": ("edv_ml", "end_diastolic_volume_ml", "end_diastolic_volume", "edv"),
    "ESV": ("esv_ml", "end_systolic_volume_ml", "end_systolic_volume", "esv"),
    "QTC": ("qtc_ms", "corrected_qt_ms", "qtc"),
}

# A number must be directly attached to the metric name via a connector word
# (is/of/=/:/was/at/~/approximately) — this trades a small amount of recall
# (see design note "known gaps": free-floating numbers near a metric name
# with no connector, e.g. "EF, 45%, was recorded" won't match) for precision,
# since bare 2-3 letter abbreviations like "CO"/"HR" would otherwise
# false-positive inside unrelated words/acronyms in free text.
def _metric_pattern(names: tuple[str, ...]) -> re.Pattern[str]:
    name_alt = "|".join(re.escape(n) for n in names)
    return re.compile(
        rf"\b(?:{name_alt})\b\s*(?:is|of|=|:|was|at|~)?\s*(?:approximately|about)?\s*"
        rf"(\d+(?:\.\d+)?)\s*%?",
        re.IGNORECASE,
    )


_CLAIM_PATTERNS: dict[str, re.Pattern[str]] = {
    "EF": _metric_pattern(("EF", "ejection fraction")),
    "SV": _metric_pattern(("SV", "stroke volume")),
    "CO": _metric_pattern(("CO", "cardiac output")),
    "MAP": _metric_pattern(("MAP", "mean arterial pressure")),
    "HR": _metric_pattern(("HR", "heart rate")),
    "EDV": _metric_pattern(("EDV", "end-diastolic volume", "end diastolic volume")),
    "ESV": _metric_pattern(("ESV", "end-systolic volume", "end systolic volume")),
    "QTC": _metric_pattern(("QTc", "QTC", "corrected QT")),
}

# Percentage-style metrics tolerate rounding; absolute-unit metrics get the
# same small fixed band per the task spec ("rounding/+/-0.5"). This is
# deliberately not tighter: the deterministic pipeline itself can present
# numbers rounded to varying precision, and this gate's job is to catch
# fabricated/unsupported values, not to police rounding.
_TOLERANCE = 0.5


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _lookup_canonical(canonical_payload: dict, metric: str) -> tuple[Optional[str], Optional[float]]:
    normalized = {_normalize_key(k): v for k, v in (canonical_payload or {}).items()}
    for alias in _METRIC_ALIASES[metric]:
        key = _normalize_key(alias)
        if key in normalized and normalized[key] is not None:
            try:
                return alias, float(normalized[key])
            except (TypeError, ValueError):
                continue
    return None, None


def validate_numeric_claims(generated_text: str, canonical_payload: dict) -> NumericValidationResult:
    """POST_RESPONSE gate: diff every numeric cardiac claim against canonical data.

    Any claimed metric absent from ``canonical_payload`` is flagged as an
    unsupported claim (``canonical_value=None``) rather than ignored — per
    GLOBAL_ARCHITECTURE.md's numerical claim gate, "Mismatch -> reject/
    regenerate/fallback. No exceptions."
    """
    mismatches: list[NumericMismatch] = []
    text = generated_text or ""

    for metric, pattern in _CLAIM_PATTERNS.items():
        for match in pattern.finditer(text):
            try:
                claimed = float(match.group(1))
            except (TypeError, ValueError):
                continue
            field, canonical_value = _lookup_canonical(canonical_payload, metric)
            if canonical_value is None:
                mismatches.append(
                    NumericMismatch(metric=metric, claimed_value=claimed, field=field, canonical_value=None)
                )
                continue
            if abs(claimed - canonical_value) > _TOLERANCE:
                mismatches.append(
                    NumericMismatch(
                        metric=metric,
                        claimed_value=claimed,
                        field=field,
                        canonical_value=canonical_value,
                    )
                )

    return NumericValidationResult(valid=not mismatches, mismatches=mismatches)


# ---------------------------------------------------------------------------
# POST_RESPONSE: output clinical-boundary gate (union of both blocklists)
# ---------------------------------------------------------------------------


class OutputSafetyDecision(BaseModel):
    blocked: bool
    reason: Optional[str] = None
    matched_terms: list[str] = Field(default_factory=list)


def check_output_safety(generated_text: str) -> OutputSafetyDecision:
    """POST_RESPONSE gate: union of copilot.py's and CareGuard's output checks.

    Runs, on the same text, every independent check either existing surface
    runs today:
      * copilot.py:418-448 ``_check_output_safety`` itself layers three
        checks — the shared regex matcher (safety.py ``check_request_safety``
        / ``_BLOCKED_PATTERNS``), the ``_OUTPUT_RED_FLAGS`` phrase list
        (copilot.py:59-74), and ``validate_simulation_outputs`` — all three
        are reproduced here via live imports.
      * careguard/copilot_agent.py's ``_BLOCK`` phrase list (line 24-25),
        written independently for the CareGuard analysis surface and never
        cross-checked against copilot.py's list until now.
    A hit on ANY layer blocks. Terms are live-imported, never copy-pasted, so
    this can't silently fall behind either source growing new coverage.
    """
    text = generated_text or ""
    matched_terms: list[str] = []

    checked = strip_allowed_safety_phrases(text)
    lowered = checked.lower()

    for phrase in _OUTPUT_RED_FLAGS:
        if phrase in lowered:
            matched_terms.append(f"copilot:{phrase}")

    for phrase in _CAREGUARD_BLOCK:
        if phrase in text.lower():
            matched_terms.append(f"careguard:{phrase}")

    try:
        check_request_safety(checked)
    except SafetyViolation as exc:
        matched_terms.append(f"regex:{exc.pattern}")

    matched_terms.extend(f"vocab:{warning}" for warning in validate_simulation_outputs({"answer": text}))

    blocked = bool(matched_terms)
    reason = None
    if blocked:
        reason = (
            "Output blocked: matched the unified clinical-boundary safety union "
            "(copilot.py output red flags + shared regex matcher + CareGuard blocklist)."
        )
    return OutputSafetyDecision(blocked=blocked, reason=reason, matched_terms=sorted(set(matched_terms)))
