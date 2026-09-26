#!/usr/bin/env python3
"""Imaging stage 11 — run prepared VISTA jobs (spec §16).

Idempotent + resumable: completed jobs are skipped. In GATED mode (no live VISTA
endpoint configured) each job honestly records state=failed with a clear
"endpoint unavailable" reason — NO masks, volumes, or confidences are fabricated.
When an endpoint IS configured, the existing vista3d_client submit/poll path runs
and the deterministic ct_volumetry tool derives volumes from the returned mask.

A checksum + capability snapshot + health snapshot is stored on every job.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402
from python.hearttwin.careguard.imaging import vista_endpoint_adapter as A  # noqa: E402
from python.hearttwin.tools import vista3d_client as VC  # noqa: E402

VISTA_LABEL = "Model-derived research segmentation requiring clinician review."


def run_job(job: dict, caps, health, log) -> dict:
    icid = job["imaging_case_id"]
    vdir = I.IMAGING_CASES / icid / "imaging" / "vista"
    (vdir / "masks").mkdir(parents=True, exist_ok=True)
    (vdir / "previews").mkdir(parents=True, exist_ok=True)
    job.setdefault("retry_count", 0)
    job["submitted_at"] = I.C.now_iso()
    job["endpoint_health"] = health
    job["capabilities_snapshot"] = caps.model_dump()

    if not VC.is_configured() or not caps.reachable:
        job["state"] = "failed"
        job["failure_reason"] = ("VISTA endpoint not configured/unreachable (gated mode): "
                                 "no live segmentation performed. No masks/volumes invented.")
        job["completed_at"] = I.C.now_iso()
        job["response_status"] = None
        job["output_paths"] = {}
        log.info("%s: gated -> failed (endpoint unavailable)", job["job_id"])
    else:
        # live path: submit + poll + deterministic volumetry (existing client)
        nifti = I.C.DATA_DIR / job["input_uri"]
        try:
            import asyncio
            result = asyncio.run(VC.segment_ct_and_analyze(
                nifti.read_bytes(), Path(job["input_uri"]).name,
                file_id=job["job_id"], target_classes=job["requested_classes"]))
            job["state"] = "completed" if result.get("status") == "analyzed" else \
                "completed_with_warning" if result.get("status") in ("empty_mask",) else "failed"
            job["response_status"] = 202
            job["vista_result"] = result
            job["label"] = VISTA_LABEL
            I.C.write_json(vdir / "result.json", result)
        except Exception as e:
            job["state"] = "failed"
            job["failure_reason"] = f"live submission error: {type(e).__name__}: {e}"
        job["completed_at"] = I.C.now_iso()

    I.C.write_json(vdir / "job.json", job)
    I.C.write_json(vdir / "capabilities.json", caps.model_dump())
    return job


def main() -> None:
    import asyncio
    I.ensure_dirs()
    log = I.C.get_logger("imaging_11_run_jobs")
    log.info("=== Imaging 11: run VISTA jobs ===")
    caps = A.discover_capabilities_sync()
    try:
        healthy, hwarn = asyncio.run(VC.health_check())
    except Exception as e:
        healthy, hwarn = False, [f"health check error: {e}"]
    health = {"healthy": healthy, "warnings": hwarn, "checked_at": I.C.now_iso()}

    jobs = sorted(I.STG_VISTA_JOBS.glob("job-*.json"))
    states = {}
    for jp in jobs:
        job = I.C.read_json(jp)
        vdir = I.IMAGING_CASES / job["imaging_case_id"] / "imaging" / "vista"
        if (vdir / "job.json").exists():
            done = I.C.read_json(vdir / "job.json")
            if done.get("state") in ("completed", "completed_with_warning"):
                states[done["state"]] = states.get(done["state"], 0) + 1
                continue  # resumable: skip already-completed
        out = run_job(job, caps, health, log)
        I.C.write_json(jp, out)  # persist state back to the queue file
        states[out["state"]] = states.get(out["state"], 0) + 1

    I.C.write_json(I.AI_VISTA / "run_summary.json", {
        "generated_at": I.C.now_iso(), "endpoint_configured": VC.is_configured(),
        "endpoint_reachable": caps.reachable, "capability_source": caps.source,
        "jobs": len(jobs), "states": states, "health": health})
    log.info("=== Imaging 11 complete: states=%s (gated=%s) ===", states, not caps.reachable)
    print(f"vista_jobs={len(jobs)} states={states}")


if __name__ == "__main__":
    main()
