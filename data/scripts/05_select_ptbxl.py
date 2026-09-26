#!/usr/bin/env python3
"""Stage 05 — build a PTB-XL feature index for transparent ECG matching.

For each PTB-XL record compute non-identifying broad features: age band, sex,
diagnostic superclass(es), rhythm label, and a broad cardiac bucket. This index
is later used (stage 06) to match ONE external ECG per case. No patient linkage
is implied — matching is on broad features only.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

OUT = C.STAGING / "ptb-xl"
SUPERCLASSES = ["NORM", "MI", "STTC", "CD", "HYP"]


def age_band(a):
    try:
        a = float(a)
    except (TypeError, ValueError):
        return "unknown"
    if a > 89:
        return "90+"
    for hi, label in [(30, "18-29"), (40, "30-39"), (50, "40-49"), (60, "50-59"),
                      (70, "60-69"), (80, "70-79"), (90, "80-89")]:
        if a < hi:
            return label
    return "90+"


def main() -> None:
    import pandas as pd
    C.ensure_dirs()
    OUT.mkdir(parents=True, exist_ok=True)
    log = C.get_logger("05_select_ptbxl")
    log.info("=== Stage 05: index PTB-XL ===")

    db = pd.read_csv(C.RAW_PTBXL / "ptbxl_database.csv")
    scp = pd.read_csv(C.RAW_PTBXL / "scp_statements.csv", index_col=0)
    diag_class = scp["diagnostic_class"].to_dict()
    is_rhythm = set(scp.index[scp["rhythm"] == 1.0]) if "rhythm" in scp.columns else set()
    log.info("PTB-XL records=%d scp_statements=%d", len(db), len(scp))

    rows = []
    for _, r in db.iterrows():
        try:
            codes = ast.literal_eval(r["scp_codes"]) if isinstance(r["scp_codes"], str) else {}
        except (ValueError, SyntaxError):
            codes = {}
        supers = sorted({diag_class.get(c) for c in codes if diag_class.get(c) in SUPERCLASSES})
        rhythms = sorted({c for c in codes if c in is_rhythm})
        # broad cardiac bucket used to match EHR cardiovascular context
        if "MI" in supers:
            bucket = "MI"
        elif "CD" in supers or any(x in rhythms for x in ("AFIB", "AFLT", "SVTAC", "PSVT")):
            bucket = "conduction_rhythm"
        elif "HYP" in supers:
            bucket = "hypertrophy"
        elif "STTC" in supers:
            bucket = "ischemia_sttc"
        elif "NORM" in supers and not supers[1:]:
            bucket = "normal"
        else:
            bucket = "other"
        sex = "male" if r.get("sex") == 0 else "female" if r.get("sex") == 1 else "unknown"
        rows.append({
            "ecg_id": int(r["ecg_id"]),
            "age_band": age_band(r.get("age")),
            "sex": sex,
            "superclasses": ",".join(supers) or "NONE",
            "primary_superclass": supers[0] if supers else "NONE",
            "rhythm": ",".join(rhythms) or "",
            "broad_bucket": bucket,
            "filename_lr": r["filename_lr"],
            "report": (str(r.get("report")) or "")[:200],
            "validated_by_human": bool(r.get("validated_by_human")),
        })

    idx = pd.DataFrame(rows)
    idx.to_parquet(OUT / "ptbxl_index.parquet", index=False)
    idx.to_csv(OUT / "ptbxl_index.csv", index=False)

    dist = idx["primary_superclass"].value_counts().to_dict()
    bucket_dist = idx["broad_bucket"].value_counts().to_dict()
    C.write_json(OUT / "ptbxl_index_summary.json", {
        "generated_at": C.now_iso(), "total": int(len(idx)),
        "superclass_distribution": {k: int(v) for k, v in dist.items()},
        "bucket_distribution": {k: int(v) for k, v in bucket_dist.items()},
    })
    log.info("=== Stage 05 complete: indexed %d ECGs; buckets=%s ===", len(idx), bucket_dist)


if __name__ == "__main__":
    main()
