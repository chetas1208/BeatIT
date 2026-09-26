"""DDInter 2.0 supplemental interaction adapter (offline snapshot).

DDInter is SUPPLEMENTAL (tier B): it may seed interaction candidates and
alternative leads, but never overrides an official label and its alternative
leads are never displayed until independently verified (spec §4, §11).
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.evidence import local_corpus
from python.hearttwin.careguard.medications.source_registry import source_enabled


def interactions(rxcuis: list[str], names: list[str]) -> list[dict[str, Any]]:
    if not source_enabled("ddinter"):
        return []
    name_set = {n.lower() for n in names if n}
    rx_set = {r for r in rxcuis if r}
    out = []
    for rec in local_corpus.med_sources().get("ddinter", []):
        a, b = rec.get("drug_a", "").lower(), rec.get("drug_b", "").lower()
        ra, rb = rec.get("rxcui_a"), rec.get("rxcui_b")
        if ({a, b} & name_set) or ({ra, rb} & rx_set):
            rec = dict(rec)
            rec["_supplemental"] = True
            rec["_requires_verification"] = True
            out.append(rec)
    return out


def version() -> str | None:
    import os

    return os.environ.get("DDINTER_VERSION") or "2.0-demo"
