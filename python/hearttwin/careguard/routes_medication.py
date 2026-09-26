"""Multimorbidity Medication Safety routes (attached to the CareGuard router)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from python.hearttwin.careguard import audit
from python.hearttwin.careguard.agents.medication_safety_agent import build_multimorbidity_output
from python.hearttwin.careguard.constants import DISCLAIMER
from python.hearttwin.careguard.errors import RunNotFoundError, SafetyBoundaryError
from python.hearttwin.careguard.medications import medication_reconciler, morbidity_reconciler
from python.hearttwin.careguard.medications.schemas import MedicationReviewRequest
from python.hearttwin.careguard.medications.source_registry import all_source_status
from python.hearttwin.careguard.memory import keys, redis_store
from python.hearttwin.careguard.risk.signals import extract_signals
from python.hearttwin.careguard.schemas import CareGuardContext, PatientContext

_MED_DISCLAIMER = "Clinical decision support draft. Clinician and pharmacist review required."


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _load_pc(case_id: str) -> PatientContext:
    ctx = await redis_store.get_json(keys.case_context(case_id))
    if not ctx:
        raise RunNotFoundError(f"No CareGuard case context for {case_id!r} — import + run first")
    return PatientContext.model_validate(ctx)


async def _build_ctx(case_id: str, clinical_question: str) -> CareGuardContext:
    citations = await redis_store.get_json(keys.case_guidelines(case_id)) or []
    record = await redis_store.get_json(keys.case_record(case_id)) or {}
    from python.hearttwin.careguard.schemas import ClinicalFact
    facts = [ClinicalFact.model_validate(f) for f in record.get("facts", [])]
    return CareGuardContext(
        run_id="med-review", case_id=case_id, clinical_question=clinical_question,
        facts=facts, prior_stage_outputs={"citations": citations},
    )


def attach(router: APIRouter) -> None:
    @router.get("/medication-safety/sources")
    async def sources() -> dict:
        return {"sources": all_source_status(), "safety_disclaimer": _MED_DISCLAIMER}

    @router.get("/medication-safety/source-status")
    async def source_status() -> dict:
        from python.hearttwin.careguard.medications import evidence_policy
        return {
            "sources": all_source_status(),
            "policy": {
                "require_official_label_for_hard_block": evidence_policy.require_official_label_for_hard_block(),
                "require_guideline_for_alternatives": evidence_policy.require_guideline_for_alternatives(),
                "allow_unverified_alternatives": evidence_policy.allow_unverified_alternatives(),
            },
            "safety_disclaimer": _MED_DISCLAIMER,
        }

    @router.post("/cases/{case_id}/medication-reconcile")
    async def medication_reconcile(case_id: str) -> dict:
        pc = await _load_pc(case_id)
        active, proposed, warnings = medication_reconciler.reconcile(pc.medications)
        payload = {"active": [m.model_dump() for m in active],
                   "proposed": [m.model_dump() for m in proposed], "warnings": warnings,
                   "reconciliation_score": medication_reconciler.reconciliation_score(active)}
        await redis_store.set_json(keys.case_medication_reconciliation(case_id), payload)
        await audit.record(case_id=case_id, actor="multimorbidity_medication_safety",
                           action="medication reconciliation", detail={"active": len(active)})
        return {**payload, "safety_disclaimer": _MED_DISCLAIMER}

    @router.post("/cases/{case_id}/morbidity-reconcile")
    async def morbidity_reconcile(case_id: str, body: dict | None = None) -> dict:
        pc = await _load_pc(case_id)
        reports = (body or {}).get("report_texts", [])
        result = morbidity_reconciler.reconcile(pc, report_texts=reports)
        await redis_store.set_json(keys.case_morbidity(case_id), result)
        return {**result, "safety_disclaimer": _MED_DISCLAIMER}

    @router.post("/cases/{case_id}/medication-review")
    async def medication_review(case_id: str, request: MedicationReviewRequest) -> dict:
        pc = await _load_pc(case_id)
        ctx = await _build_ctx(case_id, request.clinical_question)
        if request.proposed_medication:
            ctx.prior_stage_outputs["report_texts"] = []
        signals = extract_signals(pc)
        output = build_multimorbidity_output(ctx, pc, signals)
        await redis_store.set_json(keys.case_medication_safety(case_id), output.model_dump())
        await redis_store.set_json(keys.case_medication_conflicts(case_id),
                                   [c.model_dump() for c in output.conflicts])
        await redis_store.set_json(keys.case_medication_alternatives(case_id),
                                   [a.model_dump() for a in output.alternative_candidates])
        await audit.record(case_id=case_id, actor="multimorbidity_medication_safety",
                           action=f"medication review → {output.overall_status}",
                           detail={"conflicts": len(output.conflicts),
                                   "alternatives": len(output.alternative_candidates)})
        return {"medication_safety": output.model_dump(), "safety_disclaimer": _MED_DISCLAIMER}

    @router.get("/cases/{case_id}/medication-conflicts")
    async def medication_conflicts(case_id: str) -> dict:
        val = await redis_store.get_json(keys.case_medication_conflicts(case_id))
        return {"conflicts": val, "available": val is not None, "safety_disclaimer": _MED_DISCLAIMER}

    @router.get("/cases/{case_id}/medication-alternatives")
    async def medication_alternatives(case_id: str) -> dict:
        val = await redis_store.get_json(keys.case_medication_alternatives(case_id))
        return {"alternatives": val, "available": val is not None, "safety_disclaimer": _MED_DISCLAIMER}

    @router.get("/cases/{case_id}/medication-safety")
    async def medication_safety(case_id: str) -> dict:
        val = await redis_store.get_json(keys.case_medication_safety(case_id))
        return {"medication_safety": val, "available": val is not None, "safety_disclaimer": _MED_DISCLAIMER}

    @router.get("/cases/{case_id}/medication-safety-audit")
    async def medication_safety_audit(case_id: str) -> dict:
        trail = await audit.get_trail(case_id)
        med = [e for e in trail if "medication" in str(e.get("action", "")).lower()
               or e.get("actor") == "multimorbidity_medication_safety"]
        return {"audit": med, "count": len(med), "safety_disclaimer": _MED_DISCLAIMER}

    @router.post("/cases/{case_id}/condition-confirmation")
    async def condition_confirmation(case_id: str, body: dict) -> dict:
        entry = {"mention_id": body.get("mention_id"), "decision": body.get("decision", "confirm"),
                 "reason": body.get("reason", ""), "created_at": _now()}
        await redis_store.append_json(keys.case_feedback(case_id), {"condition_confirmation": entry})
        await audit.record(case_id=case_id, actor="clinician", action="condition confirmation",
                           detail={"decision": entry["decision"]})
        return {"recorded": True, **entry, "safety_disclaimer": _MED_DISCLAIMER}

    @router.post("/cases/{case_id}/medication-confirmation")
    async def medication_confirmation(case_id: str, body: dict) -> dict:
        entry = {"medication_id": body.get("medication_id"), "rxcui": body.get("rxcui"),
                 "decision": body.get("decision", "confirm"), "created_at": _now()}
        await redis_store.append_json(keys.case_feedback(case_id), {"medication_confirmation": entry})
        return {"recorded": True, **entry, "safety_disclaimer": _MED_DISCLAIMER}

    @router.post("/cases/{case_id}/medication-review-feedback")
    async def medication_review_feedback(case_id: str, body: dict) -> dict:
        decision = body.get("decision", "")
        if decision == "override" and not str(body.get("reason", "")).strip():
            raise SafetyBoundaryError("override requires a reason", reason="override_without_reason")
        entry = {"feedback_id": f"mfb-{uuid.uuid4().hex[:8]}", "decision": decision,
                 "candidate_id": body.get("candidate_id"), "reason": body.get("reason", ""),
                 "created_at": _now()}
        await redis_store.append_json(keys.case_feedback(case_id), {"medication_feedback": entry})
        await audit.record(case_id=case_id, actor="clinician", action=f"medication review feedback: {decision}")
        return {"recorded": True, **entry, "safety_disclaimer": _MED_DISCLAIMER}
