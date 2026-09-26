"""Local-first clinical evidence: retrieve verifiable passages from an approved
local corpus; abstain rather than guess. Claude's memory is never a source.
"""

from __future__ import annotations

__all__ = ["local_corpus", "retriever", "citation", "freshness", "source_policy"]
