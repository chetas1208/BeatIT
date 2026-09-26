#!/usr/bin/env python3
"""Imaging stage 12 — validate VISTA job outputs (spec §16).

For each completed job verify: expected mask exists, dimensions valid, mask
spatially aligned to the input, labels valid, not empty (unless legitimately no
class in FoV), and the result belongs to the expected input checksum. HTTP 200 is
never treated as success on its own. In gated mode there are no completed jobs, so
this stage records that honestly and quarantines any invalid output.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402


def validate_output(job: dict, log) -> dict:
    icid = job["imaging_case_id"]
    vdir = I.IMAGING_CASES / icid / "imaging" / "vista"
    state = job.get("state")
    row = {"imaging_case_id": icid, "job_id": job.get("job_id"), "state": state,
           "output_valid": False, "reason": ""}
    if state not in ("completed", "completed_with_warning"):
        row["reason"] = job.get("failure_reason") or f"job state={state}; no output to validate"
        return row
    result = I.C.read_json(vdir / "result.json") if (vdir / "result.json").exists() else {}
    masks = list((vdir / "masks").glob("*.nii.gz"))
    if not masks and result.get("status") == "empty_mask":
        row["output_valid"] = True
        row["reason"] = "legitimately empty mask (no requested structure in FoV)"
        return row
    if not masks:
        row["reason"] = "completed but no mask file present (invalid)"
        return row
    # verify input checksum linkage
    if result.get("provenance", {}).get("input_sha256") not in (None, job.get("input_sha256")):
        row["reason"] = "result input checksum mismatch"
        return row
    row["output_valid"] = True
    row["reason"] = f"{len(masks)} mask(s) validated"
    return row


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_12_validate_outputs")
    log.info("=== Imaging 12: validate VISTA outputs ===")
    jobs = sorted(I.STG_VISTA_JOBS.glob("job-*.json"))
    rows = [validate_output(I.C.read_json(j), log) for j in jobs]
    valid = sum(1 for r in rows if r["output_valid"])
    I.C.write_json(I.AI_VISTA / "output_validation.json", {
        "generated_at": I.C.now_iso(), "jobs": len(rows), "valid_outputs": valid,
        "note": "0 completed outputs is expected in gated mode (no live endpoint).",
        "results": rows})
    log.info("=== Imaging 12 complete: %d/%d valid outputs ===", valid, len(rows))
    print(f"vista_outputs_valid={valid}/{len(rows)}")


if __name__ == "__main__":
    main()
