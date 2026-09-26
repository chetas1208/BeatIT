"""Deterministic experiencer detection (patient vs family vs other)."""

from __future__ import annotations

_FAMILY = ("family history", "fh ", "fhx", "mother", "father", "sibling", "parent",
           "brother", "sister", "maternal", "paternal", "grandmother", "grandfather")


def classify(snippet: str) -> str:
    low = snippet.lower()
    if any(c in low for c in _FAMILY):
        return "family"
    return "patient"
