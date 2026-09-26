"""CareGuard FHIR R4 ingestion — deterministic, provenance-preserving.

No LLM parses clinical state here: a Bundle is validated and walked with pure
Python, and every extracted value becomes a ``ClinicalFact`` carrying a
``json_pointer`` back to its source resource. Model inference never becomes a
recorded fact.
"""

from __future__ import annotations

__all__ = ["parser", "bundle_validator", "terminology", "provenance"]
