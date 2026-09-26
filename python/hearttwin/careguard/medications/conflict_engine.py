"""Deterministic, evidence-driven medication conflict engine.

Evaluates drug–drug, drug–disease, drug–organ, allergy, therapeutic duplication,
and monitoring-gap conflicts. A hard block (blocked_for_draft) requires tier-A
evidence (an official-label contraindication) OR an allergy match OR a duplicate
active ingredient. Supplemental sources (DDInter/SIDER) never hard-block.
"""

from __future__ import annotations

import uuid
from typing import Any

from python.hearttwin.careguard.medications import (
    dailymed_client,
    ddinter_adapter,
    label_section_parser,
    openfda_client,
    provenance,
    sider_adapter,
    therapeutic_class_mapper,
)
from python.hearttwin.careguard.medications.evidence_policy import can_hard_block
from python.hearttwin.careguard.medications.schemas import (
    MedicationIdentity,
    MedicationSafetyConflict,
)

_ACK = "Clinical decision support draft. Clinician and pharmacist review required."


def _cid() -> str:
    return f"conf-{uuid.uuid4().hex[:10]}"


def _label_for(med: MedicationIdentity) -> dict[str, Any] | None:
    return dailymed_client.retrieve_label(rxcui=med.rxcui, name=med.original_text) or \
        openfda_client.retrieve_label(rxcui=med.rxcui, name=med.original_text)


def _label_evidence(label: dict[str, Any], section: str, passage: str, supports: str):
    src = "dailymed_spl" if "dailymed" in label.get("retrieval_source", "") else "openfda_label"
    return provenance.make_evidence(
        source_type=src, authority_tier="A",
        source_title=label.get("title", "drug label"),
        supports=supports, section=section, exact_passage=passage,
        source_version=label_section_parser.label_version(label),
        effective_date=label_section_parser.effective_date(label),
        source_identifier=label.get("source_id"), local_snapshot_path=label.get("local_path"),
        confidence=0.85,
    )


def evaluate(
    *,
    proposed_and_active: list[MedicationIdentity],
    signals: dict[str, Any],
    guideline_monitoring=None,
) -> list[MedicationSafetyConflict]:
    conflicts: list[MedicationSafetyConflict] = []
    allergens = [a for a in signals.get("allergen_terms", []) if a]

    # Therapeutic duplication (same active ingredient / same class).
    conflicts.extend(_duplication(proposed_and_active))

    for med in proposed_and_active:
        label = _label_for(med)
        # 1. Allergy — hard block allowed without a label.
        for allergen in allergens:
            if allergen and (allergen in med.original_text.lower()
                             or any(allergen in i.lower() for i in med.ingredients)):
                conflicts.append(MedicationSafetyConflict(
                    conflict_id=_cid(), proposed_medication_id=med.medication_id,
                    patient_fact_ids=signals.get("allergy_fact_ids", []),
                    conflict_type="allergy_conflict", severity="blocked_for_draft",
                    headline=f"Documented allergy match: {med.original_text}",
                    clinical_statement=f"A documented allergy to {allergen} may match this medication's ingredient. {_ACK}",
                    can_display=True, requires_clinician_confirmation=True, requires_pharmacist_review=True,
                    confidence=0.6,
                ))

        if not label:
            conflicts.append(MedicationSafetyConflict(
                conflict_id=_cid(), proposed_medication_id=med.medication_id,
                conflict_type="insufficient_evidence", severity="insufficient_evidence",
                headline=f"No official label evidence for {med.original_text}",
                clinical_statement=f"No official drug label was retrievable; automated conflict checks could not be completed. {_ACK}",
                missing_information=["official drug-label evidence unavailable"],
                can_display=True, requires_pharmacist_review=True, confidence=0.3,
            ))
            continue

        # 2. Drug–disease / organ (renal + potassium pathway).
        hit_k, sect_k, text_k = label_section_parser.mentions(label, "hyperkalemia", "potassium")
        contra = label_section_parser.section_text(label, "contraindications")
        if hit_k and (signals.get("reduced_egfr") or signals.get("missing_potassium")):
            in_contra = bool(contra and ("potassium" in contra[1].lower() or "hyperkalemia" in contra[1].lower()
                                         or "renal" in contra[1].lower()))
            source_types = ["dailymed_spl" if "dailymed" in label.get("retrieval_source", "") else "openfda_label"]
            severity = "blocked_for_draft" if (in_contra and can_hard_block(source_types)) else "high_concern"
            ctype = "documented_contraindication" if severity == "blocked_for_draft" else "drug_organ_function_concern"
            ev = [_label_evidence(label, sect_k, text_k, "contraindication" if in_contra else "organ_consideration")]
            missing = ["serum potassium result not present"] if signals.get("missing_potassium") else []
            conflicts.append(MedicationSafetyConflict(
                conflict_id=_cid(), proposed_medication_id=med.medication_id,
                patient_fact_ids=signals.get("renal_fact_ids", []),
                conflict_type=ctype, severity=severity,
                headline=f"Renal / potassium concern: {med.original_text}",
                clinical_statement=(f"Labeling describes hyperkalemia risk that rises with reduced renal function; "
                                    f"this patient has "
                                    + ("reduced eGFR" if signals.get("reduced_egfr") else "")
                                    + (" and no recorded potassium" if signals.get("missing_potassium") else "")
                                    + f". {_ACK}"),
                mechanism_summary="Reduced renal potassium excretion increases hyperkalemia risk.",
                authoritative_evidence=ev,
                missing_information=missing,
                can_display=True, requires_clinician_confirmation=bool(missing), requires_pharmacist_review=True,
                confidence=0.8 if severity == "blocked_for_draft" else 0.7,
            ))
            # 3. Monitoring gap.
            if signals.get("missing_potassium"):
                conflicts.append(MedicationSafetyConflict(
                    conflict_id=_cid(), proposed_medication_id=med.medication_id,
                    conflict_type="monitoring_gap", severity="caution",
                    headline=f"Missing potassium monitoring for {med.original_text}",
                    clinical_statement=f"Labeling describes potassium/renal monitoring, but no serum potassium result is present. {_ACK}",
                    authoritative_evidence=[_label_evidence(label, sect_k, text_k, "warning")],
                    missing_information=["serum potassium"], can_display=True,
                    requires_pharmacist_review=True, confidence=0.6,
                ))

        # 4. Pregnancy pathway.
        hit_p, sect_p, text_p = label_section_parser.mentions(label, "pregnan", "fetal")
        if hit_p and signals.get("pregnancy_recorded"):
            conflicts.append(MedicationSafetyConflict(
                conflict_id=_cid(), proposed_medication_id=med.medication_id,
                conflict_type="drug_disease_interaction", severity="high_concern",
                headline=f"Pregnancy consideration: {med.original_text}",
                clinical_statement=f"Labeling describes fetal/pregnancy risk and pregnancy is recorded. {_ACK}",
                authoritative_evidence=[_label_evidence(label, sect_p, text_p, "warning")],
                can_display=True, requires_pharmacist_review=True, confidence=0.75,
            ))

    # 5. Drug–drug (DDInter supplemental, must be paired with label context).
    conflicts.extend(_drug_drug(proposed_and_active))
    return conflicts


