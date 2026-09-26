"""Deterministic contraindication engine.

Emits a MedicationConflict ONLY when an official label passage supports it. When
no label is available, reports 'drug-label evidence unavailable' — never a guess.
Renal/potassium/pregnancy/allergy signals come from recorded patient facts.
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.constants import DRUG_LABEL_UNAVAILABLE
from python.hearttwin.careguard.evidence import citation
from python.hearttwin.careguard.medications import dailymed_client, openfda_client
from python.hearttwin.careguard.schemas import MedicationConflict


def _label_for(rxcui: str | None, name: str | None) -> dict[str, Any] | None:
    return dailymed_client.retrieve_label(rxcui=rxcui, name=name) or openfda_client.retrieve_label(
        rxcui=rxcui, name=name
    )


def _mentions(sections: dict, *terms: str) -> tuple[bool, str, str]:
    for sect in ("warnings", "contraindications", "boxed_warning"):
        text = (sections.get(sect) or "")
        low = text.lower()
        if any(t in low for t in terms):
            return True, sect, text
    return False, "", ""


def evaluate(*, med: dict[str, Any], context: dict[str, Any], fact_ids: list[str]) -> list[MedicationConflict]:
    name = med.get("original_text") or med.get("display") or ""
    rxcui = med.get("rxcui")
    label = _label_for(rxcui, name)
    conflicts: list[MedicationConflict] = []

    if not label:
        conflicts.append(
            MedicationConflict(
                medication_name=name,
                rxcui=rxcui,
                conflict_type="label_unavailable",
                severity="informational",
                patient_fact_ids=fact_ids,
                missing_information=[DRUG_LABEL_UNAVAILABLE],
                statement=f"{DRUG_LABEL_UNAVAILABLE} for {name}; no official contraindication check possible.",
                confidence=0.3,
            )
        )
        return conflicts

    sections = label.get("sections", {})

    # Hyperkalemia / potassium pathway (renal-sensitive).
    hits_k, sect_k, text_k = _mentions(sections, "hyperkalemia", "potassium")
    if hits_k and (context.get("reduced_egfr") or context.get("missing_potassium")):
        severity = "high" if (context.get("reduced_egfr") and context.get("missing_potassium")) else "caution"
        cites = [citation.from_drug_label(label, sect_k, text_k)]
        gcite = context.get("guideline_monitoring_citation")
        if gcite:
            cites.append(gcite)
        missing = []
        if context.get("missing_potassium"):
            missing.append("serum potassium result not present")
        conflicts.append(
            MedicationConflict(
                medication_name=name,
                rxcui=rxcui,
                conflict_type="renal_potassium_risk",
                severity=severity,
                patient_fact_ids=fact_ids + context.get("renal_fact_ids", []),
                evidence_citations=cites,
                missing_information=missing,
                statement=(
                    f"Label for {name} describes hyperkalemia risk that rises with renal impairment; "
                    f"this patient has "
                    + ("reduced eGFR" if context.get("reduced_egfr") else "")
                    + (" and " if context.get("reduced_egfr") and context.get("missing_potassium") else "")
                    + ("no recorded serum potassium" if context.get("missing_potassium") else "")
                    + " — a monitoring consideration for clinician review."
                ),
                confidence=0.8 if severity == "high" else 0.6,
            )
        )

    # Pregnancy pathway.
    hits_p, sect_p, text_p = _mentions(sections, "pregnan", "fetal")
    if hits_p and context.get("pregnancy_recorded"):
        conflicts.append(
            MedicationConflict(
                medication_name=name,
                rxcui=rxcui,
                conflict_type="pregnancy",
                severity="high",
                patient_fact_ids=fact_ids,
                evidence_citations=[citation.from_drug_label(label, sect_p, text_p)],
                statement=f"Label for {name} describes fetal/pregnancy risk and pregnancy is recorded.",
                confidence=0.8,
            )
        )

    # Allergy cross-check (only when the med name matches a recorded allergen).
    for allergen in context.get("allergen_terms", []):
        if allergen and allergen in name.lower():
            conflicts.append(
                MedicationConflict(
                    medication_name=name,
                    rxcui=rxcui,
                    conflict_type="allergy",
                    severity="high",
                    patient_fact_ids=fact_ids + context.get("allergy_fact_ids", []),
                    statement=f"{name} may relate to a documented allergy to {allergen}.",
                    confidence=0.5,
                )
            )
    return conflicts
