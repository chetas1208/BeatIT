"""Evidence source registry — tiers, priorities, configuration + license gates.

Tier A = authoritative clinical/regulatory (RxNorm, RxClass, DailyMed, openFDA,
Orange Book, guidelines). Tier B = curated supplemental (DDInter, DrugCentral,
SIDER). Tier C = licensed (DrugBank — disabled without confirmed license).
Tier D (Kaggle/scraped/blogs) is PROHIBITED as clinical authority.
"""

from __future__ import annotations

import os
from typing import Any

from python.hearttwin.tools.env_config import env_bool

# source_id → (tier, human title, env base or data-path var)
SOURCES: dict[str, dict[str, Any]] = {
    "rxnorm": {"tier": "A", "title": "RxNorm", "base_env": "RXNORM_API_BASE",
               "default_base": "https://rxnav.nlm.nih.gov/REST", "role": "identity"},
    "rxclass": {"tier": "A", "title": "RxClass", "base_env": "RXCLASS_API_BASE",
                "default_base": "https://rxnav.nlm.nih.gov/REST/rxclass", "role": "therapeutic_class"},
    "dailymed": {"tier": "A", "title": "DailyMed SPL", "base_env": "DAILYMED_API_BASE",
                 "default_base": "https://dailymed.nlm.nih.gov/dailymed/services/v2", "role": "label"},
    "openfda": {"tier": "A", "title": "openFDA Drug Labeling", "base_env": "OPENFDA_API_BASE",
                "default_base": "https://api.fda.gov", "role": "label_fallback"},
    "orange_book": {"tier": "A", "title": "FDA Orange Book", "data_env": "ORANGE_BOOK_DATA_PATH",
                    "version_env": "ORANGE_BOOK_VERSION", "role": "generic_equivalence"},
    "ddinter": {"tier": "B", "title": "DDInter 2.0", "data_env": "DDINTER_DATA_PATH",
                "version_env": "DDINTER_VERSION", "enable_env": "DDINTER_ENABLED", "role": "supplemental_interaction"},
    "drugcentral": {"tier": "B", "title": "DrugCentral", "data_env": "DRUGCENTRAL_DATA_PATH",
                    "version_env": "DRUGCENTRAL_VERSION", "enable_env": "DRUGCENTRAL_ENABLED", "role": "enrichment"},
    "sider": {"tier": "B", "title": "SIDER", "data_env": "SIDER_DATA_PATH",
              "version_env": "SIDER_VERSION", "enable_env": "SIDER_ENABLED", "role": "supplemental_adverse"},
    "drugbank": {"tier": "C", "title": "DrugBank (licensed)", "data_env": "DRUGBANK_DATA_PATH",
                 "enable_env": "DRUGBANK_ENABLED", "role": "licensed"},
}

# Explicitly prohibited as clinical authority (development fixtures only).
PROHIBITED_AS_AUTHORITY = (
    "kaggle", "scraped_pharmacy", "consumer_interaction_checker", "blog", "reddit",
    "model_memory", "autocomplete_guess", "unlicensed_commercial",
)


def _get(env: str, default: str = "") -> str:
    return os.environ.get(env, default).strip()


def drugbank_loadable() -> tuple[bool, str]:
    """DrugBank must refuse to load unless the license is confirmed."""
    if not env_bool("DRUGBANK_ENABLED", False):
        return False, "DrugBank is disabled (DRUGBANK_ENABLED=false)."
    if not env_bool("DRUGBANK_LICENSE_CONFIRMED", False):
        return False, "DrugBank refused: DRUGBANK_LICENSE_CONFIRMED != true (no license)."
    if not _get("DRUGBANK_DATA_PATH"):
        return False, "DrugBank enabled but DRUGBANK_DATA_PATH is unset."
    return True, "DrugBank license confirmed."


def source_enabled(source_id: str) -> bool:
    spec = SOURCES.get(source_id)
    if not spec:
        return False
    if source_id == "drugbank":
        return drugbank_loadable()[0]
    enable_env = spec.get("enable_env")
    if enable_env and not env_bool(enable_env, True):
        return False
    return True


def source_status(source_id: str) -> dict[str, Any]:
    spec = SOURCES[source_id]
    base = _get(spec["base_env"], spec.get("default_base", "")) if spec.get("base_env") else ""
    data_path = _get(spec["data_env"]) if spec.get("data_env") else ""
    version = _get(spec["version_env"]) if spec.get("version_env") else None
    status = {
        "source_id": source_id,
        "title": spec["title"],
        "authority_tier": spec["tier"],
        "role": spec["role"],
        "enabled": source_enabled(source_id),
        "api_base_configured": bool(base),
        "data_path_configured": bool(data_path),
        "version": version,
    }
    if source_id == "drugbank":
        ok, reason = drugbank_loadable()
        status["loadable"] = ok
        status["license_note"] = reason
    return status


def all_source_status() -> list[dict[str, Any]]:
    return [source_status(sid) for sid in SOURCES]


def assert_not_prohibited(source_label: str) -> None:
    low = (source_label or "").lower()
    for bad in PROHIBITED_AS_AUTHORITY:
        if bad in low:
            from python.hearttwin.careguard.errors import SafetyBoundaryError

            raise SafetyBoundaryError(
                f"source {source_label!r} is prohibited as clinical authority (tier D)",
                reason="prohibited_source",
            )
