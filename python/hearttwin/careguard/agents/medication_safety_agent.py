"""Agent 5 — Medication & Contraindication.

Normalizes medications via RxNorm, resolves brand/generic duplicates, retrieves
official label evidence (DailyMed → openFDA), and builds an evidence-backed
conflict matrix. No interaction is invented; 'drug-label evidence unavailable' is
reported when no label exists.
"""

from __future__ import annotations

from python.hearttwin.careguard.agents.base import StageTimer, make_stage_result
from python.hearttwin.careguard.constants import STAGE_MEDICATION_SAFETY
from python.hearttwin.careguard.evidence.citation import EvidenceCitation
from python.hearttwin.careguard.medications import contraindication_engine, rxnorm_client
from python.hearttwin.careguard.risk.signals import extract_signals
from python.hearttwin.careguard.schemas import CareGuardContext, CareGuardStageResult, PatientContext


def _guideline_monitoring_citation(ctx: CareGuardContext) -> EvidenceCitation | None:
    for c in ctx.prior_stage_outputs.get("citations", []) or []:
        section = (c.get("section") or "").lower()
        if "monitor" in section or "mra" in section:
            return EvidenceCitation.model_validate(c)
    cits = ctx.prior_stage_outputs.get("citations", []) or []
    return EvidenceCitation.model_validate(cits[0]) if cits else None


async def run(ctx: CareGuardContext) -> CareGuardStageResult:
    timer = StageTimer()
    pc_dict = ctx.prior_stage_outputs.get("patient_context")
    pc = PatientContext.model_validate(pc_dict) if pc_dict else PatientContext(case_id=ctx.case_id)
    signals = extract_signals(pc)

    normalized = []
    for m in pc.medications:
        norm = rxnorm_client.normalize(name=str(m.display or m.value or ""), coded_rxcui=m.code if m.code_system == "rxnorm" else None)
        norm["fact_id"] = m.fact_id
        normalized.append(norm)
    normalized = rxnorm_client.resolve_brand_generic(normalized)

    context = {
        "reduced_egfr": signals["reduced_egfr"],
        "missing_potassium": signals["missing_potassium"],
        "pregnancy_recorded": signals["pregnancy_recorded"],
        "allergen_terms": signals["allergen_terms"],
        "allergy_fact_ids": signals["allergy_fact_ids"],
        "renal_fact_ids": [i for i in [signals["egfr_fact_id"], signals["creatinine_fact_id"]] if i],
        "guideline_monitoring_citation": _guideline_monitoring_citation(ctx),
    }

    conflicts = []
    tools = []
    for med in normalized:
        tools.append({"tool": "normalize_medication_rxnorm", "rxcui": med.get("rxcui"), "resolved": med.get("resolved")})
        cs = contraindication_engine.evaluate(med=med, context=context, fact_ids=[med.get("fact_id")] if med.get("fact_id") else [])
        for c in cs:
            if c.evidence_citations:
                tools.append({"tool": "retrieve_dailymed_label", "medication": c.medication_name})
        conflicts.extend(cs)

    unresolved = [m["original_text"] for m in normalized if not m.get("resolved")]
    label_unavailable = [c.medication_name for c in conflicts if c.conflict_type == "label_unavailable"]
    actionable = [c for c in conflicts if c.severity in ("caution", "high", "blocked")]

    warnings = []
    if unresolved:
        warnings.append(f"unresolved medications: {', '.join(unresolved)}")
    if label_unavailable:
        warnings.append(f"drug-label evidence unavailable for: {', '.join(label_unavailable)}")

    # --- Multimorbidity Medication Safety engine (additive, richer output) ----
    med_safety = build_multimorbidity_output(ctx, pc, signals)

    return make_stage_result(
        ctx=ctx, stage_id=STAGE_MEDICATION_SAFETY, timer=timer,
        status="warning" if (actionable or unresolved) else "completed",
        structured_output={
            "normalized_medications": normalized,
            "conflicts": [c.model_dump() for c in conflicts],  # preserved contract
            "actionable_conflict_count": len(actionable),
            "medication_safety": med_safety.model_dump(),        # rich multimorbidity output
        },
        source_ids=[fid for c in conflicts for fid in c.patient_fact_ids],
        tools_called=tools,
        missing_information=[f"{n} label unavailable" for n in label_unavailable],
        warnings=warnings,
        safety_flags=[f"medication_conflict:{c.severity}" for c in actionable],
        confidence=0.8 if actionable else 0.6,
    )


