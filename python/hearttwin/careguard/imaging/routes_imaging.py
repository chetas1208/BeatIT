"""CareGuard imaging + VISTA routes (additive; spec §24).

Attached alongside the existing CareGuard routes. Read-only over the imaging
artifacts under data/, plus a fusion endpoint that ENFORCES verified same-subject
linkage — returning HTTP 409 for any non-verified case. Nothing here mutates the
baseline pipeline; import errors degrade to a no-op (like the other routers).
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from python.hearttwin.careguard.constants import DISCLAIMER
from python.hearttwin.careguard.imaging import linkage as L

_REPO = Path(__file__).resolve().parents[4]
_DATA = _REPO / "data"
VISTA_LABEL = "Model-derived research segmentation requiring clinician review."


def _load(rel: str, default):
    p = _DATA / rel
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def attach(router: APIRouter) -> None:
    @router.get("/imaging/sources")
    async def imaging_sources() -> dict:
        return {**_load("imaging_source_manifest.json", {"sources": []}),
                "safety_disclaimer": DISCLAIMER}

    @router.get("/imaging/source-status")
    async def imaging_source_status() -> dict:
        man = _load("imaging_source_manifest.json", {"sources": []})
        return {"sources": [{"source_id": s["source_id"], "access_state": s.get("access_state"),
                             "can_ingest": s.get("can_ingest"), "license": s.get("license")}
                            for s in man.get("sources", [])]}

    @router.get("/imaging/vista/capabilities")
    async def vista_capabilities() -> dict:
        from python.hearttwin.careguard.imaging import vista_endpoint_adapter as A
        caps = await A.discover_capabilities()
        return {**caps.model_dump(), "safety_disclaimer": DISCLAIMER}

    @router.get("/imaging/vista/health")
    async def vista_health() -> dict:
        from python.hearttwin.tools import vista3d_client as VC
        healthy, warnings = await VC.health_check()
        return {"healthy": healthy, "configured": VC.is_configured(),
                "warnings": warnings, "safety_disclaimer": DISCLAIMER}

    @router.post("/imaging/import")
    async def imaging_import() -> dict:
        # Gated: ingestion status is derived from recorded access; never bypasses controls.
        return {"status": "gated", "message": "Imaging ingestion is driven by scripts/imaging/*; "
                "controlled sources remain access_pending until DUA/license are recorded.",
                "sources": _load("imaging_source_manifest.json", {"sources": []}).get("sources", [])}

    @router.get("/imaging/{imaging_case_id}/vista")
    async def imaging_vista(imaging_case_id: str) -> dict:
        job = _load(f"imaging-cases/{imaging_case_id}/imaging/vista/job.json", None)
        if job is None:
            return {"imaging_case_id": imaging_case_id, "status": "no_job",
                    "safety_disclaimer": DISCLAIMER}
        return {"imaging_case_id": imaging_case_id, "state": job.get("state"),
                "failure_reason": job.get("failure_reason"),
                "requested_classes": job.get("requested_classes"),
                "label": VISTA_LABEL, "safety_disclaimer": DISCLAIMER}

    @router.get("/imaging/{imaging_case_id}/vista/masks")
    async def imaging_vista_masks(imaging_case_id: str) -> dict:
        mdir = _DATA / "imaging-cases" / imaging_case_id / "imaging" / "vista" / "masks"
        masks = [p.name for p in mdir.glob("*.nii.gz")] if mdir.exists() else []
        return {"imaging_case_id": imaging_case_id, "masks": masks, "label": VISTA_LABEL}

    @router.get("/imaging/{imaging_case_id}/metrics")
    async def imaging_metrics(imaging_case_id: str) -> dict:
        allm = _load("vista-benchmark/metrics/segmentation_metrics.json", {"rows": []})
        rows = [r for r in allm.get("rows", []) if r["imaging_case_id"] == imaging_case_id]
        return {"imaging_case_id": imaging_case_id, "metrics": rows,
                "label_map": allm.get("label_map", [])}

    @router.get("/cases/{case_id}/imaging")
    async def case_imaging(case_id: str) -> dict:
        man = _load(f"cases/{case_id}/manifest.json", {})
        return {"case_id": case_id, "ct_imaging": man.get("ct_imaging",
                {"status": L.NO_LINKED_CT}), "safety_disclaimer": DISCLAIMER}

    @router.post("/cases/{case_id}/imaging/fuse")
    async def case_imaging_fuse(case_id: str) -> JSONResponse:
        man = _load(f"cases/{case_id}/manifest.json", {})
        ct = man.get("ct_imaging", {"status": L.NO_LINKED_CT})
        allowed, msg = L.assert_fusion_permitted(ct)
        if not allowed:
            return JSONResponse(status_code=409, content={
                "error": "imaging_linkage_not_verified",
                "message": "This CT cannot be fused with the clinical case because "
                           "same-subject linkage has not been verified.",
                "linkage_status": ct.get("status")})
        return JSONResponse(status_code=200, content={
            "case_id": case_id, "fused": True, "linkage_status": ct.get("status"),
            "assertion_type": "model_derived_imaging_measurement", "label": VISTA_LABEL})
