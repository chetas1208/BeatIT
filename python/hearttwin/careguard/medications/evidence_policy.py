"""Evidence policy: what each source may and may not do (spec §4, §11, §14)."""

from __future__ import annotations

from python.hearttwin.tools.env_config import env_bool

# Sources that may support a HARD block (blocked_for_draft).
HARD_BLOCK_SOURCES = {"dailymed_spl", "openfda_label", "local_approved_document", "clinical_guideline"}

# Sources that are SUPPLEMENTAL only — never a hard block, never "safer".
SUPPLEMENTAL_ONLY = {"ddinter", "drugcentral", "sider", "rxnorm", "rxclass"}


def require_official_label_for_hard_block() -> bool:
    return env_bool("CAREGUARD_REQUIRE_OFFICIAL_LABEL_FOR_HARD_BLOCK", True)


def require_guideline_for_alternatives() -> bool:
    return env_bool("CAREGUARD_REQUIRE_GUIDELINE_FOR_ALTERNATIVES", True)


def allow_unverified_alternatives() -> bool:
    return env_bool("CAREGUARD_ALLOW_UNVERIFIED_ALTERNATIVES", False)


def can_hard_block(evidence_source_types: list[str]) -> bool:
    """A hard block requires at least one hard-block-capable source."""
    if not require_official_label_for_hard_block():
        return True
    return any(s in HARD_BLOCK_SOURCES for s in evidence_source_types)


def is_supplemental_only(source_type: str) -> bool:
    return source_type in SUPPLEMENTAL_ONLY


def sider_can_block() -> bool:
    return False  # SIDER never blocks (spec §4)


def ddinter_needs_verification() -> bool:
    return True  # DDInter alternatives always independently verified (spec §11)
