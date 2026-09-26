"""Extract condition mentions from unstructured report text (deterministic).

A mention is classified via negation / temporality / experiencer cues. Nothing
here becomes a confirmed diagnosis — every mention needs clinician confirmation.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from python.hearttwin.careguard.reports import experiencer, negation, temporality
from python.hearttwin.careguard.medications.schemas import ConditionMention

# Small clinical vocabulary (display, matcher). Extend via config in production.
_VOCAB: list[tuple[str, str]] = [
    ("atrial fibrillation", r"atrial fibrillation|afib|a-fib|a\.?fib"),
    ("obstructive sleep apnea", r"sleep apnea|osa\b"),
    ("chronic kidney disease", r"chronic kidney disease|ckd\b"),
    ("diabetes mellitus", r"diabetes|dm2|type 2 diabetes|t2dm"),
    ("COPD", r"copd|chronic obstructive pulmonary disease"),
    ("heart failure", r"heart failure|hfref|hfpef|chf\b"),
    ("hypertension", r"hypertension|htn\b"),
    ("gout", r"\bgout\b"),
    ("hyperkalemia", r"hyperkalemia"),
    ("pulmonary embolism", r"pulmonary embolism|\bpe\b"),
    ("anemia", r"\banemia\b"),
    ("cirrhosis", r"cirrhosis|hepatic impairment"),
]


def _status(snippet: str, exp: str) -> str:
    if exp == "family":
        return "family_history"
    if negation.is_ruled_out(snippet):
        return "ruled_out"
    if negation.is_negated(snippet):
        return "negated_report_mention"
    if negation.is_uncertain(snippet):
        return "uncertain"
    return "possible_report_mention"


def _sentences(text: str) -> list[str]:
    # Split on sentence terminators and newlines/semicolons so cues from an
    # adjacent sentence never contaminate a mention's classification.
    return [s.strip() for s in re.split(r"[.;\n]+", text) if s.strip()]


def extract(text: str, *, document_id: str = "report", section: str | None = None) -> list[ConditionMention]:
    if not text:
        return []
    mentions: list[ConditionMention] = []
    seen: set[str] = set()
    for sentence in _sentences(text):
        for display, pattern in _VOCAB:
            m = re.search(pattern, sentence, flags=re.IGNORECASE)
            if not m or display in seen:
                continue
            seen.add(display)
            exp = experiencer.classify(sentence)
            temporal = temporality.classify(sentence)
            status = _status(sentence, exp)
            mentions.append(ConditionMention(
                mention_id=f"cm-{uuid.uuid4().hex[:10]}",
                raw_text=m.group(0),
                normalized_display=display,
                status=status,  # type: ignore[arg-type]
                temporality=temporal,  # type: ignore[arg-type]
                experiencer=exp,  # type: ignore[arg-type]
                source_document_id=document_id,
                section=section,
                exact_snippet=sentence,
                confidence=0.5 if status == "possible_report_mention" else 0.4,
            ))
    return mentions


def requiring_confirmation(mentions: list[ConditionMention]) -> list[ConditionMention]:
    """Only patient-experiencer, non-negated, non-family mentions need confirmation."""
    return [m for m in mentions if m.status in ("possible_report_mention", "uncertain")]
