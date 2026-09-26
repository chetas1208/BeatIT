"""Decision policy for when to trust a Laya/fallback routing decision (Wave 5).

Context (see docs/assistant/GLOBAL_ARCHITECTURE.md "LAYA EVALUATION
REQUIREMENT" and "SYSTEM-1 (Laya) VS SYSTEM-2"): the orchestrator
(``orchestrator.py``) currently uses every ``LayaAdapter`` decision — whether
it came from a real Laya call or the deterministic keyword fallback —
directly, with no confidence gating at all. This module defines, for each of
the 7 named decision types in ``laya_adapter.py``, a policy for when that
decision should instead be treated as "uncertain" so the orchestrator can
prefer a more conservative execution class (typically
``CLARIFICATION_REQUIRED``, or ``INSUFFICIENT_EVIDENCE`` in the tool-dispatch
path) rather than confidently acting on a possibly-wrong route.

This module does NOT edit ``orchestrator.py`` — see the module docstring
there and docs/assistant/wave5/decision-policy.md "Integration point" for the
exact call site a follow-up wave should wire this into. It also does NOT
touch ``laya_adapter.py``; it only consumes the ``decision_name``/``source``
vocabulary already defined there.

Why "confidence" here means per-decision-type historical accuracy, not a
per-call score: a real Laya call carries a ``raw_score``, but
``laya_adapter.py``'s own module docstring already establishes that score is
UNCALIBRATED (ECE 0.213) and must never be read as a probability of
correctness. The deterministic fallback path has no score at all — it is a
regex/keyword match with no notion of "how sure" a particular call is. The
only honest confidence signal for either source is measured, ex-post
accuracy for that *decision type* on BeatIT fixtures (the "LAYA EVALUATION
REQUIREMENT" metrics: accuracy, confusion matrix, Brier score, ECE,
abstention, false-high-confidence rate). This module gates on that, per
decision type, not on any individual call's score.

Numbers status: UPDATED during Wave 5 integration.
``docs/assistant/wave5/laya-evaluation.md`` now exists — Agent 22 ran the
deterministic fallback (the path actually live in production; Laya itself
is not enabled by default) against Agent 21's 160-example fixture set. Every
``accuracy`` below is now ``AccuracySource.MEASURED`` from that real run, not
a guess. ``defer_threshold`` stays at the original policy choice (0.70) —
that's a threshold decision, not a measurement, and ``with_measured_accuracy``
deliberately only ever replaces ``accuracy``/``source``/``reference``/``note``.
Net effect: 6 of 7 decision types clear the threshold as measured
(``is_trustworthy`` True); ``classify_intent`` measured at 58.6%, the one
type that does not — see its field's note below.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Literal

from python.hearttwin.assistant.laya_adapter import DecisionSource

# ---------------------------------------------------------------------------
# Clinical-authority structural guard
#
# GLOBAL_ARCHITECTURE.md and laya_adapter.py's module docstring both state
# Laya/fallback decisions are software-routing signals only and are never
# clinically authoritative. Diagnosis/treatment/medication/emergency-triage
# blocking is intake_agent.py's rule-based classifier
# (safety_validator.classify_request_safety), which runs BEFORE this policy
# (and before Laya) in the orchestrator pipeline and is untouched by this
# module. Those terms are therefore not, and must never become, valid
# `decision_name` values here. This is enforced structurally (a restricted
# Enum + a runtime assertion in `should_defer_to_clarification`), not just by
# comment, so a future misuse attempt (e.g. someone adding a
# "should_prescribe" decision type to this file) fails loudly at call time
# instead of silently gating a clinical decision.
# ---------------------------------------------------------------------------


class DecisionType(str, Enum):
    """The exact 7 decision methods LayaAdapter exposes — see laya_adapter.py.

    Deliberately closed (an Enum, not a bare `str`) so a typo or a
    newly-invented decision name can't silently produce a permissive
    "unknown decision type, default to trusted" policy — see
    `should_defer_to_clarification`'s handling of an unrecognized name.
    """

    CLASSIFY_INTENT = "classify_intent"
    SELECT_TOOL_FAMILY = "select_tool_family"
    NEEDS_EVIDENCE_RETRIEVAL = "needs_evidence_retrieval"
    NEEDS_SIMULATION = "needs_simulation"
    NEEDS_CLARIFICATION = "needs_clarification"
    NEEDS_PHYSICIAN_REVIEW_FRAMING = "needs_physician_review_framing"
    IS_COMPLEX_REASONING_REQUIRED = "is_complex_reasoning_required"


# Names that must NEVER be accepted as a `decision_name` anywhere in this
# module, regardless of the enum above — defense in depth against a future
# edit that widens `DecisionType` or bypasses it with a raw string. Matched
# as substrings (case-insensitive) so "diagnose_condition",
# "treatment_plan", "medication_dose", "emergency_triage_level" etc. are all
# caught, not just exact words.
_CLINICAL_AUTHORITY_TERMS: tuple[str, ...] = (
    "diagnos",
    "treatment",
    "treat",
    "medicat",
    "dosage",
    "dose",
    "prescri",
    "emergency",
    "triage",
)


class ClinicalAuthorityRefused(RuntimeError):
    """Raised when this policy module is asked to gate a clinical decision.

    This module has zero clinical authority (see GLOBAL_ARCHITECTURE.md
    "SYSTEM-1 (Laya) VS SYSTEM-2" and "Decision support object" — no
    `recommended_treatment` field, ever). Diagnosis/treatment/medication/
    emergency-triage blocking already happens deterministically in
    intake_agent.py / safety_validator.py and must never be reachable
    through, or influenced by, this Laya-routing-confidence policy.
    """


def _reject_clinical_authority_misuse(decision_name: str) -> None:
    normalized = decision_name.strip().lower()
    for term in _CLINICAL_AUTHORITY_TERMS:
        if term in normalized:
            raise ClinicalAuthorityRefused(
                f"Refusing to gate {decision_name!r}: this policy module has no clinical "
                "authority. Diagnosis/treatment/medication/emergency-triage blocking is "
                "handled by safety_validator.classify_request_safety (rule-based, runs "
                "before Laya) — it is not, and must never become, a Laya decision type."
            )


# ---------------------------------------------------------------------------
# Per-decision-type accuracy / policy
# ---------------------------------------------------------------------------


class AccuracySource(str, Enum):
    """Where a decision type's accuracy number came from — always surfaced
    in `get_policy_summary()` so nobody mistakes a placeholder for data."""

    MEASURED = "measured"
    PROVISIONAL_DEFAULT = "provisional-default"


# Below this fraction, a decision TYPE's own historical accuracy is treated
# as too unreliable to act on confidently — the orchestrator should bias
# toward asking rather than assuming for that type, regardless of which call
# produced this particular answer. Provisional value per the task's own
# worked example ("always defer to clarification below 70% fallback-observed
# accuracy"); not derived from any measurement — see module docstring.
_PROVISIONAL_DEFAULT_THRESHOLD = 0.70

# The evaluation doc this policy is meant to be grounded in once it exists.
# Referenced by name (not imported) since it doesn't exist in this repo yet
# — see module docstring "Numbers status".
_PENDING_EVALUATION_DOC = "docs/assistant/wave5/laya-evaluation.md"


@dataclass(frozen=True)
class DecisionAccuracy:
    """One decision type's measured-or-provisional accuracy and threshold.

    `accuracy` is the historical fraction-correct for this decision TYPE
    (not a per-call score) on BeatIT fixtures, per source `source`.
    `defer_threshold` is the minimum `accuracy` required to trust this
    decision type's output rather than defer to clarification/a more
    conservative execution class.
    """

    decision_type: DecisionType
    accuracy: float
    defer_threshold: float
    source: AccuracySource
    reference: str
    note: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.accuracy <= 1.0:
            raise ValueError(f"accuracy must be in [0, 1], got {self.accuracy!r}")
        if not 0.0 <= self.defer_threshold <= 1.0:
            raise ValueError(f"defer_threshold must be in [0, 1], got {self.defer_threshold!r}")

    @property
    def is_trustworthy(self) -> bool:
        """True when this decision TYPE's measured/assumed accuracy clears
        its own defer threshold. Independent of `source`/`decision_source`
        at the call site — see module docstring for why per-call confidence
        isn't a meaningful signal for the fallback path."""
        return self.accuracy >= self.defer_threshold

    def with_measured_accuracy(self, accuracy: float, *, reference: str, note: str = "") -> "DecisionAccuracy":
        """Produce the measured replacement for a provisional entry.

        This is the intended integration seam for Agent 22's numbers: once
        docs/assistant/wave5/laya-evaluation.md exists, build a new
        DecisionPolicy by calling this on each provisional entry rather than
        hand-editing thresholds in place, so `source` always flips to
        MEASURED alongside the new number (never silently left stale).
        """
        return replace(
            self,
            accuracy=accuracy,
            source=AccuracySource.MEASURED,
            reference=reference,
            note=note or self.note,
        )


