"""Deterministic report-mention extraction with negation / temporality /
experiencer detection. A report mention is NEVER a confirmed diagnosis; it
requires clinician confirmation before it can participate in a hard block.
"""

from __future__ import annotations

__all__ = ["condition_mention_extractor", "negation", "temporality", "experiencer"]
