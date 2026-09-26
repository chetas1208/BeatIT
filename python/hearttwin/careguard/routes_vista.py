"""CareGuard VISTA-3D routes (attached to the CareGuard router).

Optional, external, deidentified imaging. VISTA failure never blocks the rest of
CareGuard; every result is labeled for clinician review.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, File, UploadFile

from python.hearttwin.careguard import audit
from python.hearttwin.careguard.constants import DISCLAIMER
from python.hearttwin.careguard.memory import keys, redis_store
from python.hearttwin.careguard.simulation import vista_adapter


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def attach(router: APIRouter) -> None:
    @router.get("/vista/health")
    async def vista_health() -> dict:
        return {**(await vista_adapter.health()), "safety_disclaimer": DISCLAIMER}

    @router.get("/vista/status")
    async def vista_status() -> dict:
        return {"vista": vista_adapter.status(), "safety_disclaimer": DISCLAIMER}

    @router.post("/cases/{case_id}/vista-segment")
    async def vista_segment(case_id: str, file: UploadFile = File(...)) -> dict:
        content = await file.read()
        result = await vista_adapter.segment(
            file_bytes=content, filename=file.filename or "volume.nii.gz",
        )
        result["case_id"] = case_id
        result["submitted_at"] = _now()
        # Persist the (label-carrying) segmentation record under a case key.
        await redis_store.set_json(f"{keys.case_record(case_id).rsplit(':', 1)[0]}:vista", result)
        await audit.record(case_id=case_id, actor="careguard_vista_adapter",
                           action=f"VISTA segmentation submitted → {result.get('status')}",
                           detail={"filename": file.filename, "status": result.get("status")})
        return {"vista": result, "safety_disclaimer": DISCLAIMER}

    @router.get("/cases/{case_id}/vista")
    async def get_vista(case_id: str) -> dict:
        val = await redis_store.get_json(f"{keys.case_record(case_id).rsplit(':', 1)[0]}:vista")
        return {"vista": val, "available": val is not None, "safety_disclaimer": DISCLAIMER}

    @router.get("/cases/{case_id}/vista/jobs/{job_id}")
    async def get_vista_job(case_id: str, job_id: str) -> dict:
        return {"vista": await vista_adapter.job_result(job_id), "safety_disclaimer": DISCLAIMER}