def _provisional(decision_type: DecisionType, note: str) -> DecisionAccuracy:
    return DecisionAccuracy(
        decision_type=decision_type,
        accuracy=_PROVISIONAL_DEFAULT_THRESHOLD,
        defer_threshold=_PROVISIONAL_DEFAULT_THRESHOLD,
        source=AccuracySource.PROVISIONAL_DEFAULT,
        reference=f"PENDING: {_PENDING_EVALUATION_DOC} not yet available",
        note=note,
    )


@dataclass(frozen=True)
class DecisionPolicy:
    """Full per-decision-type policy table.

    Deliberately a plain dataclass over a dict, keyed by `DecisionType`
    (a closed enum) rather than a raw string map, so every one of the 7 real
    decision types must be present (dataclass field, not a dict that could
    quietly drop an entry) and no clinical term can be added as a key
    without going through `DecisionType` first.
    """

    classify_intent: DecisionAccuracy = field(
        default_factory=lambda: _provisional(
            DecisionType.CLASSIFY_INTENT,
            "Highest-fanout decision (11 execution classes) with a keyword-only "
            "fallback (laya_adapter._fallback_classify_intent) — most exposed to "
            "misroute risk of the 7. Treat provisional threshold as a floor, not "
            "a comfortable estimate, until measured.",
        ).with_measured_accuracy(
            0.586,
            reference="docs/assistant/wave5/laya-evaluation.md (17/29, fallback, 160-fixture eval)",
            note="MEASURED BELOW THRESHOLD (58.6% < 70%) — the one decision type "
            "of 7 that does not clear its own bar. is_trustworthy is now False: "
            "should_defer_to_clarification(...) returns True for this type until "
            "either the fallback cascade is improved (see decision-adversary.md's "
            "confirmed bucket-ordering bugs, e.g. REPORT shadowing TWIN) or the "
            "threshold is deliberately revisited — do not silently lower the "
            "threshold to make this pass.",
        )
    )
    select_tool_family: DecisionAccuracy = field(
        default_factory=lambda: _provisional(
            DecisionType.SELECT_TOOL_FAMILY,
            "8-way choice (7 registry categories + NONE); a wrong choice here is "
            "cheap in this codebase specifically because "
            "orchestrator._select_and_execute_tool already falls back to "
            "INSUFFICIENT_EVIDENCE/UNSUPPORTED rather than fabricating a tool "
            "result when no candidate's required args resolve.",
        ).with_measured_accuracy(
            0.733,
            reference="docs/assistant/wave5/laya-evaluation.md (22/30, fallback, 160-fixture eval)",
            note="MEASURED above threshold (73.3%).",
        )
    )
    needs_evidence_retrieval: DecisionAccuracy = field(
        default_factory=lambda: _provisional(
            DecisionType.NEEDS_EVIDENCE_RETRIEVAL,
            "Binary yes/no; false negative just skips an evidence lookup the "
            "user could re-ask for, not a safety issue.",
        ).with_measured_accuracy(
            0.85,
            reference="docs/assistant/wave5/laya-evaluation.md (17/20, fallback, 160-fixture eval)",
            note="MEASURED above threshold (85.0%).",
        )
    )
    needs_simulation: DecisionAccuracy = field(
        default_factory=lambda: _provisional(
            DecisionType.NEEDS_SIMULATION,
            "Binary yes/no; note the deterministic simulation tools themselves "
            "(cardiac_state.py/hemodynamics.py/recovery_sim.py) are untouched by "
            "this decision either way — this only routes to them, never computes.",
        ).with_measured_accuracy(
            0.90,
            reference="docs/assistant/wave5/laya-evaluation.md (18/20, fallback, 160-fixture eval)",
            note="MEASURED above threshold (90.0%).",
        )
    )
    needs_clarification: DecisionAccuracy = field(
        default_factory=lambda: _provisional(
            DecisionType.NEEDS_CLARIFICATION,
            "Task's own worked example calls this decision type out by name "
            "('needs_clarification measured at 55% -> this decision type itself "
            "is unreliable, bias toward asking'). Kept at the same provisional "
            "floor as the others pending real numbers, but flagged: if Agent "
            "22's measurement lands low for this one specifically, the correct "
            "response is to bias the DEFAULT (i.e. make the fallback ask more "
            "often), not to raise this threshold further — see decision-policy.md.",
        ).with_measured_accuracy(
            0.952,
            reference="docs/assistant/wave5/laya-evaluation.md (20/21, fallback, 160-fixture eval)",
            note="MEASURED well above threshold (95.2%) — the worked-example "
            "worry above (modeled on a hypothetical 55%) did not materialize "
            "for the deterministic fallback; no bias-the-default action needed. "
            "(Note: real zero-shot Laya measured far worse on this same "
            "decision, 52.4% — a reason to keep LAYA_ENABLED off for this type "
            "specifically even after the wire-format bug in laya_adapter.py's "
            "choice-type calls is fixed.)",
        )
    )
    needs_physician_review_framing: DecisionAccuracy = field(
        default_factory=lambda: _provisional(
            DecisionType.NEEDS_PHYSICIAN_REVIEW_FRAMING,
            "Binary yes/no; affects presentation density only per "
            "GLOBAL_ARCHITECTURE.md's physician-support policy, never affects "
            "diagnostic/treatment authority.",
        ).with_measured_accuracy(
            0.90,
            reference="docs/assistant/wave5/laya-evaluation.md (18/20, fallback, 160-fixture eval)",
            note="MEASURED above threshold (90.0%).",
        )
    )
    is_complex_reasoning_required: DecisionAccuracy = field(
        default_factory=lambda: _provisional(
            DecisionType.IS_COMPLEX_REASONING_REQUIRED,
            "Binary yes/no; no model router exists yet in this repo "
            "(orchestrator.py module docstring: 'No LLM / model-router "
            "integration exists in this wave'), so this decision is currently "
            "inert in production regardless of its policy value.",
        ).with_measured_accuracy(
            0.85,
            reference="docs/assistant/wave5/laya-evaluation.md (17/20, fallback, 160-fixture eval)",
            note="MEASURED above threshold (85.0%); still inert in production "
            "pending a model router (unchanged from the provisional note).",
        )
    )

    def get(self, decision_type: DecisionType) -> DecisionAccuracy:
        return getattr(self, decision_type.value)

    def as_dict(self) -> dict[DecisionType, DecisionAccuracy]:
        return {dt: self.get(dt) for dt in DecisionType}