def build_multimorbidity_output(ctx, pc, signals):
    """Run the deterministic Multimorbidity Medication Safety engine.

    Agent ID: multimorbidity_medication_safety. Reconciles medications and
    morbidities, evaluates cross-condition conflicts, generates evidence-linked
    alternatives, and self-critiques — all deterministic; Claude is optional prose.
    """
    from python.hearttwin.careguard.constants import DISCLAIMER
    from python.hearttwin.careguard.medications import (
        alternative_engine,
        conflict_engine,
        medication_reconciler,
        morbidity_reconciler,
        safety_critic,
    )
    from python.hearttwin.careguard.medications.schemas import (
        ConditionMention,
        MultimorbidityMedicationSafetyOutput,
    )

    guideline_citations = ctx.prior_stage_outputs.get("citations", []) or []
    report_texts = ctx.prior_stage_outputs.get("report_texts", []) or []

    active, proposed, recon_warnings = medication_reconciler.reconcile(pc.medications)
    morbidity = morbidity_reconciler.reconcile(pc, report_texts=report_texts)

    all_meds = active + proposed
    conflicts = conflict_engine.evaluate(proposed_and_active=all_meds, signals=signals)

    # Target the medication carrying the strongest conflict for alternatives.
    ranked = sorted(conflicts, key=lambda c: {"blocked_for_draft": 3, "high_concern": 2, "caution": 1}.get(c.severity, 0), reverse=True)
    target = None
    if ranked:
        target = next((m for m in all_meds if m.medication_id == ranked[0].proposed_medication_id), None)
    alternatives = []
    if target:
        alternatives = alternative_engine.generate(
            target_med=target, signals=signals,
            guideline_citations=guideline_citations,
            indication=ctx.clinical_question or "heart failure therapy review",
        )

    critic = safety_critic.critique(
        conflicts=conflicts, alternatives=alternatives,
        report_mentions_confirmed_as_fact=False,
    )

    hard = [c for c in conflicts if c.severity == "blocked_for_draft"]
    high = [c for c in conflicts if c.severity == "high_concern"]
    if hard:
        overall = "blocked_for_draft"
    elif high:
        overall = "high_concern"
    elif conflicts:
        overall = "review_required"
    else:
        overall = "no_documented_conflict_found"

    return MultimorbidityMedicationSafetyOutput(
        case_id=ctx.case_id, run_id=ctx.run_id,
        proposed_medications=proposed,
        reconciled_active_medications=active,
        confirmed_conditions=morbidity["confirmed_conditions"],
        historical_conditions=morbidity["historical_conditions"],
        report_mentions_requiring_confirmation=[
            ConditionMention.model_validate(m)
            for m in morbidity["report_mentions_requiring_confirmation"]
        ],
        conflicts=conflicts,
        alternative_candidates=alternatives,
        missing_information=sorted({mi for c in conflicts for mi in c.missing_information}),
        clinician_confirmation_requests=[
            f"Confirm report-mentioned condition: {m['normalized_display']}"
            for m in morbidity["report_mentions_requiring_confirmation"]
        ],
        overall_status=overall,
        evidence_coverage_score=round(sum(1 for c in conflicts if c.authoritative_evidence) / max(1, len(conflicts)), 3),
        provenance_coverage_score=pc.provenance_coverage,
        medication_reconciliation_score=medication_reconciler.reconciliation_score(active),
        critic_findings=critic.blocked_reasons,
        safety_disclaimer="Clinical decision support draft. Clinician and pharmacist review required.",
    )
