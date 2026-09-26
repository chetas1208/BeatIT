"""Local-first guideline retriever: match patient topics to corpus passages.

Deterministic keyword/topic scoring. Returns verifiable citations or abstains.
External retrieval only when CAREGUARD_ALLOW_EXTERNAL_RESEARCH=true (not wired to
the network in the offline demo — abstention is the safe default).
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.evidence import citation, local_corpus, source_policy
from python.hearttwin.careguard.feature_flags import external_research_allowed
from python.hearttwin.careguard.schemas import EvidenceCitation


def _score(entry_topics: list[str], query_terms: set[str]) -> int:
    et = {t.lower() for t in entry_topics}
    return len(et & query_terms) + sum(
        1 for q in query_terms if any(q in t for t in et)
    )


def retrieve_guidelines(query_terms: set[str], *, limit: int = 4) -> tuple[list[EvidenceCitation], list[str]]:
    """Return (citations, warnings). Empty citations → caller must abstain."""
    query_terms = {t.lower() for t in query_terms if t}
    scored: list[tuple[int, dict[str, Any]]] = []
    for e in local_corpus.guideline_entries():
        s = _score(e.get("topics", []), query_terms)
        if s > 0 and source_policy.can_ground_recommendation(e):
            scored.append((s, e))
    scored.sort(key=lambda t: t[0], reverse=True)

    warnings: list[str] = []
    if not scored:
        if not external_research_allowed():
            warnings.append(
                "No approved local guideline passage matched; external retrieval is disabled — "
                "abstaining rather than grounding on unverifiable evidence."
            )
        else:
            warnings.append("No approved guideline passage found even with external retrieval enabled.")
        return [], warnings

    cites = [citation.from_guideline(e) for _, e in scored[:limit]]
    return cites, warnings


def retrieve_label(rxcui: str | None, name: str | None) -> dict[str, Any] | None:
    """Return the corpus drug label for an rxcui/name, or None (→ unavailable)."""
    name_l = (name or "").lower()
    for lbl in local_corpus.drug_labels():
        if rxcui and lbl.get("rxcui") == rxcui:
            return lbl
        if name_l and name_l in lbl.get("medication", "").lower():
            return lbl
    return None
