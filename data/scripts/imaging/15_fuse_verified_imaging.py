#!/usr/bin/env python3
"""Imaging stage 15 — fuse verified imaging into clinical cases (spec §20).

Fusion is permitted ONLY for same_subject_verified / imaging_native_same_subject.
Everything else (imaging_only, no_linked_ct, access_pending, prohibited, invalid)
is blocked. This stage also runs an explicit adversarial demonstration: it ATTEMPTS
a demographic/phenotype "match" and confirms the gate rejects it as prohibited.

Every fused imaging fact would carry assertion_type=model_derived_imaging_measurement
and full scan/model/mask provenance — never a recorded clinical diagnosis.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402
from python.hearttwin.careguard.imaging import linkage as L  # noqa: E402


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_15_fuse")
    log.info("=== Imaging 15: verified imaging fusion (gate) ===")

    idx_path = I.IMAGING_CASES / "imaging_cases_index.json"
    idx = I.C.read_json(idx_path) if idx_path.exists() else {"cases": []}

    fused, blocked = [], []
    for c in idx.get("cases", []):
        status = c["linkage_status"]
        allowed, msg = L.assert_fusion_permitted({"status": status})
        record = {"imaging_case_id": c["imaging_case_id"], "linkage_status": status,
                  "fusion_allowed": allowed, "message": msg}
        if allowed:
            # would attach model_derived_imaging_measurement facts w/ full provenance
            job = I.C.read_json(I.IMAGING_CASES / c["imaging_case_id"] / "imaging" / "vista" / "job.json") \
                if (I.IMAGING_CASES / c["imaging_case_id"] / "imaging" / "vista" / "job.json").exists() else {}
            record["assertion_type"] = "model_derived_imaging_measurement"
            record["vista_job_id"] = job.get("job_id")
            fused.append(record)
        else:
            blocked.append(record)
            log.info("BLOCKED fusion %s: %s", c["imaging_case_id"], status)

    # adversarial demonstration: a demographic "match" must be rejected as prohibited
    demo = L.evaluate_linkage(method="same_age", source_dataset="totalsegmentator",
                              source_subject_id="ts_example_full",
                              linked_clinical_subject_id="case-000001")
    demo_block = {"attempt": "demographic (same_age) match of a TotalSegmentator scan "
                  "to eICU case-000001", "resulting_status": demo.status,
                  "fusion_allowed": L.is_fusion_allowed(demo.status), "reason": demo.reason}
    log.info("adversarial demographic match -> %s (fusion_allowed=%s)",
             demo.status, demo_block["fusion_allowed"])

    I.C.write_json(I.AI_FUSION / "fusion_report.json", {
        "generated_at": I.C.now_iso(),
        "verified_fusions": len(fused), "blocked_fusions": len(blocked),
        "fusion_allowed_statuses": list(L.FUSION_ALLOWED_STATUSES),
        "fused": fused, "blocked": blocked,
        "adversarial_prohibited_demo": demo_block,
        "note": "0 verified fusions is expected: MultiD4CAD (same-subject linked) is "
                "access_pending, and TotalSegmentator cases are imaging_only."})
    log.info("=== Imaging 15 complete: fused=%d blocked=%d prohibited_demo=%s ===",
             len(fused), len(blocked), demo.status)
    print(f"fused={len(fused)} blocked={len(blocked)} demo={demo.status}")


if __name__ == "__main__":
    main()
