"""Build EvidenceCitation objects from corpus entries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from python.hearttwin.careguard.schemas import EvidenceCitation


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def from_guideline(entry: dict[str, Any], *, passage: str | None = None) -> EvidenceCitation:
    return EvidenceCitation(
        source_id=entry["source_id"],
        organization=entry.get("organization", ""),
        title=entry.get("title", ""),
        version=entry.get("version"),
        publication_date=entry.get("publication_date"),
        section=entry.get("section"),
        page=entry.get("page"),
        passage=passage or entry.get("passage", ""),
        recommendation_class=entry.get("recommendation_class"),
        evidence_level=entry.get("evidence_level"),
        local_path=entry.get("local_path"),
        canonical_source=entry.get("canonical_source"),
        sha256=entry.get("sha256"),
        retrieved_at=_now(),
        authority_level=entry.get("authority_level"),
        document_type=entry.get("document_type"),
        synthetic_excerpt=entry.get("synthetic_excerpt"),
    )


def from_drug_label(label: dict[str, Any], section: str, passage: str) -> EvidenceCitation:
    return EvidenceCitation(
        source_id=label["source_id"],
        organization=label.get("organization", ""),
        title=label.get("title", ""),
        version=label.get("label_version"),
        publication_date=label.get("effective_date"),
        section=section,
        passage=passage,
        local_path=label.get("local_path"),
        canonical_source=label.get("canonical_source"),
        sha256=label.get("sha256"),
        retrieved_at=_now(),
        authority_level=label.get("authority_level", 1),
    )
