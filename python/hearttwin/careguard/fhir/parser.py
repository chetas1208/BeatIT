"""Top-level FHIR Bundle parser → deidentified ClinicalFacts + validation summary.

Deterministic. Dispatches each supported resource to its extractor, deduplicates,
and flags critical missing evidence (e.g. a potassium result absent while a
potassium-affecting medication is present).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from python.hearttwin.careguard.fhir import (
    allergy_extractor,
    bundle_validator,
    condition_extractor,
    medication_extractor,
    observation_extractor,
)
from python.hearttwin.careguard.fhir.bundle_validator import ValidationSummary
from python.hearttwin.careguard.fhir.provenance import entry_pointer, make_fact
from python.hearttwin.careguard.fhir.resources import effective_of, status_of
from python.hearttwin.careguard.fhir import terminology
from python.hearttwin.careguard.schemas import ClinicalFact

# Critical evidence CareGuard expects for a cardiorenal medication review.
# (code, human label) — potassium is load-bearing for K-affecting drugs.
_CRITICAL_LABS = {
    "2823-3": "serum potassium",
    "6298-4": "serum potassium",
}
_POTASSIUM_SENSITIVE_HINTS = ("spironolactone", "eplerenone", "lisinopril", "losartan", "ace", "arb", "potassium")

_GENERIC_EXTRACTORS = {
    "Condition": condition_extractor.extract,
    "Observation": observation_extractor.extract,
    "MedicationRequest": medication_extractor.extract,
    "MedicationStatement": medication_extractor.extract,
    "AllergyIntolerance": allergy_extractor.extract,
}


class ParsedBundle(BaseModel):
    bundle_id: str
    validation: ValidationSummary
    facts: list[ClinicalFact] = Field(default_factory=list)
    unsupported_resources: list[dict] = Field(default_factory=list)
    missing_critical_evidence: list[str] = Field(default_factory=list)


def _procedure_fact(resource: dict[str, Any], i: int, bundle_id: str) -> list[ClinicalFact]:
    key, code, display = terminology.preferred_coding(resource.get("code") or {})
    return [
        make_fact(
            category="procedure",
            resource_type="Procedure",
            resource_id=resource.get("id", ""),
            source_bundle_id=bundle_id,
            json_pointer=entry_pointer(i, "code"),
            value=display,
            code_system=key,
            code=code,
            display=display,
            status=status_of(resource),
            effective_at=effective_of(resource),
        )
    ]


def parse_bundle(bundle: dict[str, Any]) -> ParsedBundle:
    summary = bundle_validator.validate_bundle(bundle)
    bundle_id = summary.bundle_id or "bundle"
    facts: list[ClinicalFact] = []
    entries = bundle.get("entry") or []

    for i, entry in enumerate(entries):
        resource = (entry or {}).get("resource") if isinstance(entry, dict) else None
        if not isinstance(resource, dict):
            continue
        rtype = resource.get("resourceType", "")
        extractor = _GENERIC_EXTRACTORS.get(rtype)
        if extractor:
            facts.extend(extractor(resource, i, bundle_id))
        elif rtype == "Procedure":
            facts.extend(_procedure_fact(resource, i, bundle_id))

    facts = _dedupe(facts)
    missing = _detect_missing_evidence(facts)
    return ParsedBundle(
        bundle_id=bundle_id,
        validation=summary,
        facts=facts,
        unsupported_resources=summary.unsupported,
        missing_critical_evidence=missing,
    )


def _dedupe(facts: list[ClinicalFact]) -> list[ClinicalFact]:
    seen: set[tuple] = set()
    out: list[ClinicalFact] = []
    for f in facts:
        key = (f.category, f.resource_type, f.resource_id, f.code, str(f.value))
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def _detect_missing_evidence(facts: list[ClinicalFact]) -> list[str]:
    missing: list[str] = []
    codes = {f.code for f in facts if f.code}
    med_text = " ".join(
        str(f.display or f.value or "").lower() for f in facts if f.category == "medication"
    )
    has_potassium = any(c in _CRITICAL_LABS for c in codes) or any(
        "potassium" in str(f.display or "").lower() for f in facts if f.category == "observation"
    )
    potassium_relevant = any(h in med_text for h in _POTASSIUM_SENSITIVE_HINTS)
    if potassium_relevant and not has_potassium:
        missing.append(
            "No serum potassium result present, but a potassium-affecting medication "
            "is recorded — potassium is required to reason about hyperkalemia risk."
        )
    # Renal function needed whenever renally-cleared meds or CKD present.
    has_egfr = any((f.code == "48642-3") for f in facts) or any(
        "glomerular" in str(f.display or "").lower() for f in facts
    )
    ckd = any("kidney" in str(f.display or "").lower() or str(f.code or "").startswith("N18") for f in facts)
    if ckd and not has_egfr:
        missing.append("Chronic kidney disease recorded but no eGFR result present.")
    return missing
