#!/usr/bin/env python3
"""Stage 08 — build one FHIR R4 Bundle per case and structurally validate it.

Bundles are written to staging/fhir/<case_id>.json (copied into case dirs by 09).
Reads medication normalization (stage 07) and ECG assignments (stage 06) if
present; both are optional (a case can be packaged without labels or ECG).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import fhir_build as FB  # noqa: E402

ASM = C.STAGING / "assembled"
FHIR_OUT = C.STAGING / "fhir"


def load_meds():
    p = C.STAGING / "medication-normalization" / "normalized.json"
    return C.read_json(p) if p.exists() else {}


def _load_assignments(name):
    import pandas as pd
    p = C.COHORT / name
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    out = {}
    for _, r in df.iterrows():
        d = {k: (None if pd.isna(r[k]) else r[k]) for k in df.columns}
        d["assigned"] = bool(d.get("assigned"))
        out[r["case_id"]] = d
    return out


def load_ecg():
    return _load_assignments("ecg_assignments.csv")


def load_echo():
    return _load_assignments("echo_assignments.csv")


def main() -> None:
    import pandas as pd
    C.ensure_dirs()
    FHIR_OUT.mkdir(parents=True, exist_ok=True)
    log = C.get_logger("08_build_fhir")
    cfg = C.load_config()
    log.info("=== Stage 08: build FHIR R4 bundles ===")

    sel = pd.read_csv(C.STAGING / "eicu" / "cohort_selection.csv")
    for a in sys.argv:
        if a.startswith("--limit="):
            sel = sel.head(int(a.split("=", 1)[1]))
    meds = load_meds()
    ecg = load_ecg()
    echo = load_echo()
    log.info("cases=%d normalized_meds=%d ecg=%d echo=%d", len(sel), len(meds),
             sum(1 for v in ecg.values() if v.get("assigned")),
             sum(1 for v in echo.values() if v.get("assigned")))

    rows = []
    valid_n = 0
    for _, crow in sel.iterrows():
        cid = crow["case_id"]
        asm = C.read_json(ASM / f"{cid}.json")
        b = FB.Builder(asm, meds, ecg.get(cid, {}), cfg, echo_assignment=echo.get(cid, {}))
        bundle = b.build()
        ok, issues = FB.validate_bundle_struct(bundle)
        C.write_json(FHIR_OUT / f"{cid}.json", bundle)
        rt_counts = {}
        for e in bundle["entry"]:
            rt = e["resource"]["resourceType"]
            rt_counts[rt] = rt_counts.get(rt, 0) + 1
        C.write_json(FHIR_OUT / f"{cid}.meta.json", {
            "case_id": cid, "resource_counts": rt_counts,
            "total_resources": len(bundle["entry"]),
            "dropped_conditions": b.dropped_conditions, "dropped_meds": b.dropped_meds,
            "valid": ok, "issues": issues, "has_ecg": ecg.get(cid, {}).get("assigned", False)})
        rows.append({"case_id": cid, "total_resources": len(bundle["entry"]),
                     "conditions": rt_counts.get("Condition", 0),
                     "observations": rt_counts.get("Observation", 0),
                     "medications": rt_counts.get("MedicationStatement", 0),
                     "allergies": rt_counts.get("AllergyIntolerance", 0),
                     "procedures": rt_counts.get("Procedure", 0),
                     "has_ecg_report": rt_counts.get("DiagnosticReport", 0) > 0,
                     "valid": ok, "n_issues": len(issues),
                     "issues": ";".join(issues[:5])})
        valid_n += int(ok)
        if len(rows) % 200 == 0:
            log.info("built %d bundles (%d valid)", len(rows), valid_n)

    with open(C.ANALYSIS / "fhir_validation_report.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    C.write_json(FHIR_OUT / "build_summary.json", {
        "generated_at": C.now_iso(), "cases": len(rows), "valid": valid_n,
        "invalid": len(rows) - valid_n})
    log.info("=== Stage 08 complete: %d/%d structurally valid ===", valid_n, len(rows))
    print(f"fhir_valid={valid_n}/{len(rows)}")


if __name__ == "__main__":
    main()
