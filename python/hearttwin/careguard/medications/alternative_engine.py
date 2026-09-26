"""Evidence-bounded alternative candidate generation.

Candidates come ONLY from Orange Book (generic equivalence), RxClass siblings
constrained by a guideline, or cross-class options a guideline explicitly lists —
never from model memory. Every candidate is re-run through the full conflict
engine; equal/stronger conflict → excluded. Never ranked "safest/best/optimal".
When nothing qualifies, a no-alternative message is returned.
"""

from __future__ import annotations

import uuid
from typing import Any

from python.hearttwin.careguard.medications import (
    conflict_engine,
    orange_book_client,
    provenance,
    rxnorm_client,
    therapeutic_class_mapper,
)
from python.hearttwin.careguard.medications.evidence_policy import require_guideline_for_alternatives
from python.hearttwin.careguard.medications.schemas import (
    MedicationAlternativeCandidate,
    MedicationIdentity,
)

NO_ALTERNATIVE_MESSAGE = (
    "No adequately supported lower-conflict medication candidate was identified from the "
    "configured evidence sources. Additional clinician or pharmacist review is required."
)

# Guideline passage cue → class_members key (only classes the guideline names).
_CLASS_CUES = {
    "sglt2": "Sodium-glucose co-transporter 2 (SGLT2) inhibitors",
    "mineralocorticoid": "Mineralocorticoid receptor antagonists",
    "mra": "Mineralocorticoid receptor antagonists",
}


def _identity(name: str, rxcui: str | None) -> MedicationIdentity:
    norm = rxnorm_client.normalize(name=name, coded_rxcui=rxcui)
    return MedicationIdentity(
        medication_id=f"cand-{uuid.uuid4().hex[:8]}",
        original_text=name, rxcui=norm.get("rxcui"),
        ingredients=[name.split()[0]] if name else [], status="proposed",
        source_resource_type="candidate",
        normalization_confidence=0.9 if norm.get("resolved") else 0.3,
    )


def _conflict_burden(identity: MedicationIdentity, signals: dict[str, Any]) -> list:
    return conflict_engine.evaluate(proposed_and_active=[identity], signals=signals)


def _guideline_classes(citations: list[dict]) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    seen = set()
    for c in citations:
        passage = (c.get("passage") or "").lower()
        for cue, cls in _CLASS_CUES.items():
            if cue in passage and cls not in seen:
                seen.add(cls)
                out.append((cls, c))
    return out


def _display_status(hard: list, burden: list) -> str:
    """excluded if a hard conflict; needs-more-info if no official label was found;
    else a review candidate."""
    if hard:
        return "excluded_due_to_conflict"
    if any(c.severity == "insufficient_evidence" for c in burden):
        return "requires_more_information"
    return "candidate_for_clinician_review"


def _score(identity, guideline_ev, label_burden) -> tuple[float, float, float]:
    completeness = round(0.5 + 0.25 * bool(guideline_ev) + 0.25 * bool(identity.rxcui), 3)
    hard = sum(1 for c in label_burden if c.severity in ("blocked_for_draft", "high_concern"))
    burden = round(min(1.0, hard / 3.0), 3)
    freshness = 1.0 if guideline_ev else 0.5
    return completeness, burden, freshness