def _duplication(meds: list[MedicationIdentity]) -> list[MedicationSafetyConflict]:
    out: list[MedicationSafetyConflict] = []
    by_ing: dict[str, list[MedicationIdentity]] = {}
    for m in meds:
        for ing in m.ingredients:
            by_ing.setdefault(ing.lower(), []).append(m)
    for ing, group in by_ing.items():
        if len({m.medication_id for m in group}) > 1:
            out.append(MedicationSafetyConflict(
                conflict_id=_cid(), proposed_medication_id=group[0].medication_id,
                interacting_medication_ids=[m.medication_id for m in group[1:]],
                conflict_type="therapeutic_duplication", severity="high_concern",
                headline=f"Duplicate active ingredient: {ing}",
                clinical_statement=f"More than one medication contains {ing} (same_active_ingredient). {_ACK}",
                can_display=True, requires_pharmacist_review=True, confidence=0.8,
            ))
    return out


def _drug_drug(meds: list[MedicationIdentity]) -> list[MedicationSafetyConflict]:
    names = [m.original_text for m in meds]
    rxcuis = [m.rxcui for m in meds if m.rxcui]
    records = ddinter_adapter.interactions(rxcuis, names)
    out: list[MedicationSafetyConflict] = []
    for rec in records:
        supp = provenance.make_evidence(
            source_type="ddinter", authority_tier="B",
            source_title="DDInter 2.0", supports="interaction",
            exact_passage=rec.get("mechanism"), source_version=rec.get("version"),
            source_identifier=rec.get("canonical_source"), confidence=0.5,
        )
        out.append(MedicationSafetyConflict(
            conflict_id=_cid(),
            proposed_medication_id=meds[0].medication_id if meds else "",
            conflict_type="drug_drug_interaction", severity="caution",
            headline=f"Potential interaction: {rec.get('drug_a')} + {rec.get('drug_b')}",
            clinical_statement=f"{rec.get('management', 'Interaction reported.')} {_ACK}",
            mechanism_summary=rec.get("mechanism"),
            supplemental_evidence=[supp],
            can_display=True, requires_pharmacist_review=True, confidence=0.5,
        ))
    return out
