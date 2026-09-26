"""Staged-run routes (attached to the CareGuard router)."""

from __future__ import annotations

from fastapi import APIRouter

from python.hearttwin.careguard import orchestrator
from python.hearttwin.careguard.constants import DISCLAIMER
from python.hearttwin.careguard.schemas import CreateRunRequest


def attach(router: APIRouter) -> None:
    @router.post("/runs")
    async def create_run(request: CreateRunRequest) -> dict:
        run = await orchestrator.create_run(
            case_id=request.case_id,
            workflow_intent=request.workflow_intent,
            clinical_question=request.clinical_question,
        )
        return {"run": run.model_dump(), "safety_disclaimer": DISCLAIMER}

    @router.get("/runs/{run_id}")
    async def get_run(run_id: str) -> dict:
        run = await orchestrator.get_run(run_id)
        return {"run": run.model_dump(), "safety_disclaimer": DISCLAIMER}

    @router.post("/runs/{run_id}/next")
    async def advance(run_id: str) -> dict:
        out = await orchestrator.advance_run(run_id)
        out["safety_disclaimer"] = DISCLAIMER
        return out

    @router.post("/runs/{run_id}/cancel")
    async def cancel(run_id: str) -> dict:
        run = await orchestrator.cancel_run(run_id)
        return {"run": run.model_dump(), "safety_disclaimer": DISCLAIMER}
