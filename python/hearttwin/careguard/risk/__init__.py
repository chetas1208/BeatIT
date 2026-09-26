"""Deterministic cross-organ risk evaluation. Records facts and gaps; never
diagnoses a new condition. Domain evaluators live in sibling modules; the matrix
assembles them.
"""

from __future__ import annotations

__all__ = ["cross_organ_matrix"]
