"""DrugBank adapter — REFUSES to load without a confirmed license (spec §4).

DrugBank data must never be loaded when DRUGBANK_LICENSE_CONFIRMED != true, and
must never be copied from GitHub/Kaggle/unofficial mirrors.
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.medications.source_registry import drugbank_loadable


def load_guard() -> dict[str, Any]:
    ok, reason = drugbank_loadable()
    return {"loadable": ok, "reason": reason, "source": "drugbank"}


def lookup(rxcui: str | None, name: str | None) -> dict[str, Any] | None:
    ok, reason = drugbank_loadable()
    if not ok:
        # Do not load, do not fabricate — disclose the license state.
        return {"source": "drugbank", "loaded": False, "reason": reason}
    # A licensed deployment would read DRUGBANK_DATA_PATH here.
    return {"source": "drugbank", "loaded": True, "note": "licensed lookup not bundled in demo"}
