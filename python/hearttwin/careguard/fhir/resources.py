"""Small FHIR resource helpers shared by the extractors."""

from __future__ import annotations

from typing import Any, Optional


def status_of(resource: dict[str, Any]) -> Optional[str]:
    """Best-effort status across resource types."""
    if "status" in resource:
        return resource.get("status")
    cs = resource.get("clinicalStatus") or {}
    for c in cs.get("coding", []) or []:
        if c.get("code"):
            return c.get("code")
    return None


def effective_of(resource: dict[str, Any]) -> Optional[str]:
    for key in ("effectiveDateTime", "onsetDateTime", "recordedDate", "issued", "authoredOn"):
        if resource.get(key):
            return resource.get(key)
    period = resource.get("effectivePeriod") or {}
    return period.get("start")


def quantity(node: Optional[dict[str, Any]]) -> tuple[Optional[float], Optional[str]]:
    if not isinstance(node, dict):
        return (None, None)
    val = node.get("value")
    unit = node.get("unit") or node.get("code")
    try:
        return (float(val) if val is not None else None, unit)
    except (TypeError, ValueError):
        return (None, unit)


def reference_id(node: Optional[dict[str, Any]]) -> Optional[str]:
    if not isinstance(node, dict):
        return None
    ref = node.get("reference")
    if not ref:
        return None
    return ref.split("/")[-1] if "/" in ref else ref
