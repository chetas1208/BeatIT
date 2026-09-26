"""Report-specific consistency validation for the BeatIT assistant (Wave 6.5).

Extends `python/hearttwin/assistant/safety_validator.py`'s existing output-rail
gates rather than replacing them, per AGENTS.md SS1.7 ("stay in your lane") and
`docs/assistant/PHYSICIAN_HELPER_HARDENING.md`'s explicit instruction that
`validate_numeric_claims` "already does exactly what this spec... asks for
numbers — extend its checks (unit validation, historical/current confusion,
negation reversal) rather than building a parallel validator." Every function
here imports from `safety_validator.py`/`physician_brief.py`/`schemas.py`;
none of those files are modified.

Five checks, none of which `validate_numeric_claims` performs today:

  * `validate_unit_consistency` — a claimed metric's UNIT, not its value
    (EF stated in "mL" instead of "%", CO in "%" instead of "L/min").
  * `detect_negation_reversal` — a source negation ("no evidence of X",
    "denies Y", "without Z") whose subject reappears asserted positively in
    generated text.
  * `detect_uncertainty_loss` — a source hedge ("possible", "suspected",
    "cannot exclude", "unlikely", "inconclusive") whose subject reappears in
    generated text as flat, unhedged fact.
  * `validate_observed_derived_simulated_boundary` — a bundle's real
    `CanonicalProvenanceKind` for a piece of data vs. generated text's own
    explicit claim about that data's nature ("observed"/"measured" vs.
    "simulated"/"calculated" language).
  * `detect_number_before_label_claims` — a composition-based fix for
    `validate_numeric_claims`'s documented gap ("45% EF" isn't matched
    because its regex requires the metric name before the number; see
    `safety_validator.py`'s `_metric_pattern` docstring). Fixed HERE, not by
    editing `safety_validator.py` (this task's file-ownership constraint) —
    verified against the live gap (`validate_numeric_claims("The ventricle
    showed 45% EF on this study.", {"ejection_fraction_pct": 60.0})` returns
    `valid=True, mismatches=[]`, i.e. it silently misses a real 45-vs-60
    mismatch) and against every existing `test_safety_validator.py` case
    before writing this file, without touching that file at all. The fix
    itself reuses `validate_numeric_claims`'s real comparison/tolerance logic
    by rewriting the reversed-order snippet into label-first order and
    calling it — it does not reimplement the comparison.

**Honesty about scope, per the spec's own tolerance for "bounded, not
perfect"** (see `language_integrity.py`'s `narrow_can_i_take_check` and
`safety_validator.py`'s numeric-claim regex for the same house style of
documenting known gaps instead of hiding them):

  * `detect_negation_reversal` and `detect_uncertainty_loss` are regex +
    keyword-overlap pattern matching, not a negation-scope or coreference
    parser. They match a captured subject phrase as a literal substring (or,
    for uncertainty, via >=50% content-word overlap) between a source
    sentence and a generated sentence. Known failure modes: synonym/paraphrase
    subjects ("pericardial effusion" vs. "fluid around the heart") are missed
    entirely; a subject captured with extra leading adjectives ("significant
    pericardial effusion") won't substring-match a generated sentence that
    drops the adjective; double negation ("not able to rule out X") is not
    specially handled; a coordinated list split across "and"/"or" only
    recognizes the boundary as a stop-word, not real conjunction parsing. This
    is a real, useful bounded check for the common single-clause case the
    spec calls out, not a general NLP solution.
  * `validate_observed_derived_simulated_boundary`'s aggregate use (inside
    `validate_report_consistency`, looping over `bundle.provenance`) is
    intentionally coarse: it checks whether generated text's kind-language IS
    UNAMBIGUOUS ACROSS THE WHOLE REPORT before comparing it to any one
    provenance entry, because `DecisionSupportBundle` (Wave 3,
    `physician_brief.py`) carries a flat `list[ProvenanceRef]`, not a
    per-sentence or per-finding provenance map. A report that correctly
    describes two different findings with two different kinds (one derived,
    one simulated) will not be checked at this aggregate granularity — this
    is a real, documented extension point for whenever `case_context.py`
    and/or `report_personalization.py` (Wave 6.5 siblings, checked for at the
    start of this task and not yet present in this repo — see
    `docs/assistant/wave6.5/report-consistency.md`) produce structured
    per-finding provenance the caller can pass in directly via the function's
    own per-call `claimed_kind` parameter instead of relying on this coarse
    fallback.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel, Field

from python.hearttwin.assistant.physician_brief import DecisionSupportBundle
from python.hearttwin.assistant.safety_validator import (
    NumericMismatch,
    OutputSafetyDecision,
    check_output_safety,
    validate_numeric_claims,
)
from python.hearttwin.assistant.schemas import CanonicalProvenanceKind

# ---------------------------------------------------------------------------
# Shared metric label list
#
# Deliberately duplicated from safety_validator.py's private `_CLAIM_PATTERNS`
# label tuples (that dict, and the label names inside it, are not exported —
# only PUBLIC names are imported from safety_validator.py throughout this
# file, per AGENTS.md's composition-not-coupling instruction). This is a
# duplication of label SYNONYMS only, never of comparison/tolerance logic —
# every actual value comparison below still calls the real
# `validate_numeric_claims`.
# ---------------------------------------------------------------------------

_METRIC_LABELS: dict[str, tuple[str, ...]] = {
    "EF": ("EF", "ejection fraction"),
    "SV": ("SV", "stroke volume"),
    "CO": ("CO", "cardiac output"),
    "MAP": ("MAP", "mean arterial pressure"),
    "HR": ("HR", "heart rate"),
    "EDV": ("EDV", "end-diastolic volume", "end diastolic volume"),
    "ESV": ("ESV", "end-systolic volume", "end systolic volume"),
    "QTC": ("QTc", "QTC", "corrected QT"),
}

DEFAULT_EXPECTED_UNITS: dict[str, str] = {
    "EF": "%",
    "SV": "mL",
    "CO": "L/min",
    "MAP": "mmHg",
    "HR": "bpm",
    "EDV": "mL",
    "ESV": "mL",
    "QTC": "ms",
}


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class UnitMismatch(BaseModel):
    metric: str
    expected_unit: str
    found_unit: str
    context: str


class NegationReversal(BaseModel):
    subject: str
    source_snippet: str
    generated_snippet: str


class UncertaintyLossFinding(BaseModel):
    subject: str
    hedge_term: str
    source_snippet: str
    generated_snippet: str


class BoundaryViolation(BaseModel):
    real_kind: str
    claimed_kind: str
    generated_snippet: Optional[str] = None
    detail: str


class ReportConsistencyResult(BaseModel):
    valid: bool
    numeric_mismatches: list[NumericMismatch] = Field(default_factory=list)
    numeric_before_label_mismatches: list[NumericMismatch] = Field(default_factory=list)
    output_safety: OutputSafetyDecision
    unit_mismatches: list[UnitMismatch] = Field(default_factory=list)
    negation_reversals: list[NegationReversal] = Field(default_factory=list)
    uncertainty_loss: list[UncertaintyLossFinding] = Field(default_factory=list)
    boundary_violations: list[BoundaryViolation] = Field(default_factory=list)
    # Fail-safely on incomplete data (spec's own requirement): an empty check
    # result here means "not checked" for a documented reason, distinct from
    # "checked and clean" — mirrors DecisionSupportBundle's own
    # missing_evidence/conflicts precedent (physician_brief.py) of never
    # letting an empty list silently read as "verified absent."
    skipped_checks: list[str] = Field(default_factory=list)


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


# ---------------------------------------------------------------------------
# 1. Unit consistency
# ---------------------------------------------------------------------------

# Deliberately bounded to unit tokens directly adjacent to the number (no
# free-floating "the result, in milliliters, was..." phrasing) — same
# precision-over-recall tradeoff `safety_validator.py`'s own numeric-claim
# gate documents for its connector-word list.
_UNIT_ALIASES: dict[str, str] = {
    "%": "%",
    "percent": "%",
    "ml": "mL",
    "milliliter": "mL",
    "milliliters": "mL",
    "l/min": "L/min",
    "lmin": "L/min",
    "liter/min": "L/min",
    "liters/min": "L/min",
    "liters/minute": "L/min",
    "mmhg": "mmHg",
    "bpm": "bpm",
    "beats/min": "bpm",
    "ms": "ms",
    "millisecond": "ms",
    "milliseconds": "ms",
}
_UNIT_TOKEN_ALT = "|".join(re.escape(k) for k in sorted(_UNIT_ALIASES, key=len, reverse=True))


def _normalize_unit(raw: str) -> Optional[str]:
    return _UNIT_ALIASES.get(raw.strip().lower())


def _unit_patterns(labels: tuple[str, ...]) -> list[re.Pattern[str]]:
    name_alt = "|".join(re.escape(name) for name in labels)
    return [
        # label ... number UNIT  ("EF was 45 mL")
        re.compile(
            rf"\b(?:{name_alt})\b\s*(?:is|of|=|:|was|at|~)?\s*(?:approximately|about)?\s*"
            rf"\d+(?:\.\d+)?\s*({_UNIT_TOKEN_ALT})(?=\W|$)",
            re.IGNORECASE,
        ),
        # number UNIT ... label  ("45 mL EF")
        re.compile(
            rf"\d+(?:\.\d+)?\s*({_UNIT_TOKEN_ALT})(?=\W|$)\s*(?:of|for)?\s*\b(?:{name_alt})\b",
            re.IGNORECASE,
        ),
    ]


def validate_unit_consistency(text: str, expected_units: dict[str, str]) -> list[UnitMismatch]:
    """Flag a metric mentioned with the wrong unit (EF in "mL", CO in "%", ...).

    Complementary to `validate_numeric_claims`, which checks the VALUE against
    canonical data but never looks at the unit token at all — a report could
    pass the numeric gate while still saying "cardiac output is 45%" (a unit
    error, not a value error). Only fires when an explicit, recognized unit
    token is actually present next to the number; a bare number with no unit
    is not checked (fail-safely on incomplete data rather than guessing).
    """
    source = text or ""
    mismatches: list[UnitMismatch] = []
    seen_spans: set[int] = set()

    for metric, labels in _METRIC_LABELS.items():
        expected = expected_units.get(metric)
        if not expected:
            continue
        for pattern in _unit_patterns(labels):
            for match in pattern.finditer(source):
                if match.start() in seen_spans:
                    continue
                canonical = _normalize_unit(match.group(1))
                if canonical is None or canonical == expected:
                    continue
                seen_spans.add(match.start())
                mismatches.append(
                    UnitMismatch(
                        metric=metric,
                        expected_unit=expected,
                        found_unit=canonical,
                        context=source[max(0, match.start() - 25) : match.end() + 10].strip(),
                    )
                )
    return mismatches


# ---------------------------------------------------------------------------
# 2. Negation reversal
# ---------------------------------------------------------------------------

_NEGATION_CUE_PATTERNS = [
    re.compile(r"\bno evidence of\s+(.+)", re.IGNORECASE),
    re.compile(r"\bdenies\s+(.+)", re.IGNORECASE),
    re.compile(r"\bwithout\s+(.+)", re.IGNORECASE),
    re.compile(r"\bno signs? of\s+(.+)", re.IGNORECASE),
    re.compile(r"\babsence of\s+(.+)", re.IGNORECASE),
    re.compile(r"\bruled out\s+(.+)", re.IGNORECASE),
    re.compile(r"\bnegative for\s+(.+)", re.IGNORECASE),
]

_NEGATION_MARKERS_IN_GENERATED = re.compile(
    r"\b(no|not|n't|denies|without|absence of|ruled out|negative for|unremarkable for)\b",
    re.IGNORECASE,
)

# A subject phrase is capped at this many words after the cue, then further
# trimmed at the first word from this small filler/verb list — a word-list
# heuristic standing in for real clause boundary detection (mirrors
# language_integrity.py's `_CAN_I_TAKE_WINDOW_WORDS` window approach).
_NEGATION_SUBJECT_WINDOW_WORDS = 6
_NEGATION_SUBJECT_STOP_WORDS = {
    "is", "was", "are", "were", "on", "in", "at", "with", "during",
    "noted", "seen", "found", "present", "identified", "observed", "and", "or",
}
_SUBJECT_LEADING_STOPWORDS = re.compile(r"^(?:any|a|an|the)\s+", re.IGNORECASE)


def _extract_negated_subjects(sentence: str) -> list[str]:
    subjects: list[str] = []
    for pattern in _NEGATION_CUE_PATTERNS:
        match = pattern.search(sentence)
        if not match:
            continue
        remainder = re.split(r"[.;]", match.group(1))[0]
        words = remainder.strip().split()[:_NEGATION_SUBJECT_WINDOW_WORDS]
        trimmed: list[str] = []
        for word in words:
            if word.lower().strip(",") in _NEGATION_SUBJECT_STOP_WORDS:
                break
            trimmed.append(word.strip(","))
        subject = _SUBJECT_LEADING_STOPWORDS.sub("", " ".join(trimmed)).strip().lower()
        subject = re.sub(r"\s+", " ", subject)
        if len(subject) >= 3:
            subjects.append(subject)
    return subjects


def detect_negation_reversal(source_text: str, generated_text: str) -> list[NegationReversal]:
    """Flag a source negation whose subject reappears asserted positively.

    Bounded pattern match, not a negation-scope parser — see module
    docstring "Honesty about scope" for the specific, real failure modes
    (synonym subjects, dropped adjectives, double negation) this does not
    handle. What it DOES reliably catch: the common single-clause case where
    a source sentence says "no evidence of X" / "denies Y" / "without Z" and
    a generated sentence contains that same phrase with no negation marker
    anywhere in it.
    """
    findings: list[NegationReversal] = []
    seen: set[tuple[str, str]] = set()
    gen_sentences = _sentences(generated_text)

    for src_sentence in _sentences(source_text):
        for subject in _extract_negated_subjects(src_sentence):
            for gen_sentence in gen_sentences:
                if subject not in gen_sentence.lower():
                    continue
                if _NEGATION_MARKERS_IN_GENERATED.search(gen_sentence):
                    continue
                key = (subject, gen_sentence.strip())
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    NegationReversal(
                        subject=subject,
                        source_snippet=src_sentence.strip(),
                        generated_snippet=gen_sentence.strip(),
                    )
                )
    return findings


# ---------------------------------------------------------------------------
# 3. Uncertainty loss
# ---------------------------------------------------------------------------

_HEDGE_PATTERNS = [
    re.compile(r"\bpossible\b", re.IGNORECASE),
    re.compile(r"\bpossibly\b", re.IGNORECASE),
    re.compile(r"\bsuspected\b", re.IGNORECASE),
    re.compile(r"\bsuspicious for\b", re.IGNORECASE),
    re.compile(r"\bcannot exclude\b", re.IGNORECASE),
    re.compile(r"\bcan'?t exclude\b", re.IGNORECASE),
    re.compile(r"\bcannot rule out\b", re.IGNORECASE),
    re.compile(r"\bcan'?t rule out\b", re.IGNORECASE),
    re.compile(r"\bunlikely\b", re.IGNORECASE),
    re.compile(r"\binconclusive\b", re.IGNORECASE),
    re.compile(r"\bequivocal\b", re.IGNORECASE),
    re.compile(r"\bindeterminate\b", re.IGNORECASE),
    re.compile(r"\bborderline\b", re.IGNORECASE),
]

# Generic words and the hedge vocabulary itself are excluded from the
# content-word overlap so overlap only ever reflects shared SUBJECT matter,
# never house-style scaffolding or the hedge word being compared for absence.
_CONTENT_STOPWORDS = {
    "this", "that", "with", "from", "have", "been", "were", "there", "which",
    "their", "about", "also", "into", "over", "under", "findings", "finding",
    "imaging", "noted", "shows", "showed", "report", "patient", "case",
    "study", "possible", "possibly", "suspected", "unlikely", "inconclusive",
    "equivocal", "indeterminate", "borderline", "exclude", "excluded",
}


def _has_hedge(sentence: str) -> bool:
    return any(pattern.search(sentence) for pattern in _HEDGE_PATTERNS)


def _content_words(sentence: str) -> set[str]:
    words = re.findall(r"[a-z]{4,}", sentence.lower())
    return {w for w in words if w not in _CONTENT_STOPWORDS}


def detect_uncertainty_loss(source_text: str, generated_text: str) -> list[UncertaintyLossFinding]:
    """Flag a source hedge whose subject reappears in generated text as flat fact.

    Keyword-overlap heuristic (>=2 shared content words, >=50% of the source
    sentence's content words), not semantic similarity — a real, bounded
    substitute for full coreference resolution, same tradeoff class as
    `detect_negation_reversal`. A generated sentence is only ever compared
    when it contains NO hedge language of its own, so a report that
    rephrases-but-still-hedges never false-positives here.
    """
    findings: list[UncertaintyLossFinding] = []
    gen_sentences = _sentences(generated_text)

    for src_sentence in _sentences(source_text):
        hedge_hits = [m.group(0) for p in _HEDGE_PATTERNS for m in [p.search(src_sentence)] if m]
        if not hedge_hits:
            continue
        source_content = _content_words(src_sentence)
        if len(source_content) < 2:
            continue
        for gen_sentence in gen_sentences:
            if _has_hedge(gen_sentence):
                continue
            overlap = source_content & _content_words(gen_sentence)
            if len(overlap) >= 2 and len(overlap) / len(source_content) >= 0.5:
                findings.append(
                    UncertaintyLossFinding(
                        subject=", ".join(sorted(overlap)),
                        hedge_term=hedge_hits[0],
                        source_snippet=src_sentence.strip(),
                        generated_snippet=gen_sentence.strip(),
                    )
                )
    return findings


# ---------------------------------------------------------------------------
# 4. Observed / derived / simulated boundary
# ---------------------------------------------------------------------------

# Only these three CanonicalProvenanceKind values map onto this check's
# observed/derived/simulated boundary. MODEL_PRIOR/EXTERNAL_REFERENCE/
# USER_ASSERTED don't map onto that 3-way split without guessing a bucket, so
# they are out of scope for THIS check (fail-safely: no verdict, not a forced
# guess) — see module docstring.
_THREE_WAY_KINDS = {"observed", "derived", "simulated"}

_KIND_LANGUAGE_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "observed": [
        re.compile(r"\bobserved\b", re.IGNORECASE),
        re.compile(r"\bdirectly measured\b", re.IGNORECASE),
        re.compile(r"\bmeasured\b", re.IGNORECASE),
        re.compile(r"\bdocumented\b", re.IGNORECASE),
    ],
    "derived": [
        re.compile(r"\bderived\b", re.IGNORECASE),
        re.compile(r"\bcomputed\b", re.IGNORECASE),
        re.compile(r"\bcalculated\b", re.IGNORECASE),
    ],
    "simulated": [
        re.compile(r"\bsimulated\b", re.IGNORECASE),
        re.compile(r"\bmodel(?:ed|ling|led)?\b", re.IGNORECASE),
        re.compile(r"\bestimated by (?:the )?simulation\b", re.IGNORECASE),
    ],
}


def _normalize_kind(raw: "CanonicalProvenanceKind | str | None") -> Optional[str]:
    if raw is None or raw == "":
        return None
    value = raw.value if isinstance(raw, CanonicalProvenanceKind) else str(raw)
    value = value.strip().lower()
    return value if value in _THREE_WAY_KINDS else None


def _find_snippet_for_kind(text: str, kind: str) -> Optional[str]:
    patterns = _KIND_LANGUAGE_PATTERNS.get(kind, [])
    for sentence in _sentences(text):
        if any(p.search(sentence) for p in patterns):
            return sentence.strip()
    return None


def validate_observed_derived_simulated_boundary(
    bundle_field_source: "CanonicalProvenanceKind | str",
    generated_text: str,
    claimed_kind: str,
) -> Optional[BoundaryViolation]:
    """Flag generated text that claims a different provenance kind than the bundle tracks.

    `claimed_kind` is the caller's explicit claim about what this text says
    (e.g. a report-section label). When it's empty/unrecognized, this falls
    back to scanning `generated_text` itself for explicit kind language
    ("observed"/"measured" vs. "simulated"/"calculated") — but only acts on
    that fallback when the text's kind language is UNAMBIGUOUS (exactly one
    kind detected); ambiguous or silent text yields no verdict rather than a
    guess, per the spec's fail-safely-on-incomplete-data requirement.
    """
    real_kind = _normalize_kind(bundle_field_source)
    if real_kind is None:
        return None

    text = generated_text or ""
    stated_kind = _normalize_kind(claimed_kind)
    if stated_kind is None:
        text_kinds = {
            kind for kind, patterns in _KIND_LANGUAGE_PATTERNS.items()
            if any(p.search(text) for p in patterns)
        }
        if len(text_kinds) != 1:
            return None
        stated_kind = next(iter(text_kinds))

    if stated_kind == real_kind:
        return None

    return BoundaryViolation(
        real_kind=real_kind,
        claimed_kind=stated_kind,
        generated_snippet=_find_snippet_for_kind(text, stated_kind),
        detail=(
            f"bundle tracks this data's provenance as {real_kind!r}, but the "
            f"generated text describes it as {stated_kind!r}"
        ),
    )


# ---------------------------------------------------------------------------
# 5. Number-before-label numeric gate fix (composition over safety_validator.py)
# ---------------------------------------------------------------------------

_NUMBER_BEFORE_LABEL_PATTERNS: dict[str, re.Pattern[str]] = {
    metric: re.compile(
        rf"(\d+(?:\.\d+)?)\s*%?\s*(?:percent\s+)?(?:of\s+)?"
        rf"\b(?:{'|'.join(re.escape(label) for label in labels)})\b",
        re.IGNORECASE,
    )
    for metric, labels in _METRIC_LABELS.items()
}


def detect_number_before_label_claims(
    generated_text: str, canonical_payload: dict
) -> list[NumericMismatch]:
    """Catch "45% EF"-style claims `validate_numeric_claims` misses by design.

    `safety_validator.py`'s `_metric_pattern` requires the metric name BEFORE
    the number (documented tradeoff: it trades recall on this exact shape for
    precision against bare abbreviations like "CO"/"HR" false-positiving
    inside unrelated text). Rather than editing that owned, tested regex,
    this rewrites each reversed-order match into label-first order ("EF is
    45") and re-runs the REAL `validate_numeric_claims` on that synthetic
    snippet — reusing its actual comparison/tolerance logic rather than
    duplicating it. The reversed-order pattern itself requires tight
    adjacency (number, then only "%"/"percent"/"of", then the label) so it
    does not cross sentence or clause boundaries — e.g. "the patient is 45.
    EF is preserved" does not false-positive on 45 here (the period breaks
    the adjacency).
    """
    text = generated_text or ""
    mismatches: list[NumericMismatch] = []
    seen_spans: set[tuple[int, int]] = set()

    for metric, pattern in _NUMBER_BEFORE_LABEL_PATTERNS.items():
        for match in pattern.finditer(text):
            if match.span() in seen_spans:
                continue
            seen_spans.add(match.span())
            canonical_label = _METRIC_LABELS[metric][0]
            synthetic = f"{canonical_label} is {match.group(1)}"
            mismatches.extend(validate_numeric_claims(synthetic, canonical_payload).mismatches)
    return mismatches


# ---------------------------------------------------------------------------
# Top-level aggregate
# ---------------------------------------------------------------------------


def _canonical_payload_from_bundle(bundle: DecisionSupportBundle) -> dict[str, Any]:
    """Best-effort metric:value extraction from a DecisionSupportBundle.

    Honest and partial, not exhaustive: `simulated_results` entries carry a
    clean `metric_id`/`mean` pair (ensemble.py's shape) so those are used
    directly; `derived_evidence` entries (get_cardiac_findings' findings) are
    evidence prose, not clean metric:value records in this bundle shape, so
    they are not attempted here. An empty result is not a failure — it means
    every numeric claim in the report text will be reported as unsupported by
    `validate_numeric_claims`, which is that gate's own documented
    no-exceptions behavior, not a gap introduced here.
    """
    payload: dict[str, Any] = {}
    for entry in bundle.simulated_results:
        metric_id = entry.get("metric_id")
        mean = entry.get("mean")
        if metric_id and isinstance(mean, (int, float)) and not isinstance(mean, bool):
            payload[str(metric_id)] = mean
    for key, value in bundle.clinical_context.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            payload[key] = value
    return payload


def validate_report_consistency(
    report_text: str,
    bundle: DecisionSupportBundle,
    source_texts: list[str] | None = None,
) -> ReportConsistencyResult:
    """Aggregate report-consistency gate: every check above plus the existing
    numeric-claim and clinical-boundary gates, as ONE pass/fail result.

    `validate_numeric_claims`/`check_output_safety` are called directly (not
    reimplemented) per this task's composition-not-duplication constraint.
    """
    skipped_checks: list[str] = []

    canonical_payload = _canonical_payload_from_bundle(bundle)
    if not canonical_payload:
        skipped_checks.append(
            "numeric checks ran against an empty canonical payload (bundle "
            "exposed no simulated_results/clinical_context numerics) — every "
            "numeric claim in report_text is reported as unsupported rather "
            "than silently skipped, per validate_numeric_claims' own "
            "no-exceptions rule."
        )

    numeric_result = validate_numeric_claims(report_text, canonical_payload)
    numeric_before_label = detect_number_before_label_claims(report_text, canonical_payload)
    output_safety = check_output_safety(report_text)
    unit_mismatches = validate_unit_consistency(report_text, DEFAULT_EXPECTED_UNITS)

    negation_reversals: list[NegationReversal] = []
    uncertainty_loss: list[UncertaintyLossFinding] = []
    if source_texts:
        for source_text in source_texts:
            negation_reversals.extend(detect_negation_reversal(source_text, report_text))
            uncertainty_loss.extend(detect_uncertainty_loss(source_text, report_text))
    else:
        skipped_checks.append(
            "negation_reversals/uncertainty_loss not checked: no source_texts "
            "supplied — both are relative checks (source vs. generated) and "
            "cannot run against report_text alone."
        )

    boundary_violations: list[BoundaryViolation] = []
    seen_boundary: set[tuple[str, str]] = set()
    for ref in bundle.provenance:
        violation = validate_observed_derived_simulated_boundary(ref.kind, report_text, "")
        if violation is None:
            continue
        key = (violation.real_kind, violation.claimed_kind)
        if key in seen_boundary:
            continue
        seen_boundary.add(key)
        boundary_violations.append(violation)
    if bundle.provenance:
        skipped_checks.append(
            "observed/derived/simulated boundary check ran at aggregate "
            "(whole-report) granularity, not per-finding — DecisionSupportBundle "
            "carries a flat provenance list, not a per-sentence/per-finding "
            "map; see module docstring 'Honesty about scope'."
        )

    valid = (
        numeric_result.valid
        and not numeric_before_label
        and not output_safety.blocked
        and not unit_mismatches
        and not negation_reversals
        and not uncertainty_loss
        and not boundary_violations
    )

    return ReportConsistencyResult(
        valid=valid,
        numeric_mismatches=numeric_result.mismatches,
        numeric_before_label_mismatches=numeric_before_label,
        output_safety=output_safety,
        unit_mismatches=unit_mismatches,
        negation_reversals=negation_reversals,
        uncertainty_loss=uncertainty_loss,
        boundary_violations=boundary_violations,
        skipped_checks=skipped_checks,
    )
