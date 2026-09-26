"""Laya System-1 adapter — bounded, non-clinical routing/gating decisions only.

Laya (Apache-2.0, github.com/NandhaKishorM/laya) is a fast, non-autoregressive
typed-decision encoder (`choice` / `score` / `noul` heads evaluated in one
forward pass) that BeatIT may use ONLY as its System-1 fast-decision layer —
see docs/assistant/GLOBAL_ARCHITECTURE.md ("SYSTEM-1 VS SYSTEM-2") and
docs/assistant/LAYA_RESEARCH.md.

HARD BOUNDARY (see GLOBAL_ARCHITECTURE.md "LAYA'S ROLE IN IMPORTANT
DECISIONS" and LAYA_RESEARCH.md "Recommended Integration Boundaries"): Laya
may decide software/routing questions only — intent, tool family, whether
evidence/simulation/clarification/physician-review-framing is needed, and
simple-vs-complex reasoning triage. Laya must NEVER decide diagnosis,
treatment, medication, emergency triage, or medical safety. This module
therefore exposes only named, bounded decision methods; there is
deliberately no generic "ask Laya anything" entry point, so a caller cannot
route an open clinical question through this adapter and treat the answer
as authoritative.

Calibration caveat (LAYA_RESEARCH.md "Calibration Campaign Prerequisites"):
Laya's own fine-tuned-checkpoint benchmark shows HIGHER accuracy (0.766)
but WORSE calibration (ECE 0.213) than the stated Jev baseline (ECE 0.144).
A raw Laya probability is not a calibrated confidence. Every decision below
therefore reports `raw_score` (never "confidence") plus a hardcoded
`calibration_status="uncalibrated"`, until BeatIT's own calibration
campaign (Wave 5) says otherwise — see docs/assistant/wave2/laya-integration.md.

Laya is not reachable from this environment. If it is unconfigured, or a
real call fails for any reason (timeout, connection error, malformed
response), every method falls through to a deterministic, clearly-labeled
fallback heuristic. The adapter never raises and never blocks the caller.

Env vars:
  LAYA_ENABLED         - "true" to attempt real Laya HTTP calls (default: false)
  LAYA_BASE_URL        - base URL of a running `laya-serve` instance
  LAYA_API_KEY         - optional bearer token; never logged, including in errors
  LAYA_TIMEOUT_SECONDS - per-call timeout in seconds (default: 2.5)
"""

from __future__ import annotations

import os
import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from python.hearttwin.assistant.schemas import ExecutionClass
from python.hearttwin.tools.env_config import env_bool

_DEFAULT_TIMEOUT_SECONDS = 2.5
_SYSTEMONE_PATH = "/v1/systemone"

DecisionSource = Literal["laya", "fallback"]
CalibrationStatus = Literal["uncalibrated"]


# ---------------------------------------------------------------------------
# Typed decision results (mirrors Laya's choice/score/noul decision heads)
# ---------------------------------------------------------------------------


class ChoiceDecision(BaseModel):
    """One of N labeled options was chosen."""

    decision_name: str
    options: list[str]
    chosen: str
    raw_score: Optional[float] = None
    source: DecisionSource
    calibration_status: CalibrationStatus = "uncalibrated"
    warnings: list[str] = Field(default_factory=list)


class YesNoDecision(BaseModel):
    """A bounded yes/no ("noul") decision."""

    decision_name: str
    answer: bool
    raw_score: Optional[float] = None
    source: DecisionSource
    calibration_status: CalibrationStatus = "uncalibrated"
    warnings: list[str] = Field(default_factory=list)


class ScoreDecision(BaseModel):
    """A bounded numeric ("score") decision.

    Modeled here for parity with Laya's real typed-decision API shape
    (choice/score/noul) even though no named public method returns one yet.
    Add a named method only for a bounded, non-clinical numeric routing
    value (e.g. a queue-priority weight) — never a clinical score.
    """

    decision_name: str
    value: float
    min_value: float = 0.0
    max_value: float = 1.0
    source: DecisionSource
    calibration_status: CalibrationStatus = "uncalibrated"
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Env-guarded config
# ---------------------------------------------------------------------------


def is_configured() -> bool:
    """True only when explicitly enabled and a base URL is set.

    Mirrors the VISTA3D adapter's opt-in pattern (tools/vista3d_client.py):
    an unset/false LAYA_ENABLED must never attempt a network call, even if a
    stray LAYA_BASE_URL is present in the environment.
    """
    if not env_bool("LAYA_ENABLED", False):
        return False
    return bool(_base_url())


