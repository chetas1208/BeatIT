"""FHIR R4 Bundle structural validation.

Returns a structured summary (never raises for *content* problems — only for a
fundamentally non-Bundle input). Unsupported resources are recorded, not dropped
silently; broken references and duplicates are reported.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from python.hearttwin.careguard.constants import SUPPORTED_FHIR_RESOURCES
from python.hearttwin.careguard.errors import FhirValidationError


class ValidationSummary(BaseModel):
    valid: bool
    bundle_id: str = ""
    bundle_type: str = ""
    total_entries: int = 0
    supported: list[dict] = Field(default_factory=list)
    unsupported: list[dict] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    resource_counts: dict[str, int] = Field(default_factory=dict)
    has_patient: bool = False


def validate_bundle(bundle: Any) -> ValidationSummary:
    if not isinstance(bundle, dict):
        raise FhirValidationError("Input is not a FHIR Bundle object", issues=["not_an_object"])
    if bundle.get("resourceType") != "Bundle":
        raise FhirValidationError(
            f"resourceType must be 'Bundle', got {bundle.get('resourceType')!r}",
            issues=["resourceType_not_bundle"],
        )

    entries = bundle.get("entry") or []
    summary = ValidationSummary(
        valid=True,
        bundle_id=bundle.get("id", ""),
        bundle_type=bundle.get("type", ""),
        total_entries=len(entries),
    )
    if not isinstance(entries, list):
        summary.valid = False
        summary.issues.append("entry_not_a_list")
        return summary

    seen_ids: set[tuple[str, str]] = set()
    known_refs: set[str] = set()
    counts: dict[str, int] = {}

    for i, entry in enumerate(entries):
        resource = (entry or {}).get("resource") if isinstance(entry, dict) else None
        if not isinstance(resource, dict):
            summary.issues.append(f"entry[{i}] has no resource object")
            continue
        rtype = resource.get("resourceType", "")
        rid = resource.get("id", "")
        counts[rtype] = counts.get(rtype, 0) + 1

        if rtype == "Patient":
            summary.has_patient = True
        if rid:
            key = (rtype, rid)
            if key in seen_ids:
                summary.issues.append(f"duplicate resource id {rtype}/{rid}")
            seen_ids.add(key)
            known_refs.add(f"{rtype}/{rid}")
        else:
            summary.warnings.append(f"entry[{i}] {rtype} has no id")

        # Required status fields for common resource types.
        if rtype in ("Observation", "MedicationRequest", "Encounter", "DiagnosticReport", "ServiceRequest"):
            if not resource.get("status"):
                summary.warnings.append(f"{rtype}/{rid} missing required status")

        record = {"index": i, "resourceType": rtype, "id": rid}
        if rtype in SUPPORTED_FHIR_RESOURCES:
            summary.supported.append(record)
        else:
            summary.unsupported.append(record)

    # Reference resolution (subject/patient references must resolve within Bundle).
    for i, entry in enumerate(entries):
        resource = (entry or {}).get("resource") if isinstance(entry, dict) else None
        if not isinstance(resource, dict):
            continue
        for field in ("subject", "patient", "encounter"):
            ref = (resource.get(field) or {}).get("reference") if isinstance(resource.get(field), dict) else None
            if ref and "/" in ref and not ref.startswith("urn:") and ref not in known_refs:
                summary.warnings.append(f"unresolved reference {ref} in entry[{i}]")

    summary.resource_counts = counts
    if not summary.has_patient:
        summary.warnings.append("Bundle has no Patient resource")
    return summary
