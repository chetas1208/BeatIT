"""Authority hierarchy + policy: a research paper can't substitute for a clinical
guideline when grounding a candidate care-plan review (spec §8).
"""

from __future__ import annotations

AUTHORITY = {
    1: "clinical_regulatory",   # FDA labeling, DailyMed SPL, ACC/AHA/HFSA, KDIGO, ADA, FDA CDS
    2: "interoperability",      # HL7 FHIR, US Core, SMART, CDS Hooks
    3: "peer_reviewed_research",  # digital-twin / ECG / segmentation methodology
    4: "internal_implementation",  # architecture, mapping, testing
}


def can_ground_recommendation(entry: dict) -> bool:
    """Only Level-1 (and Level-2 for interoperability facts) may ground a
    clinical care-plan recommendation. Research papers (Level 3) cannot."""
    level = entry.get("authority_level")
    return level == 1


def is_research_paper(entry: dict) -> bool:
    return entry.get("authority_level") == 3 or entry.get("document_type") == "research_paper"


def rejects_domain(entry: dict, allowed_domains: set[str]) -> bool:
    """True if the source's organization/domain is not on the approved list."""
    org = (entry.get("organization") or "").lower()
    if not allowed_domains:
        return False
    return not any(d in org for d in allowed_domains)