def _base_url() -> str:
    return os.environ.get("LAYA_BASE_URL", "").strip().rstrip("/")


def _api_key() -> str:
    return os.environ.get("LAYA_API_KEY", "").strip()


def _timeout() -> float:
    raw = os.environ.get("LAYA_TIMEOUT_SECONDS")
    try:
        return float(raw) if raw else _DEFAULT_TIMEOUT_SECONDS
    except ValueError:
        return _DEFAULT_TIMEOUT_SECONDS


def _headers() -> dict[str, str]:
    key = _api_key()
    return {"Authorization": f"Bearer {key}"} if key else {}


# ---------------------------------------------------------------------------
# Wire call — POST /v1/systemone
#
# The exact request/response JSON body could not be read from source during
# Wave 1 research (LAYA_RESEARCH.md: "the literal request/response JSON body
# was not present in the fetched excerpts"). Only the Python-level shape
# (`router.predict(state, questions)` -> `answers[name][type]`) and the
# "Jev-wire-compatible" claim are confirmed. This builds the request on that
# documented shape and parses the response defensively, since it cannot be
# verified against a live server in this environment. ANY failure — disabled
# config, connection error, timeout, unexpected schema — returns None so the
# caller always falls through to its deterministic fallback.
# ---------------------------------------------------------------------------


async def _call_systemone(
    decision_name: str,
    decision_type: Literal["choice", "noul"],
    text: str,
    context: dict[str, Any] | None,
    *,
    options: list[str] | None = None,
    instructions: str,
) -> dict[str, Any] | None:
    if not is_configured():
        return None
    try:
        import httpx  # imported lazily so the dependency stays optional at import time

        criteria: dict[str, Any] = {"options": list(options)} if options else {}
        payload = {
            "state": {"text": text, **(context or {})},
            "questions": {
                decision_name: {
                    "type": decision_type,
                    "instructions": instructions,
                    "criteria": criteria,
                }
            },
        }
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            resp = await client.post(f"{_base_url()}{_SYSTEMONE_PATH}", headers=_headers(), json=payload)
        resp.raise_for_status()
        body = resp.json()
        answers = body.get("answers", body) if isinstance(body, dict) else {}
        answer = answers.get(decision_name) if isinstance(answers, dict) else None
        return answer if isinstance(answer, dict) else None
    except Exception:  # noqa: BLE001 — any failure degrades to the deterministic fallback; never raise, never log the API key
        return None


def _parse_choice_answer(answer: dict[str, Any], options: list[str]) -> Optional[tuple[str, Optional[float]]]:
    raw_choice = answer.get("choice", answer.get("value"))
    if isinstance(raw_choice, dict):
        raw_choice = raw_choice.get("value") or raw_choice.get("label")
    if raw_choice is None:
        return None
    chosen = str(raw_choice)
    if chosen not in options:
        return None
    return chosen, _coerce_float(answer.get("score", answer.get("probability", answer.get("confidence"))))


def _parse_noul_answer(answer: dict[str, Any]) -> Optional[tuple[bool, Optional[float]]]:
    raw = answer.get("noul", answer.get("answer", answer.get("value")))
    score = _coerce_float(answer.get("score", answer.get("probability", answer.get("confidence"))))
    if isinstance(raw, bool):
        return raw, score
    if isinstance(raw, (int, float)):
        return raw >= 0.5, score
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in ("yes", "true", "1"):
            return True, score
        if normalized in ("no", "false", "0"):
            return False, score
    return None


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Fallback vocabularies
# ---------------------------------------------------------------------------

# Reuses the canonical execution-class vocabulary already defined for the
# unified assistant (python/hearttwin/assistant/schemas.py) rather than
# inventing a second one — GLOBAL_ARCHITECTURE.md forbids competing
# vocabularies for the same concept.
_INTENT_OPTIONS: list[str] = [item.value for item in ExecutionClass]

# GLOBAL_ARCHITECTURE.md "SINGLE TOOL REGISTRY" categories, plus NONE for
# "no tool call needed" (e.g. a pure conversational follow-up).
_TOOL_FAMILY_OPTIONS: list[str] = [
    "TWIN",
    "EVIDENCE",
    "PHYSIOLOGY",
    "EXPERIMENT",
    "COMPARE",
    "UNCERTAINTY",
    "REPORT",
    "NONE",
]

_CONTEXT_REFERENT_KEYS = ("patient_id", "snapshot_id", "component_id", "scenario_id", "ensemble_id", "pair_id")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _fallback_warning() -> list[str]:
    return ["Laya unavailable; used deterministic keyword fallback"]


