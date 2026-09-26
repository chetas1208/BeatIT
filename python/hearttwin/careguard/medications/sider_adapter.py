"""SIDER supplemental adverse-effect adapter (offline snapshot).

SIDER is SUPPLEMENTAL ONLY: it can NEVER trigger a hard block and can NEVER mark
an alternative as safer (spec §4). Signals are displayed as context.
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.evidence import local_corpus
from python.hearttwin.careguard.medications.source_registry import source_enabled


def effects(rxcui: str | None) -> list[dict[str, Any]]:
    if not rxcui or not source_enabled("sider"):
        return []
    sigs = local_corpus.med_sources().get("sider", {}).get(rxcui, [])
    for s in sigs:
        s = dict(s)
        s["_supplemental_only"] = True
        s["_can_block"] = False
    return sigs
