"""AllergyIntolerance → ClinicalFact, preserving criticality and reaction text."""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.fhir import terminology
from python.hearttwin.careguard.fhir.provenance import entry_pointer, make_fact
from python.hearttwin.careguard.fhir.resources import status_of
from python.hearttwin.careguard.schemas import ClinicalFact


def extract(resource: dict[str, Any], entry_index: int, bundle_id: str) -> list[ClinicalFact]:
    concept = resource.get("code") or {}
    key, code, display = terminology.preferred_coding(concept)
    criticality = resource.get("criticality")
    fact = make_fact(
        category="allergy",
        resource_type="AllergyIntolerance",
        resource_id=resource.get("id", ""),
        source_bundle_id=bundle_id,
        json_pointer=entry_pointer(entry_index, "code"),
        value=display or (concept.get("text") if isinstance(concept, dict) else None),
        code_system=key,
        code=code,
        display=display or concept.get("text"),
        status=status_of(resource) or (f"criticality:{criticality}" if criticality else None),
        assertion_type="recorded",
    )
    return [fact]