def _fallback_classify_intent(text: str, context: dict[str, Any] | None) -> ChoiceDecision:
    """Keyword router over BeatIT's own execution-class vocabulary.

    Ordered so unambiguous, high-precision cues (simulation/evidence/report
    keywords) are checked before the broad, low-precision "why/explain"
    bucket — a wrong DIRECT_STATE_READ vs GENERATIVE_EXPLANATION guess just
    costs a retry (per LAYA_RESEARCH.md's "MAY decide" list), so recall isn't
    tuned aggressively; this is the safety net, not the product.
    """
    normalized = _normalize(text)
    if not normalized or len(normalized.split()) <= 1:
        chosen = ExecutionClass.CLARIFICATION_REQUIRED.value
    elif _contains_any(normalized, [r"\bwhat if\b", r"\bscenario\b", r"\bsimulat", r"\brecovery\b", r"\brun\b.*\bexperiment\b"]):
        chosen = ExecutionClass.SIMULATION.value
    elif _contains_any(normalized, [r"\bevidence\b", r"\bsource\b", r"\bprovenance\b", r"\bwhere (did|does)\b.*\bcome from\b"]):
        chosen = ExecutionClass.EVIDENCE_RETRIEVAL.value
    elif _contains_any(normalized, [r"\bpv loop\b", r"\becg\b", r"\bcalculate\b", r"\bcompute\b", r"\bhemodynamic"]):
        chosen = ExecutionClass.DETERMINISTIC_COMPUTATION.value
    elif _contains_any(normalized, [r"\breport\b", r"\bbrief\b", r"\bartifact\b", r"\bgenerate (a |an )?(pdf|document)\b"]):
        chosen = ExecutionClass.ARTIFACT_GENERATION.value
    elif _contains_any(normalized, [r"\bcompare\b", r"\bsummariz.*\band\b", r"\bdirectly observed versus\b", r"\bover the last (week|month|year)\b"]):
        chosen = ExecutionClass.COMPLEX_SYNTHESIS.value
    elif _contains_any(normalized, [r"\bwhy\b", r"\bhow does\b", r"\bexplain\b"]):
        chosen = ExecutionClass.GENERATIVE_EXPLANATION.value
    elif _contains_any(normalized, [r"\bwhat is\b", r"\bcurrent\b", r"\bshow me\b", r"\bget\b"]):
        chosen = ExecutionClass.DIRECT_STATE_READ.value
    else:
        chosen = ExecutionClass.GENERATIVE_EXPLANATION.value
    return ChoiceDecision(
        decision_name="classify_intent",
        options=_INTENT_OPTIONS,
        chosen=chosen,
        raw_score=None,
        source="fallback",
        warnings=_fallback_warning(),
    )


def _fallback_select_tool_family(text: str, context: dict[str, Any] | None) -> ChoiceDecision:
    normalized = _normalize(text)
    if _contains_any(normalized, [r"\bevidence\b", r"\bsource\b", r"\bprovenance\b", r"\bcite\b"]):
        chosen = "EVIDENCE"
    elif _contains_any(normalized, [r"\bpv loop\b", r"\becg\b", r"\bcausal\b", r"\bhemodynamic"]):
        chosen = "PHYSIOLOGY"
    elif _contains_any(normalized, [r"\bscenario\b", r"\bsimulat", r"\bensemble\b", r"\bshadow trial\b", r"\bwhat if\b"]):
        chosen = "EXPERIMENT"
    elif _contains_any(normalized, [r"\bcompare\b", r"\bpair\b", r"\bversus\b", r"\bvs\.?\b"]):
        chosen = "COMPARE"
    elif _contains_any(normalized, [r"\buncertain", r"\bmissing piece\b", r"\bwhat evidence would\b", r"\bdominant assumption"]):
        chosen = "UNCERTAINTY"
    elif _contains_any(normalized, [r"\breport\b", r"\bbrief\b", r"\bsummary\b"]):
        chosen = "REPORT"
    elif _contains_any(normalized, [r"\btwin\b", r"\bsnapshot\b", r"\bcomponent\b", r"\bef\b", r"\bejection fraction\b", r"\bcurrent\b"]):
        chosen = "TWIN"
    else:
        chosen = "NONE"
    return ChoiceDecision(
        decision_name="select_tool_family",
        options=_TOOL_FAMILY_OPTIONS,
        chosen=chosen,
        raw_score=None,
        source="fallback",
        warnings=_fallback_warning(),
    )


