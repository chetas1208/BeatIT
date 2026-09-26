"""MedicationRequest / MedicationStatement → ClinicalFact.

Preserves the original medication text AND the RxNorm code when present. RxNorm
normalization to a canonical RxCUI happens later (medication_safety agent); this
extractor only records what the Bundle actually contains.
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.fhir import terminology
from python.hearttwin.careguard.fhir.provenance import entry_pointer, make_fact
from python.hearttwin.careguard.fhir.resources import effective_of, status_of
from python.hearttwin.careguard.schemas import ClinicalFact


def extract(resource: dict[str, Any], entry_index: int, bundle_id: str) -> list[ClinicalFact]:
    concept = resource.get("medicationCodeableConcept") or {}
    key, code, display = terminology.preferred_coding(concept)
    original_text = concept.get("text") if isinstance(concept, dict) else None
    rxcui = None
    for c in terminology.all_codes(concept):
        if c["system"] == "rxnorm":
            rxcui = c["code"]
            break
    fact = make_fact(
        category="medication",
        resource_type=resource.get("resourceType", "MedicationStatement"),
        resource_id=resource.get("id", ""),
        source_bundle_id=bundle_id,
        json_pointer=entry_pointer(entry_index, "medicationCodeableConcept"),
        value=original_text or display,
        code_system="rxnorm" if rxcui else key,
        code=rxcui or code,
        display=display or original_text,
        status=status_of(resource),
        effective_at=effective_of(resource),
        assertion_type="recorded",
    )
    return [fact]