def generate(
    *,
    target_med: MedicationIdentity,
    signals: dict[str, Any],
    guideline_citations: list[dict],
    indication: str,
) -> list[MedicationAlternativeCandidate]:
    candidates: list[MedicationAlternativeCandidate] = []
    ingredient_is_conflict = bool(signals.get("reduced_egfr") or signals.get("missing_potassium"))

    # 1. Generic equivalents (Orange Book). Excluded if the ingredient itself conflicts.
    ob = orange_book_client.equivalents(target_med.rxcui)
    if ob:
        for eq in ob.get("equivalents", []):
            ident = _identity(eq.get("name", ""), eq.get("rxcui"))
            status = "excluded_due_to_conflict" if ingredient_is_conflict else "candidate_for_clinician_review"
            candidates.append(MedicationAlternativeCandidate(
                candidate_id=f"alt-{uuid.uuid4().hex[:8]}",
                original_proposed_medication_id=target_med.medication_id,
                medication_identity=ident, alternative_type="generic_equivalent",
                indication_under_review=indication,
                label_evidence=[provenance.make_evidence(
                    source_type="orange_book", authority_tier="A", source_title="FDA Orange Book",
                    supports="generic_equivalence", section="therapeutic_equivalence",
                    exact_passage=f"TE code {eq.get('te_code')}", source_identifier=ob.get("canonical_source"))],
                reasons_considered=["same active ingredient, strength, dosage form, and route"],
                unresolved_questions=(["generic equivalence does not resolve an ingredient-level conflict"]
                                      if ingredient_is_conflict else []),
                evidence_completeness_score=0.7, conflict_burden_score=1.0 if ingredient_is_conflict else 0.0,
                source_freshness_score=0.8, display_status=status, pharmacist_review_recommended=True,
            ))

    # 2/3. Same-class + cross-class candidates — require guideline grounding.
    if require_guideline_for_alternatives() and not guideline_citations:
        return candidates or []

    # Same-class siblings of the target (e.g., other MRAs).
    for sib in therapeutic_class_mapper.sibling_members(target_med.rxcui):
        ident = _identity(sib.get("name", ""), sib.get("rxcui"))
        burden = _conflict_burden(ident, signals)
        gl = [c for c in guideline_citations if (sib.get("class_name", "").split()[0].lower() in (c.get("passage") or "").lower())]
        hard = [c for c in burden if c.severity in ("blocked_for_draft", "high_concern")]
        comp, bscore, fresh = _score(ident, gl, burden)
        candidates.append(MedicationAlternativeCandidate(
            candidate_id=f"alt-{uuid.uuid4().hex[:8]}",
            original_proposed_medication_id=target_med.medication_id,
            medication_identity=ident, alternative_type="same_guideline_supported_class",
            indication_under_review=indication,
            guideline_evidence=[provenance.make_evidence(
                source_type="clinical_guideline", authority_tier="A",
                source_title=gl[0].get("title", "guideline"), supports="therapeutic_class",
                exact_passage=gl[0].get("passage"), source_version=gl[0].get("version"),
                effective_date=gl[0].get("publication_date"), source_identifier=gl[0].get("source_id"))] if gl else [],
            documented_conflicts=burden,
            reasons_considered=[f"member of {sib.get('class_name')} (same class as reviewed medication)"],
            unresolved_questions=[c.headline for c in hard],
            evidence_completeness_score=comp, conflict_burden_score=bscore, source_freshness_score=fresh,
            display_status=_display_status(hard, burden),
            pharmacist_review_recommended=True,
        ))

    # Cross-class options the guideline explicitly names.
    target_ingredient = (target_med.ingredients[0].lower() if target_med.ingredients else "")
    for cls, cite in _guideline_classes(guideline_citations):
        for member in therapeutic_class_mapper.class_members(cls):
            if target_ingredient and target_ingredient in (member.get("name", "").lower()):
                continue  # not cross-class if it's the same drug
            ident = _identity(member.get("name", ""), member.get("rxcui"))
            burden = _conflict_burden(ident, signals)
            hard = [c for c in burden if c.severity in ("blocked_for_draft", "high_concern")]
            comp, bscore, fresh = _score(ident, [cite], burden)
            candidates.append(MedicationAlternativeCandidate(
                candidate_id=f"alt-{uuid.uuid4().hex[:8]}",
                original_proposed_medication_id=target_med.medication_id,
                medication_identity=ident, alternative_type="cross_class_guideline_candidate",
                indication_under_review=indication,
                guideline_evidence=[provenance.make_evidence(
                    source_type="clinical_guideline", authority_tier="A",
                    source_title=cite.get("title", "guideline"), supports="indication",
                    exact_passage=cite.get("passage"), source_version=cite.get("version"),
                    effective_date=cite.get("publication_date"), source_identifier=cite.get("source_id"))],
                documented_conflicts=burden,
                reasons_considered=[f"guideline names the {cls} strategy for this indication"],
                unresolved_questions=[c.headline for c in hard],
                missing_information=[c.missing_information[0] for c in burden if c.missing_information],
                evidence_completeness_score=comp, conflict_burden_score=bscore, source_freshness_score=fresh,
                display_status=_display_status(hard, burden),
                pharmacist_review_recommended=True,
            ))

    return _dedupe(candidates)


def _dedupe(cands: list[MedicationAlternativeCandidate]) -> list[MedicationAlternativeCandidate]:
    """Keep one candidate per (rxcui or name); prefer a displayable status."""
    order = {"candidate_for_clinician_review": 0, "requires_more_information": 1,
             "excluded_due_to_conflict": 2, "insufficient_evidence": 3}
    best: dict[str, MedicationAlternativeCandidate] = {}
    for c in cands:
        key = c.medication_identity.rxcui or c.medication_identity.original_text.lower()
        if key not in best or order.get(c.display_status, 9) < order.get(best[key].display_status, 9):
            best[key] = c
    return list(best.values())


def displayable(candidates: list[MedicationAlternativeCandidate]) -> list[MedicationAlternativeCandidate]:
    return [c for c in candidates if c.display_status == "candidate_for_clinician_review"]
