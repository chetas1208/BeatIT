"""Observation → ClinicalFact(s). Preserves units and LOINC codes; supports
BP-style component observations. Values are recorded, never derived here.
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.fhir import terminology
from python.hearttwin.careguard.fhir.provenance import entry_pointer, make_fact
from python.hearttwin.careguard.fhir.resources import effective_of, quantity, status_of
from python.hearttwin.careguard.schemas import ClinicalFact


def extract(resource: dict[str, Any], entry_index: int, bundle_id: str) -> list[ClinicalFact]:
    facts: list[ClinicalFact] = []
    status = status_of(resource)
    effective = effective_of(resource)
    rid = resource.get("id", "")

    components = resource.get("component") or []
    if components:
        for ci, comp in enumerate(components):
            key, code, display = terminology.preferred_coding(comp.get("code") or {})
            val, unit = quantity(comp.get("valueQuantity"))
            facts.append(
                make_fact(
                    category="observation",
                    resource_type="Observation",
                    resource_id=rid,
                    source_bundle_id=bundle_id,
                    json_pointer=entry_pointer(entry_index, "component", str(ci), "valueQuantity", "value"),
                    value=val,
                    unit=unit,
                    code_system=key,
                    code=code,
                    display=display,
                    status=status,
                    effective_at=effective,
                )
            )
        return facts

    key, code, display = terminology.preferred_coding(resource.get("code") or {})
    val, unit = quantity(resource.get("valueQuantity"))
    if val is None and resource.get("valueString"):
        val = resource.get("valueString")
    facts.append(
        make_fact(
            category="observation",
            resource_type="Observation",
            resource_id=rid,
            source_bundle_id=bundle_id,
            json_pointer=entry_pointer(entry_index, "valueQuantity", "value"),
            value=val,
            unit=unit,
            code_system=key,
            code=code,
            display=display,
            status=status,
            effective_at=effective,
        )
    )
    return facts
