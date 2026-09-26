"""Deterministic temporality detection for a mention snippet."""

from __future__ import annotations

_HISTORICAL = ("history of", "h/o", "prior", "previous", "past", "status post", "s/p", "remote", "resolved")
_FUTURE = ("plan to", "will start", "scheduled", "future", "anticipated")


def classify(snippet: str) -> str:
    low = snippet.lower()
    if any(c in low for c in _HISTORICAL):
        return "historical"
    if any(c in low for c in _FUTURE):
        return "future"
    if any(c in low for c in ("current", "active", "ongoing", "now")):
        return "current"
    return "unknown"
