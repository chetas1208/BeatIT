"""openFDA drug-label retrieval (fallback label source). Offline → local corpus.

openFDA also exposes adverse-event reports; CareGuard deliberately does NOT use
those as contraindication evidence (spec §10) — only the drug LABEL endpoint.
"""

from __future__ import annotations

from typing import Any, Optional

from python.hearttwin.careguard.evidence import retriever
from python.hearttwin.careguard.feature_flags import external_research_allowed


def retrieve_label(*, rxcui: Optional[str], name: Optional[str]) -> Optional[dict[str, Any]]:
    label = retriever.retrieve_label(rxcui, name)
    if label:
        label = dict(label)
        label["retrieval_source"] = "local_corpus_openfda"
        return label
    if external_research_allowed():  # pragma: no cover - network
        return _retrieve_online(name=name)
    return None


def _retrieve_online(*, name: Optional[str]) -> Optional[dict[str, Any]]:  # pragma: no cover
    import os

    import httpx

    base = os.environ.get("OPENFDA_API_BASE", "https://api.fda.gov").rstrip("/")
    key = os.environ.get("OPENFDA_API_KEY", "")
    params = {"search": f'openfda.generic_name:"{name}"', "limit": 1}
    if key:
        params["api_key"] = key
    try:
        r = httpx.get(f"{base}/drug/label.json", params=params, timeout=20)
        results = r.json().get("results", [])
        if results:
            return {"retrieval_source": "openfda", "raw": results[0], "sections": {}, "medication": name}
    except Exception:  # noqa: BLE001
        return None
    return None
