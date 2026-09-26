"""Per-case CT + echo modality routes (matched external research modalities).

GET  /cases/{id}/imaging-map        → mapped echo (EF/ESV/EDV) + CT candidate
POST /cases/{id}/imaging/echo-sim   → HeartTwin hemodynamics on the echo volumes
POST /cases/{id}/imaging/ct-segment → VISTA-3D segmentation of the mapped CT
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from python.hearttwin.careguard import audit
from python.hearttwin.careguard.constants import DISCLAIMER
from python.hearttwin.careguard.imaging import modality_map
from python.hearttwin.careguard.memory import keys, redis_store
from python.hearttwin.careguard.schemas import PatientContext
from python.hearttwin.careguard.simulation import hearttwin_adapter, vista_adapter

_EXTERNAL_SIM_LABEL = (
    "Simulated on EchoNet external research echo volumes — NOT this patient's own cardiac "
    "measurements. Physiologic comparison only; clinician review required."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _cardiac_conditions(case_id: str) -> list[str]:
    ctx = await redis_store.get_json(keys.case_context(case_id))
    if not ctx:
        return []
    pc = PatientContext.model_validate(ctx)
    return [str(f.display) for f in (pc.active_cardiac_problem + pc.historical_cardiac_problems)]


async def _hr_bp(case_id: str) -> tuple[float, float, float, bool]:
    """Return (hr, sbp, dbp, from_case). Falls back to population defaults, flagged."""
    ctx = await redis_store.get_json(keys.case_context(case_id))
    hr = sbp = dbp = None
    if ctx:
        for f in ctx.get("observations", []):
            code = f.get("code")
            if code == "8867-4" and isinstance(f.get("value"), (int, float)):
                hr = f["value"]
            elif code == "8480-6" and isinstance(f.get("value"), (int, float)):
                sbp = f["value"]
            elif code == "8462-4" and isinstance(f.get("value"), (int, float)):
                dbp = f["value"]
    from_case = all(x is not None for x in (hr, sbp, dbp))
    return (hr or 72.0, sbp or 120.0, dbp or 80.0, from_case)


def attach(router: APIRouter) -> None:
    @router.get("/cases/{case_id}/imaging-map")
    async def imaging_map(case_id: str) -> dict:
        conditions = await _cardiac_conditions(case_id)
        mp = modality_map.build_imaging_map(case_id, conditions)
        await redis_store.set_json(keys.case_record(case_id).rsplit(":", 1)[0] + ":imaging-map", mp)
        return {"imaging_map": mp, "safety_disclaimer": DISCLAIMER}

    @router.post("/cases/{case_id}/imaging/echo-sim")
    async def echo_sim(case_id: str) -> dict:
        conditions = await _cardiac_conditions(case_id)
        echo = modality_map.map_echo(case_id, conditions)
        if not echo.get("available"):
            return {"ran": False, "reason": echo.get("reason"), "safety_disclaimer": DISCLAIMER}
        dm = echo["derived_measurements"]
        hr, sbp, dbp, from_case = await _hr_bp(case_id)
        inputs = {
            "edv_ml": dm["end_diastolic_volume_ml"], "esv_ml": dm["end_systolic_volume_ml"],
            "heart_rate_bpm": hr, "systolic_bp_mmhg": sbp, "diastolic_bp_mmhg": dbp,
        }
        sim = hearttwin_adapter.run_scenarios(inputs, ["baseline", "afterload_reduction", "preload_optimization"])
        sim["label"] = _EXTERNAL_SIM_LABEL
        sim["echo_source"] = {"dataset": "EchoNet-Dynamic", "record_id": echo["source_record_id"],
                              "ef_pct": dm["ejection_fraction_pct"], "same_subject": False}
        sim["hr_bp_from_case_record"] = from_case
        await redis_store.set_json(keys.case_record(case_id).rsplit(":", 1)[0] + ":echo-sim", sim)
        await audit.record(case_id=case_id, actor="careguard_echo_modality",
                           action=f"echo-derived heartbeat sim (EF {dm['ejection_fraction_pct']}%, external modality)",
                           detail={"record_id": echo["source_record_id"], "same_subject": False})
        return {"echo_simulation": sim, "safety_disclaimer": DISCLAIMER}

    @router.post("/cases/{case_id}/imaging/ct-segment")
    async def ct_segment(case_id: str) -> dict:
        ct = modality_map.map_ct(case_id)
        if not ct.get("vista_eligible"):
            return {"submitted": False, "reason": ct.get("reason"), "ct": ct, "safety_disclaimer": DISCLAIMER}
        try:
            with open(ct["ct_volume_path"], "rb") as fh:
                data = fh.read()
        except OSError as exc:
            return {"submitted": False, "reason": f"cannot read CT volume: {exc}", "safety_disclaimer": DISCLAIMER}
        result = await vista_adapter.segment(
            file_bytes=data, filename="ct.nii.gz",
            target_classes=["heart", "aorta", "left atrium", "left ventricle", "myocardium"],
            file_id=case_id,
        )
        result["ct_source"] = ct
        await redis_store.set_json(keys.case_record(case_id).rsplit(":", 1)[0] + ":ct-segmentation", result)
        await audit.record(case_id=case_id, actor="careguard_vista_adapter",
                           action=f"CT segmentation submitted (external modality) → {result.get('status')}",
                           detail={"same_subject": False})
        return {"ct_segmentation": result, "safety_disclaimer": DISCLAIMER}

    @router.get("/cases/{case_id}/imaging/ct-segment/{job_id}")
    async def ct_segment_result(case_id: str, job_id: str) -> dict:
        return {"ct_segmentation": await vista_adapter.job_result(job_id), "safety_disclaimer": DISCLAIMER}
