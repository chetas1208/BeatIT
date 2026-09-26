"""Terminology helpers — preserve codes verbatim, never invent them.

Maps a FHIR coding ``system`` URI to a short key (snomed/loinc/rxnorm/icd10/ucum)
and picks a preferred code from a CodeableConcept without discarding local codes.
"""

from __future__ import annotations

from typing import Any, Optional

from python.hearttwin.careguard.constants import CODE_SYSTEMS

_SYSTEM_TO_KEY = {uri: key for key, uri in CODE_SYSTEMS.items()}
# Preference order when a concept carries multiple codings.
_PREFERENCE = ("rxnorm", "loinc", "snomed", "icd10")


def system_key(system_uri: Optional[str]) -> Optional[str]:
    if not system_uri:
        return None
    if system_uri in _SYSTEM_TO_KEY:
        return _SYSTEM_TO_KEY[system_uri]
    low = system_uri.lower()
    for key in CODE_SYSTEMS:
        if key in low:
            return key
    return None  # unknown/local system — preserved as-is by callers


def codings(concept: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(concept, dict):
        return []
    out = []
    for c in concept.get("coding", []) or []:
        if isinstance(c, dict):
            out.append(c)
    return out


def preferred_coding(concept: Optional[dict[str, Any]]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (code_system_key_or_uri, code, display) using the preference order.

    Falls back to the raw system URI (never dropped) and to concept ``text``.
    """
    cs = codings(concept)
    if not cs:
        text = (concept or {}).get("text") if isinstance(concept, dict) else None
        return (None, None, text)

    ranked: list[tuple[int, dict[str, Any]]] = []
    for c in cs:
        key = system_key(c.get("system"))
        rank = _PREFERENCE.index(key) if key in _PREFERENCE else len(_PREFERENCE)
        ranked.append((rank, c))
    ranked.sort(key=lambda t: t[0])
    best = ranked[0][1]
    key = system_key(best.get("system")) or best.get("system")
    return (key, best.get("code"), best.get("display") or (concept or {}).get("text"))


def all_codes(concept: Optional[dict[str, Any]]) -> list[dict[str, str]]:
    """Every code preserved (for downstream matching), local codes included."""
    out = []
    for c in codings(concept):
        out.append(
            {
                "system": system_key(c.get("system")) or (c.get("system") or "local"),
                "code": c.get("code") or "",
                "display": c.get("display") or "",
            }
        )
    return out
