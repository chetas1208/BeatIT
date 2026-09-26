"""RxClass memberships + class members. Offline → supplemental corpus; online →
RxNav rxclass API when external retrieval is enabled. Class membership never
implies interchangeability (spec §4).
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.evidence import local_corpus
from python.hearttwin.careguard.feature_flags import external_research_allowed
from python.hearttwin.careguard.medications.source_registry import source_enabled


def memberships(rxcui: str | None) -> list[dict[str, Any]]:
    if not rxcui or not source_enabled("rxclass"):
        return []
    data = local_corpus.med_sources().get("rxclass", {})
    if rxcui in data:
        return data[rxcui]
    if external_research_allowed():  # pragma: no cover - network
        return _online_memberships(rxcui)
    return []


def members_of_class(class_name: str) -> list[dict[str, Any]]:
    if not source_enabled("rxclass"):
        return []
    return local_corpus.med_sources().get("class_members", {}).get(class_name, [])


def _online_memberships(rxcui: str) -> list[dict[str, Any]]:  # pragma: no cover - network
    import os

    import httpx

    base = os.environ.get("RXCLASS_API_BASE", "https://rxnav.nlm.nih.gov/REST/rxclass").rstrip("/")
    try:
        r = httpx.get(f"{base}/class/byRxcui.json", params={"rxcui": rxcui}, timeout=15)
        out = []
        for item in r.json().get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
            ci = item.get("rxclassMinConceptItem", {})
            out.append({"class_id": ci.get("classId"), "class_name": ci.get("className"),
                        "class_type": ci.get("classType"), "source": "rxclass"})
        return out
    except Exception:
        return []