DEFAULT_POLICY = DecisionPolicy()


# ---------------------------------------------------------------------------
# Orchestrator-facing entry point
# ---------------------------------------------------------------------------


def should_defer_to_clarification(
    decision_name: str,
    decision_source: DecisionSource,
    *,
    policy: DecisionPolicy = DEFAULT_POLICY,
) -> bool:
    """True when the orchestrator should treat this decision as uncertain.

    Intended integration point (NOT wired up this wave — see
    docs/assistant/wave5/decision-policy.md "Integration point"):
    ``orchestrator.handle_message``, immediately after each
    ``family_decision``/``intent_decision`` call, e.g.::

        family_decision = await laya.select_tool_family(...)
        if should_defer_to_clarification("select_tool_family", family_decision.source):
            return _clarification_response()

    ``decision_source`` is accepted (not ignored) for forward compatibility
    with a future per-call signal (e.g. once Laya's calibration campaign
    lands a trustworthy per-call score) but does NOT currently change the
    result — see module docstring for why type-level accuracy, not
    call-level source, is the only honest signal available today. Both
    "laya" and "fallback" sources for the same decision type get gated
    identically until that changes.

    Raises ``ClinicalAuthorityRefused`` if `decision_name` names or contains
    a clinical-authority term — see module docstring. This never happens for
    a real ``LayaAdapter`` call (its 7 decision names are all safe), so a
    raise here means a caller is misusing this module, not that Laya
    produced something unsafe.
    """
    _reject_clinical_authority_misuse(decision_name)

    try:
        decision_type = DecisionType(decision_name)
    except ValueError:
        # An unrecognized (but non-clinical) decision_name is a caller bug —
        # e.g. a typo, or a new LayaAdapter method added without updating
        # this policy. Fail toward the SAFER product outcome (defer to
        # clarification) rather than silently trusting an unknown decision,
        # mirroring this module's own conservative bias.
        return True

    accuracy = policy.get(decision_type)
    return not accuracy.is_trustworthy


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------


