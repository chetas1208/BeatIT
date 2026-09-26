"""Build MedicationEvidence objects with hashes + retrieval metadata."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from python.hearttwin.careguard.medications.schemas import (
    AuthorityTier,
    EvidenceSource,
    EvidenceSupports,
    MedicationEvidence,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(text: str) -> str:
    return hashlib.sha256((text or "").encode()).hexdigest()


def make_evidence(
    *,
    source_type: EvidenceSource,
    authority_tier: AuthorityTier,
    source_title: str,
    supports: EvidenceSupports,
    section: Optional[str] = None,
    exact_passage: Optional[str] = None,
    source_version: Optional[str] = None,
    effective_date: Optional[str] = None,
    source_identifier: Optional[str] = None,
    local_snapshot_path: Optional[str] = None,
    confidence: float = 0.7,
) -> MedicationEvidence:
    return MedicationEvidence(
        evidence_id=f"ev-{uuid.uuid4().hex[:10]}",
        source_type=source_type,
        authority_tier=authority_tier,
        source_title=source_title,
        source_version=source_version,
        effective_date=effective_date,
        retrieved_at=_now(),
        section=section,
        exact_passage=exact_passage,
        source_identifier=source_identifier,
        local_snapshot_path=local_snapshot_path,
        source_hash=_hash(exact_passage or source_title),
        supports=supports,
        confidence=confidence,
    )