def _fallback_needs_evidence_retrieval(text: str, context: dict[str, Any] | None) -> YesNoDecision:
    normalized = _normalize(text)
    answer = _contains_any(
        normalized,
        [r"\bevidence\b", r"\bsource\b", r"\bprovenance\b", r"\bcite\b", r"\bcitation\b", r"\bwhere (did|does)\b.*\bcome from\b", r"\bbased on what\b"],
    )
    return YesNoDecision(decision_name="needs_evidence_retrieval", answer=answer, raw_score=None, source="fallback", warnings=_fallback_warning())


def _fallback_needs_simulation(text: str, context: dict[str, Any] | None) -> YesNoDecision:
    normalized = _normalize(text)
    answer = _contains_any(
        normalized,
        [r"\bwhat if\b", r"\bscenario\b", r"\bsimulat", r"\brecovery\b", r"\brerun\b", r"\brun (an? )?experiment\b"],
    )
    return YesNoDecision(decision_name="needs_simulation", answer=answer, raw_score=None, source="fallback", warnings=_fallback_warning())


def _fallback_needs_clarification(text: str, context: dict[str, Any] | None) -> YesNoDecision:
    """True when the request is too short/ambiguous to route safely.

    Two independent triggers, matched to the "unclear" handling already used
    by python/hearttwin/agents/intake_agent.py's rule-based classifier:
    (1) near-empty or single-word input, or (2) a bare referent ("this",
    "that", "it", "here") with no context id to resolve it against — the
    same resolution rule GLOBAL_ARCHITECTURE.md's CONTEXT ARCHITECTURE
    describes for the assistant's memory of "this"/"here".
    """
    normalized = _normalize(text)
    if not normalized or len(normalized.split()) <= 1:
        return YesNoDecision(decision_name="needs_clarification", answer=True, raw_score=None, source="fallback", warnings=_fallback_warning())
    has_bare_referent = _contains_any(normalized, [r"\bthis\b", r"\bthat\b", r"\bit\b", r"\bhere\b"])
    has_resolving_context = bool(context) and any(context.get(key) for key in _CONTEXT_REFERENT_KEYS)
    answer = has_bare_referent and not has_resolving_context
    return YesNoDecision(decision_name="needs_clarification", answer=answer, raw_score=None, source="fallback", warnings=_fallback_warning())


def _fallback_needs_physician_review_framing(text: str, context: dict[str, Any] | None) -> YesNoDecision:
    """True in physician audience mode, or when the text touches
    uncertainty/risk language that GLOBAL_ARCHITECTURE.md's physician-support
    policy says should carry extra evidence/assumption framing — this never
    decides whether something IS risky, only whether the response should be
    framed with that density."""
    audience = (context or {}).get("audience")
    if audience == "physician":
        return YesNoDecision(decision_name="needs_physician_review_framing", answer=True, raw_score=None, source="fallback", warnings=_fallback_warning())
    normalized = _normalize(text)
    answer = _contains_any(normalized, [r"\bconcerning\b", r"\babnormal\b", r"\bshould i be worried\b", r"\brisk\b", r"\buncertain", r"\bassumption\b"])
    return YesNoDecision(decision_name="needs_physician_review_framing", answer=answer, raw_score=None, source="fallback", warnings=_fallback_warning())


def _fallback_is_complex_reasoning_required(text: str, context: dict[str, Any] | None) -> YesNoDecision:
    """True for multi-part/comparative asks that need synthesis across
    sources (GLOBAL_ARCHITECTURE.md's COMPLEX_SYNTHESIS example query),
    approximated here by length and comparison/synthesis keywords rather
    than any semantic understanding — a false "True" only costs an
    unnecessarily deep model call, never a safety failure."""
    normalized = _normalize(text)
    word_count = len(normalized.split())
    answer = word_count > 18 or _contains_any(
        normalized,
        [r"\bcompare\b", r"\bsummariz.*\band\b", r"\bwhich (findings|results) are\b", r"\btrade-?off\b", r"\bdirectly observed versus\b"],
    )
    return YesNoDecision(decision_name="is_complex_reasoning_required", answer=answer, raw_score=None, source="fallback", warnings=_fallback_warning())


# ---------------------------------------------------------------------------
# Public adapter
# ---------------------------------------------------------------------------


