"""Deterministic safety critic for the medication-safety output (spec §14)."""

from __future__ import annotations

import re
from typing import Any

from python.hearttwin.careguard.medications.schemas import (
    MedicationSafetyConflict,
    MedicationSafetyCriticOutput,
)

_DOSE = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|g|units?|ml)\b", re.IGNORECASE)
_BANNED = ("safe medication", "best medication", "optimal treatment", "safest", "best choice",
           "no risk", "clinically approved by the system", "cannot be prescribed")


def critique(
    *,
    conflicts: list[MedicationSafetyConflict],
    alternatives: list[Any],
    report_mentions_confirmed_as_fact: bool,
) -> MedicationSafetyCriticOutput:
    blocked: list[str] = []
    unsupported: list[str] = []
    missing_sources: list[str] = []
    unverified_alts: list[str] = []
    hidden: list[str] = []

    for c in conflicts:
        # Hard conclusion without tier-A evidence.
        if c.severity == "blocked_for_draft" and c.conflict_type != "allergy_conflict":
            if not any(e.authority_tier == "A" for e in c.authoritative_evidence):
                blocked.append(f"hard block {c.conflict_id} lacks tier-A evidence")
        if _DOSE.search(c.clinical_statement):
            blocked.append(f"conflict {c.conflict_id} contains a dose")
        if any(b in c.clinical_statement.lower() for b in _BANNED):
            blocked.append(f"conflict {c.conflict_id} uses banned certainty/safety language")

    for a in alternatives:
        text = " ".join(a.reasons_considered) + a.medication_identity.original_text
        if any(b in text.lower() for b in _BANNED):
            blocked.append(f"alternative {a.candidate_id} uses banned safety/superiority language")
        if _DOSE.search(text):
            blocked.append(f"alternative {a.candidate_id} contains a dose")
        if a.display_status == "candidate_for_clinician_review" and not (a.guideline_evidence or a.label_evidence):
            blocked.append(f"alternative {a.candidate_id} displayed without guideline/label evidence")
            unverified_alts.append(a.candidate_id)
        if not a.clinician_review_required:
            blocked.append(f"alternative {a.candidate_id} missing clinician-review requirement")

    if report_mentions_confirmed_as_fact:
        blocked.append("a possible report mention was treated as a confirmed diagnosis")

    return MedicationSafetyCriticOutput(
        safe_to_display=not blocked,
        blocked_reasons=blocked,
        unsupported_claims=unsupported,
        missing_sources=missing_sources,
        unverified_alternatives=unverified_alts,
        hidden_uncertainty=hidden,
        required_revisions=[],
    )
