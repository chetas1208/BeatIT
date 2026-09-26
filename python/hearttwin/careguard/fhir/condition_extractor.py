"""Condition → ClinicalFact(s). Never infers an unrecorded condition."""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.fhir import terminology
from python.hearttwin.careguard.fhir.provenance import entry_pointer, make_fact
from python.hearttwin.careguard.fhir.resources import effective_of, status_of
from python.hearttwin.careguard.schemas import ClinicalFact

# SNOMED/ICD hints that classify a condition as cardiac (display-text fallback only).
_CARDIAC_HINTS = (
    "heart", "cardiac", "cardio", "coronary", "myocard", "ventric", "atrial",
    "arrhythm", "fibrillation", "ischemi", "infarct", "angina", "valv",
)


def is_cardiac(display: str, codes: list[dict]) -> bool:
    text = (display or "").lower()
    if any(h in text for h in _CARDIAC_HINTS):
        return True
    for c in codes:
        if any(h in (c.get("display", "").lower()) for h in _CARDIAC_HINTS):
            return True
        if str(c.get("code", "")).startswith("I"):  # ICD-10 circulatory chapter
            return True
    return False


def extract(resource: dict[str, Any], entry_index: int, bundle_id: str) -> list[ClinicalFact]:
    concept = resource.get("code") or {}
    key, code, display = terminology.preferred_coding(concept)
    status = status_of(resource)
    fact = make_fact(
        category="condition",
        resource_type="Condition",
        resource_id=resource.get("id", ""),
        source_bundle_id=bundle_id,
        json_pointer=entry_pointer(entry_index, "code"),
        value=display or (concept.get("text") if isinstance(concept, dict) else None),
        code_system=key,
        code=code,
        display=display or concept.get("text"),
        status=status,
        effective_at=effective_of(resource),
        assertion_type="recorded",
    )
    return [fact]
