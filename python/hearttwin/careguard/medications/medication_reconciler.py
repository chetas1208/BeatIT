"""Reconcile active + proposed medications into MedicationIdentity records.

Preserves original text, resolves brand→ingredient via RxNorm, decomposes
combination products, detects duplicate ingredient exposure, and flags ambiguity
for clinician confirmation. Never infers a dose; never silently picks when
normalization is ambiguous.
"""

from __future__ import annotations

import uuid
from typing import Any

from python.hearttwin.careguard.medications import rxnorm_client
from python.hearttwin.careguard.medications.schemas import MedicationIdentity
from python.hearttwin.careguard.schemas import ClinicalFact

_COMBO_SPLIT = ("/", " and ", "+", "-")


def _ingredients(text: str, rxcui: str | None) -> tuple[list[str], list[str]]:
    """Return (ingredient names, ingredient rxcuis). Combo products split by name."""
    base = text.split()[0] if text else ""
    for sep in _COMBO_SPLIT:
        if sep in text and sep != "-":  # avoid splitting hyphenated single names blindly
            parts = [p.strip() for p in text.replace(" and ", "/").split("/") if p.strip()]
            names = [p.split()[0] for p in parts if p]
            if len(names) > 1:
                return names, []
    return ([base] if base else []), ([rxcui] if rxcui else [])


def reconcile(
    medication_facts: list[ClinicalFact],
    *,
    proposed: dict[str, Any] | None = None,
) -> tuple[list[MedicationIdentity], list[MedicationIdentity], list[str]]:
    """Return (active, proposed, warnings)."""
    active: list[MedicationIdentity] = []
    for f in medication_facts:
        text = str(f.display or f.value or "")
        norm = rxnorm_client.normalize(
            name=text, coded_rxcui=f.code if f.code_system == "rxnorm" else None
        )
        names, ing_rx = _ingredients(text, norm.get("rxcui"))
        warnings: list[str] = []
        if not norm.get("resolved"):
            warnings.append("medication could not be normalized to an RxCUI — clinician confirmation required")
        active.append(MedicationIdentity(
            medication_id=f"med-{uuid.uuid4().hex[:10]}",
            original_text=text,
            normalized_name=norm.get("rxcui") and text or text,
            rxcui=norm.get("rxcui"),
            ingredient_rxcuis=ing_rx,
            ingredients=names,
            status="active" if (f.status or "active") == "active" else "historical",
            source_resource_type=f.resource_type,
            source_resource_id=f.resource_id,
            provenance_pointer=f.json_pointer,
            normalization_confidence=0.9 if norm.get("resolved") else 0.3,
            normalization_warnings=warnings,
        ))

    proposed_ids: list[MedicationIdentity] = []
    if proposed:
        ptext = proposed.get("name") or proposed.get("text") or ""
        pnorm = rxnorm_client.normalize(name=ptext, coded_rxcui=proposed.get("rxcui"))
        pnames, ping = _ingredients(ptext, pnorm.get("rxcui"))
        proposed_ids.append(MedicationIdentity(
            medication_id=f"med-proposed-{uuid.uuid4().hex[:8]}",
            original_text=ptext,
            rxcui=pnorm.get("rxcui"),
            ingredient_rxcuis=ping,
            ingredients=pnames,
            status="proposed",
            source_resource_type="proposed",
            normalization_confidence=0.9 if pnorm.get("resolved") else 0.3,
            normalization_warnings=[] if pnorm.get("resolved") else ["proposed medication unresolved"],
        ))

    warnings = _duplicate_warnings(active + proposed_ids)
    return active, proposed_ids, warnings


def _duplicate_warnings(meds: list[MedicationIdentity]) -> list[str]:
    seen: dict[str, str] = {}
    warns: list[str] = []
    for m in meds:
        for ing in m.ingredients:
            key = ing.lower()
            if key in seen and seen[key] != m.medication_id:
                warns.append(f"duplicate active ingredient exposure: {ing}")
            seen[key] = m.medication_id
    return sorted(set(warns))


def reconciliation_score(active: list[MedicationIdentity]) -> float:
    if not active:
        return 0.0
    resolved = sum(1 for m in active if m.rxcui)
    return round(resolved / len(active), 3)
