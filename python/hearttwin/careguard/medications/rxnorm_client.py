"""RxNorm normalization. Offline: use the RxCUI already coded in FHIR, else map
by name against the local corpus. Online (external tests only): query RxNav.

Never invents an RxCUI. Preserves the original medication text.
"""

from __future__ import annotations

from typing import Any, Optional

from python.hearttwin.careguard.evidence import local_corpus
from python.hearttwin.careguard.feature_flags import external_research_allowed


def _corpus_name_to_rxcui(name: str) -> Optional[str]:
    n = name.lower()
    for lbl in local_corpus.drug_labels():
        if lbl.get("medication", "").lower() in n or n in lbl.get("medication", "").lower():
            return lbl.get("rxcui")
    return None


def normalize(*, name: str, coded_rxcui: Optional[str] = None) -> dict[str, Any]:
    """Return {original_text, rxcui, resolved, source}. Deterministic offline."""
    if coded_rxcui:
        return {"original_text": name, "rxcui": coded_rxcui, "resolved": True, "source": "fhir_coding"}

    rxcui = _corpus_name_to_rxcui(name)
    if rxcui:
        return {"original_text": name, "rxcui": rxcui, "resolved": True, "source": "local_corpus"}

    if external_research_allowed():
        online = _normalize_online(name)
        if online:
            return online

    return {"original_text": name, "rxcui": None, "resolved": False, "source": "unresolved"}


def _normalize_online(name: str) -> Optional[dict[str, Any]]:  # pragma: no cover - network
    import os

    import httpx

    base = os.environ.get("RXNORM_API_BASE", "https://rxnav.nlm.nih.gov/REST").rstrip("/")
    try:
        r = httpx.get(f"{base}/rxcui.json", params={"name": name}, timeout=15)
        ids = r.json().get("idGroup", {}).get("rxnormId", [])
        if ids:
            return {"original_text": name, "rxcui": ids[0], "resolved": True, "source": "rxnav"}
    except Exception:  # noqa: BLE001
        return None
    return None


def resolve_brand_generic(meds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse duplicates that resolve to the same RxCUI (brand/generic)."""
    seen: dict[str, dict] = {}
    out: list[dict] = []
    for m in meds:
        rx = m.get("rxcui")
        if rx and rx in seen:
            seen[rx].setdefault("aliases", []).append(m.get("original_text"))
            continue
        if rx:
            seen[rx] = m
        out.append(m)
    return out