class LayaAdapter:
    """Bounded System-1 decision client.

    Every method answers exactly one software-routing question named in
    GLOBAL_ARCHITECTURE.md's "System 1 — Laya" list. There is intentionally
    no generic method that accepts an arbitrary clinical question.
    """

    async def classify_intent(self, text: str, context: dict[str, Any] | None = None) -> ChoiceDecision:
        answer = await _call_systemone(
            "classify_intent",
            "choice",
            text,
            context,
            options=_INTENT_OPTIONS,
            instructions="Pick exactly one BeatIT execution class that best routes this request.",
        )
        if answer is not None:
            parsed = _parse_choice_answer(answer, _INTENT_OPTIONS)
            if parsed is not None:
                chosen, score = parsed
                return ChoiceDecision(decision_name="classify_intent", options=_INTENT_OPTIONS, chosen=chosen, raw_score=score, source="laya")
        return _fallback_classify_intent(text, context)

    async def select_tool_family(self, text: str, context: dict[str, Any] | None = None) -> ChoiceDecision:
        answer = await _call_systemone(
            "select_tool_family",
            "choice",
            text,
            context,
            options=_TOOL_FAMILY_OPTIONS,
            instructions="Pick exactly one BeatIT tool-registry category (or NONE) that should handle this request.",
        )
        if answer is not None:
            parsed = _parse_choice_answer(answer, _TOOL_FAMILY_OPTIONS)
            if parsed is not None:
                chosen, score = parsed
                return ChoiceDecision(decision_name="select_tool_family", options=_TOOL_FAMILY_OPTIONS, chosen=chosen, raw_score=score, source="laya")
        return _fallback_select_tool_family(text, context)

    async def needs_evidence_retrieval(self, text: str, context: dict[str, Any] | None = None) -> YesNoDecision:
        answer = await _call_systemone(
            "needs_evidence_retrieval",
            "noul",
            text,
            context,
            instructions="Does answering this request require retrieving provenance/evidence records?",
        )
        if answer is not None:
            parsed = _parse_noul_answer(answer)
            if parsed is not None:
                value, score = parsed
                return YesNoDecision(decision_name="needs_evidence_retrieval", answer=value, raw_score=score, source="laya")
        return _fallback_needs_evidence_retrieval(text, context)

    async def needs_simulation(self, text: str, context: dict[str, Any] | None = None) -> YesNoDecision:
        answer = await _call_systemone(
            "needs_simulation",
            "noul",
            text,
            context,
            instructions="Does answering this request require running a deterministic scenario/recovery simulation?",
        )
        if answer is not None:
            parsed = _parse_noul_answer(answer)
            if parsed is not None:
                value, score = parsed
                return YesNoDecision(decision_name="needs_simulation", answer=value, raw_score=score, source="laya")
        return _fallback_needs_simulation(text, context)

    async def needs_clarification(self, text: str, context: dict[str, Any] | None = None) -> YesNoDecision:
        answer = await _call_systemone(
            "needs_clarification",
            "noul",
            text,
            context,
            instructions="Is this request too ambiguous or underspecified to route safely without asking the user a clarifying question?",
        )
        if answer is not None:
            parsed = _parse_noul_answer(answer)
            if parsed is not None:
                value, score = parsed
                return YesNoDecision(decision_name="needs_clarification", answer=value, raw_score=score, source="laya")
        return _fallback_needs_clarification(text, context)

    async def needs_physician_review_framing(self, text: str, context: dict[str, Any] | None = None) -> YesNoDecision:
        answer = await _call_systemone(
            "needs_physician_review_framing",
            "noul",
            text,
            context,
            instructions="Should the response be framed with physician-review evidence density (assumptions, provenance, uncertainty) per BeatIT's physician-support policy?",
        )
        if answer is not None:
            parsed = _parse_noul_answer(answer)
            if parsed is not None:
                value, score = parsed
                return YesNoDecision(decision_name="needs_physician_review_framing", answer=value, raw_score=score, source="laya")
        return _fallback_needs_physician_review_framing(text, context)

    async def is_complex_reasoning_required(self, text: str, context: dict[str, Any] | None = None) -> YesNoDecision:
        answer = await _call_systemone(
            "is_complex_reasoning_required",
            "noul",
            text,
            context,
            instructions="Does this request require deep multi-source synthesis (vs. a simple explanation or a direct state read)?",
        )
        if answer is not None:
            parsed = _parse_noul_answer(answer)
            if parsed is not None:
                value, score = parsed
                return YesNoDecision(decision_name="is_complex_reasoning_required", answer=value, raw_score=score, source="laya")
        return _fallback_is_complex_reasoning_required(text, context)
