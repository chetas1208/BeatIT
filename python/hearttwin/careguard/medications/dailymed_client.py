"""DailyMed SPL label retrieval (primary label source). Offline → local corpus."""

from __future__ import annotations

from typing import Any, Optional

from python.hearttwin.careguard.evidence import retriever
from python.hearttwin.careguard.feature_flags import external_research_allowed


def retrieve_label(*, rxcui: Optional[str], name: Optional[str]) -> Optional[dict[str, Any]]:
    label = retriever.retrieve_label(rxcui, name)
    if label:
        label = dict(label)
        label["retrieval_source"] = "local_corpus_dailymed"
        return label
    if external_research_allowed():  # pragma: no cover - network
        return _retrieve_online(rxcui=rxcui, name=name)
    return None


def _retrieve_online(*, rxcui: Optional[str], name: Optional[str]) -> Optional[dict[str, Any]]:  # pragma: no cover
    import os

    import httpx

    base = os.environ.get("DAILYMED_API_BASE", "https://dailymed.nlm.nih.gov/dailymed/services/v2").rstrip("/")
    try:
        r = httpx.get(f"{base}/spls.json", params={"drug_name": name or ""}, timeout=20)
        data = r.json().get("data", [])
        if data:
            return {"retrieval_source": "dailymed", "raw": data[0], "sections": {}, "medication": name}
    except Exception:  # noqa: BLE001
        return None
    return None
