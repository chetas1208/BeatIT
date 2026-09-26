"""Medication normalization + official-label evidence + contraindication engine.

RxNorm establishes drug identity; it is NOT the contraindication authority.
Conflicts are emitted only when backed by an official label passage; otherwise
CareGuard reports 'drug-label evidence unavailable'. Adverse-event reports are
never converted into verified contraindications. No interaction is invented.
"""

from __future__ import annotations

__all__ = ["rxnorm_client", "openfda_client", "dailymed_client", "contraindication_engine"]
