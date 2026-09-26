"""FDA Orange Book generic-equivalence lookup (offline snapshot).

Generic equivalence does NOT resolve an ingredient-level contraindication
(spec §11): if the active ingredient is the source of conflict, equivalents are
excluded by the alternative engine.
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.evidence import local_corpus


def equivalents(rxcui: str | None) -> dict[str, Any] | None:
    if not rxcui:
        return None
    return local_corpus.med_sources().get("orange_book", {}).get(rxcui)
