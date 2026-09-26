"""Provenance helpers — build ClinicalFacts with a JSON pointer to their source.

The JSON pointer is relative to the Bundle root (RFC 6901), e.g.
``/entry/7/resource/valueQuantity/value`` — so any fact can be traced to the
exact field in the exact resource it came from.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from python.hearttwin.careguard.schemas import AssertionType, ClinicalFact


def entry_pointer(entry_index: int, *suffix: str) -> str:
    parts = ["/entry", str(entry_index), "resource", *suffix]
    return "/" + "/".join(p.strip("/") for p in parts if p != "")


def make_fact(
    *,
    category: str,
    resource_type: str,
    resource_id: str,
    source_bundle_id: str,
    json_pointer: str,
    value: Any = None,
    unit: Optional[str] = None,
    code_system: Optional[str] = None,
    code: Optional[str] = None,
    display: Optional[str] = None,
    status: Optional[str] = None,
    effective_at: Optional[str] = None,
    confidence: float = 1.0,
    assertion_type: AssertionType = "recorded",
) -> ClinicalFact:
    return ClinicalFact(
        fact_id=f"fact-{uuid.uuid4().hex[:12]}",
        category=category,
        value=value,
        unit=unit,
        code_system=code_system,
        code=code,
        display=display,
        status=status,
        effective_at=effective_at,
        resource_type=resource_type,
        resource_id=resource_id,
        json_pointer=json_pointer,
        source_bundle_id=source_bundle_id,
        confidence=confidence,
        assertion_type=assertion_type,
    )


def missing_fact(*, category: str, description: str, source_bundle_id: str) -> ClinicalFact:
    """A first-class 'missing' fact — evidence CareGuard looked for and did not find."""
    return ClinicalFact(
        fact_id=f"missing-{uuid.uuid4().hex[:12]}",
        category=category,
        value=None,
        display=description,
        resource_type="Missing",
        resource_id="",
        json_pointer="",
        source_bundle_id=source_bundle_id,
        confidence=0.0,
        assertion_type="missing",
    )
