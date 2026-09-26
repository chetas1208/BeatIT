"""Source freshness: flag stale/undated guideline sources.

Uses a supplied reference date (never a live clock — see spec's determinism rule;
the API layer passes 'today' explicitly).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from python.hearttwin.careguard.config import max_source_age_days, require_source_version


def _parse(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        return date.fromisoformat(d[:10])
    except ValueError:
        return None


def assess(entry: dict, *, today: Optional[date] = None) -> dict:
    """Return {fresh, stale, undated, missing_version, age_days, reasons}."""
    reasons: list[str] = []
    pub = _parse(entry.get("publication_date") or entry.get("effective_date"))
    version = entry.get("version") or entry.get("label_version")
    missing_version = require_source_version() and not version
    if missing_version:
        reasons.append("source version/effective date required but absent")

    # Clinical guidelines stay valid for years until a newer version supersedes
    # them; age alone does not retire them. The age limit applies to time-sensitive
    # sources (drug labels, datasets). Supersession/undated/missing-version always
    # disqualify, for any source type.
    doc_type = entry.get("document_type", "")
    age_exempt = doc_type == "clinical_guideline"
    superseded = bool(entry.get("superseded_by") or entry.get("retired"))
    if superseded:
        reasons.append(f"source superseded by {entry.get('superseded_by', 'a newer version')}")

    age_days = None
    stale = superseded
    undated = pub is None
    if undated:
        reasons.append("source has no parseable date")
    elif today is not None:
        age_days = (today - pub).days
        if age_days > max_source_age_days() and not age_exempt:
            stale = True
            reasons.append(f"source is {age_days} days old (> {max_source_age_days()} allowed)")

    return {
        "fresh": not (stale or undated or missing_version),
        "stale": stale,
        "undated": undated,
        "missing_version": missing_version,
        "age_days": age_days,
        "reasons": reasons,
    }
