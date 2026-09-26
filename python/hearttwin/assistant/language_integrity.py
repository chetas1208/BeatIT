"""Prescriptive/authority-language style guard for the BeatIT assistant (Wave 3).

This is deliberately NOT a replacement for, or a superset of,
``python/hearttwin/assistant/safety_validator.py``'s ``check_output_safety``.
That module unions two production blocklists (``copilot.py``'s
``_OUTPUT_RED_FLAGS`` and ``careguard/copilot_agent.py``'s ``_BLOCK``) and is
the authoritative output-rail safety gate. This module is a narrower,
purpose-built TONE/STYLE guard: it targets the specific phrasing shapes
AGENTS.md SS1.4 and GLOBAL_ARCHITECTURE.md's "Decision support object" /
output-rail sections call out — imperative treatment instructions,
unhedged diagnostic certainty, and clinical-authority claims ("I
recommend...") — independent of whether those phrasings happen to contain a
blocklisted term. It is meant to run IN ADDITION to ``check_output_safety``,
never instead of it, and it does not modify or import from
``safety_validator.py`` (that file is Wave 2's, owned, read-only from here).

Two entry points matter to callers:

  * ``scan_for_prescriptive_language`` — check one piece of generated text.
  * ``scan_assistant_module_for_violations`` — walk a source tree and flag
    string literals that read like end-user response text. This is the
    "guard rail as code" a future wave/CI step can run against new
    response-generation modules before they're wired into the pipeline.

See docs/assistant/wave3/clinical-language-integrity.md for the full audit
of Wave 2's flagged judgment calls (including why ``narrow_can_i_take_check``
exists below) and the integration note for folding it into
``safety_validator.py`` proper.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

LanguageIntegrityCategory = Literal[
    "imperative_treatment",
    "unsupported_diagnostic_certainty",
    "clinical_authority_claim",
    "clean",
]


class LanguageIntegrityResult(BaseModel):
    flagged: bool
    matched_patterns: list[str] = Field(default_factory=list)
    category: LanguageIntegrityCategory


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


# ---------------------------------------------------------------------------
# Category 1: imperative treatment instructions
# ---------------------------------------------------------------------------
# Verb+dose or verb+medication-noun shapes that read as a direct instruction
# to act on a drug/dose, as opposed to describing what the simulation did.
# The (?:ing|d)? suffix on the verb covers "increasing"/"started" phrasing
# without trying to be a full morphological analyzer — a pragmatic, not
# exhaustive, match (see module docstring on scope).
_IMPERATIVE_TREATMENT_PATTERNS = [
    r"\btake\s+\d+(?:\.\d+)?\s*(?:mg|mcg|milligrams?|micrograms?|ml|milliliters?|units?)\b",
    r"\b(?:start|stop|increase|decrease|discontinue)(?:ing|ed|d)?\s+(?:taking\s+)?"
    r"(?:your|the|his|her)?\s*(?:dose|dosage|medication|prescription|drug|pill|tablet)s?\b",
    r"\byou should\s+(?:take|start|stop|increase|decrease|discontinue)\b",
]

# ---------------------------------------------------------------------------
# Category 2: clinical-authority claims
# ---------------------------------------------------------------------------
_CLINICAL_AUTHORITY_PATTERNS = [
    r"\bi recommend\b",
    r"\bmy recommendation is\b",
    r"\bi advise\b",
    r"\byou must\b",
]

# ---------------------------------------------------------------------------
# Category 3: unsupported diagnostic certainty
# ---------------------------------------------------------------------------
# Checked per-sentence with a hedge-word guard: a sentence containing any
# hedge word is skipped entirely for this category, so "may have"/"is
# consistent with"/"evidence is insufficient" phrasing (BeatIT's required
# house style) never trips these patterns even though it can share vocabulary
# ("you have", "this is") with the unhedged form.
_DIAGNOSTIC_CERTAINTY_PATTERNS = [
    r"\byou have (?!to\b|a right\b|access\b|questions?\b|options?\b|been\b)[a-z]",
    r"\byour diagnosis is\b",
    r"\bthe diagnosis is\b",
    r"\bwhat you have is\b",
    r"\b(?:indicates|confirms|proves) (?:that )?you have\b",
]

_HEDGE_PATTERN = re.compile(
    r"\b(?:may|might|could|possibly|likely|consistent with|suggests?|suggestive of|"
    r"insufficient|evidence supports|does not confirm|cannot confirm|available evidence)\b"
)


def _diagnostic_certainty_hits(text: str) -> list[str]:
    hits: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text or ""):
        normalized = _normalize(sentence)
        if not normalized or _HEDGE_PATTERN.search(normalized):
            continue
        for pattern in _DIAGNOSTIC_CERTAINTY_PATTERNS:
            if re.search(pattern, normalized):
                hits.append(pattern)
    return sorted(set(hits))


def scan_for_prescriptive_language(text: str) -> LanguageIntegrityResult:
    """Style/tone guard for imperative, authority, or unhedged-diagnostic phrasing.

    Runs all three category checks and reports every matched pattern, but
    ``category`` picks a single label using severity order imperative >
    authority > diagnostic-certainty (an instruction to act on a dose is the
    most directly actionable risk; an authority claim without a concrete
    action is next; unhedged diagnostic language is presented as
    informational but still risks being read as a diagnosis).
    """
    normalized = _normalize(text)

    imperative_hits = sorted({p for p in _IMPERATIVE_TREATMENT_PATTERNS if re.search(p, normalized)})
    authority_hits = sorted({p for p in _CLINICAL_AUTHORITY_PATTERNS if re.search(p, normalized)})
    diagnostic_hits = _diagnostic_certainty_hits(text)

    matched_patterns = (
        [f"imperative_treatment:{p}" for p in imperative_hits]
        + [f"clinical_authority_claim:{p}" for p in authority_hits]
        + [f"unsupported_diagnostic_certainty:{p}" for p in diagnostic_hits]
    )

    if imperative_hits:
        category: LanguageIntegrityCategory = "imperative_treatment"
    elif authority_hits:
        category = "clinical_authority_claim"
    elif diagnostic_hits:
        category = "unsupported_diagnostic_certainty"
    else:
        category = "clean"

    return LanguageIntegrityResult(flagged=bool(matched_patterns), matched_patterns=matched_patterns, category=category)


# ---------------------------------------------------------------------------
# "can I take" narrowing (see clinical-language-integrity.md SS1 for the audit
# verdict this implements — Wave 2's Agent 10 flagged the bare
# `_SUPPLEMENTAL_TREATMENT_PATTERNS` entry `r"\bcan i take\b"` in
# safety_validator.py as the highest false-positive-risk phrase in that file,
# citing "can I take this simulation further?" as a plausible benign hit.
# This is a PROPOSED narrower replacement, implemented here as an additional
# layer rather than an edit to safety_validator.py, which is Wave 2's owned
# file. Integration note: a future wave should replace the bare
# r"\bcan i take\b" entry in `_SUPPLEMENTAL_TREATMENT_PATTERNS` with a call to
# this function (or an equivalent regex) so `classify_request_safety` only
# blocks on "can I take" when it is actually medication/dose-adjacent.
# ---------------------------------------------------------------------------

# Deliberately not exhaustive — an open-ended drug-name list is unbounded.
# This covers common OTC/prescription names and generic medication nouns,
# which is enough to distinguish the plausible benign uses of "can I take"
# ("...this simulation further", "...a closer look") from the medication
# question intake_agent.py doesn't otherwise catch. Anything missed here
# still has to clear intake_agent.py's own "medic(ine|ation)"/"drug"/"dose"
# patterns and the broader safety_validator.py output gate, so this is a
# precision improvement on one supplemental input pattern, not the last line
# of defense.
_MED_ADJACENT_WORDS = (
    "ibuprofen",
    "acetaminophen",
    "tylenol",
    "advil",
    "aspirin",
    "warfarin",
    "metoprolol",
    "lisinopril",
    "statin",
    "insulin",
    "nitroglycerin",
    "beta blocker",
    "blood thinner",
    "medication",
    "medicine",
    "drug",
    "pill",
    "dose",
    "dosage",
    "tablet",
    "over-the-counter",
    "over the counter",
    "supplement",
    "prescription",
)

_DOSE_SHAPE_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*(?:mg|mcg|milligrams?|micrograms?|ml|units?)\b")

# Word-count, not char-count, window: keeps the check robust to short vs.
# long medication names ("mg" vs "over-the-counter") without needing two
# different distances tuned per phrase.
_CAN_I_TAKE_WINDOW_WORDS = 8


def narrow_can_i_take_check(text: str) -> bool:
    """True only when "can I take" appears near an actual medication/dose word.

    Mirrors safety_validator.py's normalization (lowercase, collapsed
    whitespace) so behavior would match if folded into that file directly.
    """
    normalized = _normalize(text)
    words = normalized.split(" ")

    for match in re.finditer(r"\bcan i take\b", normalized):
        # Locate the match's word index by counting spaces before it, then
        # take a window of words after "take" to search for a medication cue.
        prefix_word_count = normalized[: match.end()].count(" ")
        window_words = words[prefix_word_count : prefix_word_count + _CAN_I_TAKE_WINDOW_WORDS]
        window = " ".join(window_words)
        if any(term in window for term in _MED_ADJACENT_WORDS):
            return True
        if _DOSE_SHAPE_PATTERN.search(window):
            return True
    return False


# ---------------------------------------------------------------------------
# Repo-scanning guard rail
# ---------------------------------------------------------------------------


def _looks_like_prose(text: str) -> bool:
    """Pragmatic filter for "this string literal is end-user-facing prose."

    Known limitations (documented per task spec, not hidden): this is a
    heuristic, not a real static analyzer.
      * Skips anything with a backslash, which excludes regex-pattern source
        strings (this module's own pattern lists) but would also skip a
        genuine response string that happened to contain an escape (e.g. a
        literal "\\n" left unformatted) — acceptable false-negative for a
        style guard.
      * Skips single-token strings (no space) — filters out dict keys,
        format placeholders, and identifiers, but would also skip a
        one-word response fragment ("Understood." is 10 chars with no
        space... actually contains no space so it WOULD be skipped). A
        single unhedged word is not where prescriptive-language risk lives
        in practice, so this tradeoff favors fewer false alarms.
      * Does not distinguish an f-string's literal segments from its
        interpolated expressions — ``ast.get_source_segment`` on a
        ``JoinedStr`` returns the original source text including
        ``{expr}`` placeholders, so a variable name could theoretically
        collide with a flagged phrase. Not observed in practice on this
        codebase (see design note for actual scan output).
    """
    stripped = text.strip()
    if len(stripped) < 8:
        return False
    if "\\" in stripped:
        return False
    if " " not in stripped:
        return False
    return True


def _extract_literal_text(node: ast.AST, source: str) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return ast.get_source_segment(source, node)
    return None


def scan_assistant_module_for_violations(root_dir: str = "python/hearttwin/assistant") -> list[tuple[str, str]]:
    """Walk ``root_dir`` and flag string literals that read as prescriptive.

    Intended use: a future wave/CI step runs this against
    ``python/hearttwin/assistant`` (or any new response-generation package)
    before wiring new code into the pipeline. It is intentionally a
    heuristic over string literals and f-strings, not a full data-flow
    analysis of what actually reaches a user — see ``_looks_like_prose``
    for the specific tradeoffs. It skips this module's own source file
    (its pattern lists and docstrings quote the exact phrases this checker
    looks for, which would otherwise self-flag as a scanner artifact, not a
    real violation) and any ``test_*.py`` file.
    """
    root = Path(root_dir)
    if not root.exists():
        # Support being invoked with a repo-relative path regardless of the
        # caller's current working directory (e.g. from pytest run at repo
        # root, or from an arbitrary CI working directory).
        root = Path(__file__).resolve().parents[3] / root_dir

    violations: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*.py")):
        if path.name == "language_integrity.py" or path.name.startswith("test_") or "__pycache__" in path.parts:
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue

        seen: set[str] = set()
        for node in ast.walk(tree):
            text = _extract_literal_text(node, source)
            if text is None or text in seen or not _looks_like_prose(text):
                continue
            seen.add(text)
            result = scan_for_prescriptive_language(text)
            if result.flagged:
                snippet = " ".join(text.split())[:160]
                violations.append((str(path), f"[{result.category}] {snippet}"))
    return violations