def get_policy_summary(*, policy: DecisionPolicy = DEFAULT_POLICY) -> dict:
    """Machine-readable snapshot of every decision type's current policy.

    Shape (one entry per `DecisionType`, keyed by its string value):

        {
          "classify_intent": {
            "accuracy": 0.7,
            "defer_threshold": 0.7,
            "is_trustworthy": true,
            "source": "provisional-default",
            "reference": "PENDING: docs/assistant/wave5/laya-evaluation.md not yet available",
            "note": "...",
          },
          ...
        }

    Plus a top-level "all_measured" bool so a caller (e.g. a status
    dashboard, or a future CI check) can tell at a glance whether every
    threshold is still provisional without inspecting each entry.
    """
    entries = policy.as_dict()
    per_decision = {
        decision_type.value: {
            "accuracy": accuracy.accuracy,
            "defer_threshold": accuracy.defer_threshold,
            "is_trustworthy": accuracy.is_trustworthy,
            "source": accuracy.source.value,
            "reference": accuracy.reference,
            "note": accuracy.note,
        }
        for decision_type, accuracy in entries.items()
    }
    return {
        "decisions": per_decision,
        "all_measured": all(a.source is AccuracySource.MEASURED for a in entries.values()),
        "pending_evaluation_doc": _PENDING_EVALUATION_DOC,
    }
