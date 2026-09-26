#!/usr/bin/env python3
"""Imaging stage 10 — prepare VISTA segmentation jobs (spec §14/§16).

For each vista-eligible imaging case, build a VistaSegmentationJob whose requested
classes are derived from the endpoint capability handshake — NEVER requesting a
class the endpoint does not declare. Jobs are written to staging/imaging/vista-jobs/.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402
from python.hearttwin.careguard.imaging import vista_endpoint_adapter as A  # noqa: E402

# Preferred structures (spec §14). Only those the endpoint declares are requested.
PREFERRED = ["heart", "myocardium", "left atrium", "right atrium", "left ventricle",
             "right ventricle", "aorta", "pulmonary artery", "inferior vena cava",
             "superior vena cava", "lungs", "liver", "kidneys", "spleen", "pancreas",
             "coronary arteries", "epicardial adipose tissue", "pericoronary adipose tissue"]


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_10_prepare_jobs")
    log.info("=== Imaging 10: prepare VISTA jobs ===")

    caps = A.discover_capabilities_sync()
    I.C.write_json(I.STG_VISTA_JOBS / "capabilities.json", caps.model_dump())
    log.info("endpoint reachable=%s supported=%s", caps.reachable, caps.supported_classes)
    accepted, rejected, warns = A.resolve_requested_classes(PREFERRED, caps)
    log.info("accepted classes: %s | rejected: %d", accepted, len(rejected))

    idx_path = I.IMAGING_CASES / "imaging_cases_index.json"
    idx = I.C.read_json(idx_path) if idx_path.exists() else {"cases": []}
    n = 0
    for c in idx.get("cases", []):
        if not c.get("vista_eligible"):
            continue
        icid = c["imaging_case_id"]
        nifti = I.IMAGING_CASES / icid / "imaging" / "normalized" / "ct.nii.gz"
        if not nifti.exists():
            log.warning("%s: no normalized nifti; skip", icid)
            continue
        job = {
            "job_id": f"job-{icid}", "imaging_case_id": icid,
            "source_dataset": c["source_dataset"], "source_subject_id": c["source_subject_id"],
            "input_uri": str(nifti.relative_to(I.C.DATA_DIR)), "input_sha256": I.C.sha256_file(nifti),
            "modality": "CT", "requested_classes": accepted,
            "endpoint_model": caps.service, "endpoint_version": caps.version,
            "created_at": I.C.now_iso(), "linkage_status": c["linkage_status"],
            "deidentified": True, "state": "queued",
            "accepted_classes": accepted, "rejected_classes": rejected,
            "warnings": warns, "capability_source": caps.source, "endpoint_reachable": caps.reachable,
        }
        I.C.write_json(I.STG_VISTA_JOBS / f"{job['job_id']}.json", job)
        n += 1
    log.info("=== Imaging 10 complete: %d jobs prepared (requesting %s) ===", n, accepted)
    print(f"jobs_prepared={n} classes={accepted}")


if __name__ == "__main__":
    main()
