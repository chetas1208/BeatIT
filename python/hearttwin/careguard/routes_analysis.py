"""Care-evaluation harness + Copilot analysis routes (attached to the router)."""

from __future__ import annotations

from fastapi import APIRouter

from python.hearttwin.careguard import audit
from python.hearttwin.careguard.agents import care_evaluation_agent
from python.hearttwin.careguard.constants import DISCLAIMER
from python.hearttwin.careguard.copilot_agent import answer as copilot_answer
from python.hearttwin.careguard.memory import keys, redis_store


async def _artifacts(case_id: str) -> dict:
    async def g(k):
        return await redis_store.get_json(k)
    return {
        "patient_context": await g(keys.case_context(case_id)),
        "citations": await g(keys.case_guidelines(case_id)),
        "conflicts": await g(keys.case_contraindications(case_id)),
        "candidates": await g(keys.case_candidates(case_id)),
        "cross_organ_matrix": await g(keys.case_multimorbidity(case_id)),
        "critic": await g(keys.case_critic(case_id)),
        "medication_safety": await g(keys.case_medication_safety(case_id)),
    }


def attach(router: APIRouter) -> None:
    @router.post("/cases/{case_id}/care-evaluation")
    async def care_evaluation(case_id: str, body: dict) -> dict:
        artifacts = await _artifacts(case_id)
        ev = care_evaluation_agent.evaluate_process(
            case_id=case_id, artifacts=artifacts,
            doctor_report=str(body.get("doctor_report", "")),
            patient_progress=str(body.get("patient_progress", "")),
        )
        if body.get("use_anthropic", True):
            ev = await care_evaluation_agent.enrich_narrative_with_anthropic(ev)
        await redis_store.set_json(keys.case_critic(case_id).rsplit(":", 1)[0] + ":care-evaluation", ev.model_dump())
        await audit.record(case_id=case_id, actor="careguard_care_evaluation_agent",
                           action=f"care-process evaluation (overall {ev.overall_process_quality})",
                           detail={"model_used": ev.model_used})
        return {"care_evaluation": ev.model_dump(), "safety_disclaimer": DISCLAIMER}

    @router.get("/cases/{case_id}/care-evaluation")
    async def get_care_evaluation(case_id: str) -> dict:
        val = await redis_store.get_json(keys.case_critic(case_id).rsplit(":", 1)[0] + ":care-evaluation")
        return {"care_evaluation": val, "available": val is not None, "safety_disclaimer": DISCLAIMER}

    @router.post("/cases/{case_id}/copilot")
    async def copilot(case_id: str, body: dict) -> dict:
        ans = await copilot_answer(case_id, str(body.get("question", "")))
        await audit.record(case_id=case_id, actor="careguard_copilot",
                           action="copilot analysis question", detail={"used_anthropic": ans.used_anthropic})
        return {"copilot": ans.model_dump(), "safety_disclaimer": DISCLAIMER}
