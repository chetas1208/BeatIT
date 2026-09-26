"""DrugCentral enrichment adapter (offline, optional). Not the final
contraindication authority — enrichment/cross-reference only (spec §4).
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.medications.source_registry import source_enabled


def enrichment(rxcui: str | None, name: str | None) -> dict[str, Any] | None:
    if not source_enabled("drugcentral"):
        return None
    # No local DrugCentral snapshot bundled; returns a clear "not loaded" marker
    # so the pipeline discloses the gap rather than fabricating enrichment.
    return {"source": "drugcentral", "loaded": False,
            "note": "DrugCentral enabled but no DRUGCENTRAL_DATA_PATH snapshot configured."}
