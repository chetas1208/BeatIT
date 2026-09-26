"""CareGuard case-browser routes (additive; spec: select a case and demo it).

Read-only over the packaged cases under data/. Lists all cases, serves one case's
composite demo payload (EHR summary + ECG + echo + CT linkage + quality), and
streams case assets (ECG PNG, echo GIF/frame) for the frontend. Import errors
degrade to a no-op like the other routers.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from python.hearttwin.careguard.constants import DISCLAIMER

_REPO = Path(__file__).resolve().parents[4]
_DATA = _REPO / "data"
_CASES = _DATA / "cases"

# Whitelisted, safe-to-serve per-case assets (path traversal blocked).
_ASSETS = {
    "ecg.png": ("ecg/ecg.png", "image/png"),
    "echo.gif": ("echo/echo.gif", "image/gif"),
    "echo-frame.png": ("echo/echo-frame.png", "image/png"),
}


def _load(rel: str, default):
    p = _DATA / rel
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def attach(router: APIRouter) -> None:
    @router.get("/cases")
    async def list_cases() -> dict:
        rows = _load("cohort/cohort_manifest.json", [])
        compact = [{
            "case_id": r.get("case_id"), "age": r.get("age"), "gender": r.get("gender"),
            "icu_type": r.get("icu_type"), "cv_categories": r.get("cv_categories"),
            "n_noncardiac_organs": r.get("n_noncardiac_organs"),
            "ecg_assigned": r.get("ecg_assigned"), "ecg_superclass": r.get("ecg_superclass"),
            "overall_completeness_score": r.get("overall_completeness_score"),
        } for r in rows]
        return {"count": len(compact), "cases": compact, "safety_disclaimer": DISCLAIMER}

    @router.get("/cases/{case_id}/demo")
    async def case_demo(case_id: str) -> JSONResponse:
        if not (_CASES / case_id).is_dir() or "/" in case_id or ".." in case_id:
            return JSONResponse(status_code=404, content={"error": "case_not_found"})
        summary = _load(f"cases/{case_id}/clinical/patient-summary.json", {})
        manifest = _load(f"cases/{case_id}/manifest.json", {})
        quality = _load(f"cases/{case_id}/quality.json", {})
        echo = _load(f"cases/{case_id}/echo/echo.json", None)
        ecg_prov = _load(f"cases/{case_id}/ecg/ecg-provenance.json", None)
        assets = {k: f"/cases/{case_id}/asset/{k}"
                  for k, (rel, _) in _ASSETS.items() if (_CASES / case_id / rel).exists()}
        return JSONResponse(content={
            "case_id": case_id,
            "summary": summary,
            "ct_imaging": manifest.get("ct_imaging"),
            "modalities": {
                "ecg": {"source": manifest.get("ecg_source"),
                        "same_patient_as_ehr": False,
                        "warning": (ecg_prov or {}).get("warning")},
                "echo": {"source": manifest.get("echo_source"),
                         "same_patient_as_ehr": False,
                         "donor_ejection_fraction_pct": manifest.get("echo_donor_ejection_fraction_pct"),
                         "warning": manifest.get("echo_warning"),
                         "note": (echo or {}).get("donor_measurements", {}).get("note")},
            },
            "quality": {"overall_completeness_score": quality.get("overall_completeness_score"),
                        "warnings": quality.get("missingness_warnings", [])},
            "assets": assets,
            "safety_disclaimer": DISCLAIMER,
            "composite_notice": "Composite research case assembled from deidentified open datasets "
                                "for software testing. ECG and echo are matched external modalities "
                                "from different individuals than the eICU record.",
        })

    @router.get("/cases/{case_id}/bundle")
    async def case_bundle(case_id: str) -> JSONResponse:
        # Serve a packaged case's FHIR R4 bundle so the runner can import + analyze it.
        if "/" in case_id or ".." in case_id:
            return JSONResponse(status_code=404, content={"error": "case_not_found"})
        bundle = _load(f"cases/{case_id}/clinical/fhir-bundle.json", None)
        if bundle is None:
            return JSONResponse(status_code=404, content={"error": "bundle_not_found"})
        return JSONResponse(content=bundle)

    @router.get("/cases/{case_id}/asset/{name}")
    async def case_asset(case_id: str, name: str):
        if name not in _ASSETS or "/" in case_id or ".." in case_id:
            return JSONResponse(status_code=404, content={"error": "asset_not_found"})
        rel, media = _ASSETS[name]
        p = _CASES / case_id / rel
        if not p.exists():
            return JSONResponse(status_code=404, content={"error": "asset_not_found"})
        return FileResponse(str(p), media_type=media)
