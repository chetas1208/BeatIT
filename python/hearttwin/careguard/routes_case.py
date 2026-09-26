"""Per-case getter routes + clinician feedback + evidence export."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from python.hearttwin.careguard import audit
from python.hearttwin.careguard.constants import CLINICIAN_REVIEW_LABEL, DISCLAIMER
from python.hearttwin.careguard.errors import RunNotFoundError
from python.hearttwin.careguard.memory import keys, redis_store
from python.hearttwin.careguard.schemas import FeedbackRequest


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def attach(router: APIRouter) -> None:
    async def _get(case_key: str, label: str):
        val = await redis_store.get_json(case_key)
        return {label: val, "available": val is not None, "safety_disclaimer": DISCLAIMER}

    @router.get("/cases/{case_id}/context")
    async def context(case_id: str) -> dict:
        return await _get(keys.case_context(case_id), "patient_context")

    @router.get("/cases/{case_id}/evidence")
    async def evidence(case_id: str) -> dict:
        return await _get(keys.case_guidelines(case_id), "citations")

    @router.get("/cases/{case_id}/contraindications")
    async def contraindications(case_id: str) -> dict:
        return await _get(keys.case_contraindications(case_id), "conflicts")

    @router.get("/cases/{case_id}/candidates")
    async def candidates(case_id: str) -> dict:
        return await _get(keys.case_candidates(case_id), "candidates")

    @router.get("/cases/{case_id}/simulation")
    async def simulation(case_id: str) -> dict:
        return await _get(keys.case_simulation(case_id), "simulation")

    @router.get("/cases/{case_id}/critic")
    async def critic(case_id: str) -> dict:
        return await _get(keys.case_critic(case_id), "critic")

    @router.get("/cases/{case_id}/audit")
    async def audit_trail(case_id: str) -> dict:
        trail = await audit.get_trail(case_id)
        return {"audit": trail, "count": len(trail), "safety_disclaimer": DISCLAIMER}

    @router.post("/cases/{case_id}/feedback")
    async def feedback(case_id: str, request: FeedbackRequest) -> dict:
        if request.decision == "override" and not request.reason.strip():
            from python.hearttwin.careguard.errors import SafetyBoundaryError

            raise SafetyBoundaryError("override requires a reason", reason="override_without_reason")
        entry = {
            "feedback_id": f"fb-{uuid.uuid4().hex[:10]}",
            "decision": request.decision,
            "candidate_id": request.candidate_id,
            "reason": request.reason,
            "reviewer_role": request.reviewer_role,
            "created_at": _now(),
        }
        await redis_store.append_json(keys.case_feedback(case_id), entry)
        try:
            from python.hearttwin.careguard.db.repository import get_repository

            await get_repository().save_feedback(case_id, {**entry, "reviewer_role": request.reviewer_role})
        except Exception:  # noqa: BLE001
            pass
        aid = await audit.record(case_id=case_id, actor=f"clinician:{request.reviewer_role}",
                                 action=f"decision {request.decision}",
                                 detail={"candidate_id": request.candidate_id})
        return {"recorded": True, "feedback_id": entry["feedback_id"], "audit_event_id": aid,
                "clinician_review_label": CLINICIAN_REVIEW_LABEL, "safety_disclaimer": DISCLAIMER}

    @router.post("/cases/{case_id}/export")
    async def export(case_id: str) -> dict:
        record = await redis_store.get_json(keys.case_record(case_id))
        if not record:
            raise RunNotFoundError(f"No CareGuard case {case_id!r}")
        bundle = {
            "case_id": case_id,
            "exported_at": _now(),
            "clinician_review_label": CLINICIAN_REVIEW_LABEL,
            "patient_context": await redis_store.get_json(keys.case_context(case_id)),
            "evidence": await redis_store.get_json(keys.case_guidelines(case_id)),
            "contraindications": await redis_store.get_json(keys.case_contraindications(case_id)),
            "candidates": await redis_store.get_json(keys.case_candidates(case_id)),
            "simulation": await redis_store.get_json(keys.case_simulation(case_id)),
            "critic": await redis_store.get_json(keys.case_critic(case_id)),
            "audit": await audit.get_trail(case_id),
        }
        await audit.record(case_id=case_id, actor="clinician", action="exported evidence review")
        return {"export": bundle, "safety_disclaimer": DISCLAIMER}
