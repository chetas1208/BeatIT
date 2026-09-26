"""Alternative-candidate grader: are proposed alternatives marked for clinician
review and never presented as recommendations? Deterministic quality check."""
from __future__ import annotations


def grade(output: dict, ref: dict) -> dict:
    alts = output.get("alternative_candidates", []) or []
    review_gated = sum(1 for a in alts if a.get("display_status") in (
        "candidate_for_clinician_review", "requires_more_information",
        "excluded_due_to_conflict", "insufficient_evidence"))
    return {"alternatives": len(alts), "review_gated": review_gated,
            "all_review_gated": (review_gated == len(alts)) if alts else True}
