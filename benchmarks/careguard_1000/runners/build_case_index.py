#!/usr/bin/env python3
"""Build a validated index of every case under data/cases/.

Emits results/case_index.parquet and results/case_index.csv with the fields
required by the spec (§4). Cases are classified into eligibility statuses and
NONE are silently dropped — ineligible cases are recorded with a reason.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _bench_common import CASES_DIR, RESULTS_DIR  # noqa: E402

STATUS_ELIGIBLE = "eligible"
STATUS_WARN = "eligible_with_warning"
STATUS_CORRUPT = "ineligible_corrupt"
STATUS_MISSING = "ineligible_missing_core_files"
STATUS_PROV = "ineligible_provenance_failure"


def _load_json(path: Path):
    return json.loads(path.read_text())


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with path.open() as f:
        for i, _ in enumerate(f):
            n = i  # last index; header is line 0
    return max(n, 0)


def index_one(case_dir: Path) -> dict:
    cid = case_dir.name
    row: dict = {
        "case_id": cid,
        "status": STATUS_ELIGIBLE,
        "status_reason": "",
        "warnings": [],
    }

    man_p = case_dir / "manifest.json"
    qual_p = case_dir / "quality.json"
    prov_p = case_dir / "provenance.json"
    psum_p = case_dir / "clinical" / "patient-summary.json"
    fhir_p = case_dir / "clinical" / "fhir-bundle.json"
    meds_p = case_dir / "ehr" / "medications.csv"
    medev_p = case_dir / "medication-evidence" / "label-evidence.json"
    normed_p = case_dir / "medication-evidence" / "normalized-medications.json"

    # --- Parse core JSON, catch corruption ---
    manifest = summary = quality = provenance = None
    try:
        if man_p.exists():
            manifest = _load_json(man_p)
        if qual_p.exists():
            quality = _load_json(qual_p)
        if psum_p.exists():
            summary = _load_json(psum_p)
        if prov_p.exists():
            provenance = _load_json(prov_p)
    except (json.JSONDecodeError, ValueError) as exc:
        row["status"] = STATUS_CORRUPT
        row["status_reason"] = f"json parse error: {exc}"
        return row

    # --- Core-file presence ---
    missing_core = []
    if manifest is None:
        missing_core.append("manifest.json")
    if not fhir_p.exists():
        missing_core.append("clinical/fhir-bundle.json")
    if summary is None:
        missing_core.append("clinical/patient-summary.json")
    if not meds_p.exists():
        missing_core.append("ehr/medications.csv")
    if missing_core:
        row["status"] = STATUS_MISSING
        row["status_reason"] = "missing: " + ", ".join(missing_core)
        # still record whatever descriptive fields we can
    # --- Provenance integrity ---
    prov_cov = None
    if provenance is not None:
        prov_cov = provenance.get("provenance_coverage")
    if provenance is None:
        if row["status"] == STATUS_ELIGIBLE:
            row["status"] = STATUS_PROV
            row["status_reason"] = "provenance.json missing"
    elif isinstance(prov_cov, (int, float)) and prov_cov < 0.5:
        if row["status"] == STATUS_ELIGIBLE:
            row["status"] = STATUS_PROV
            row["status_reason"] = f"provenance_coverage {prov_cov:.2f} < 0.5"

    # --- Descriptive fields ---
    counts = (summary or {}).get("counts", {}) if summary else {}
    cv = (summary or {}).get("cardiovascular_context", []) if summary else []
    noncardiac = (
        (summary or {}).get("noncardiac_organ_systems", []) if summary else []
    )
    row["source_type"] = (manifest or {}).get("source_type")
    real = (manifest or {}).get("real_patient_data")
    row["real_or_synthetic"] = (
        "real" if real is True else ("synthetic" if real is False else None)
    )
    row["selection_tier"] = (manifest or {}).get("selection_tier")
    row["cardiac_category"] = "|".join(cv) if cv else "none"
    row["noncardiac_organ_systems"] = "|".join(noncardiac)
    row["organ_system_count"] = (
        len(cv) + len(noncardiac) if summary else 0
    )
    row["medication_count"] = counts.get("medications", 0) or 0
    row["allergy_count"] = counts.get("allergies", 0) or 0
    row["lab_count"] = counts.get("labs", 0) or 0
    row["vital_count"] = _count_csv_rows(case_dir / "ehr" / "vitals.csv")
    row["has_fhir"] = fhir_p.exists()
    row["has_report"] = (case_dir / "clinical" / "patient-report.txt").exists()
    row["has_pdf"] = (case_dir / "clinical" / "patient-report.pdf").exists()
    row["has_ccda"] = (case_dir / "clinical" / "ccda.xml").exists()
    row["has_tabular"] = meds_p.exists()
    row["has_ecg"] = (case_dir / "ecg" / "ecg.json").exists()

    med_ev_ok = False
    n_labels = 0
    if medev_p.exists():
        try:
            labels = _load_json(medev_p)
            n_labels = len(labels) if isinstance(labels, list) else 0
            med_ev_ok = n_labels > 0
        except (json.JSONDecodeError, ValueError):
            med_ev_ok = False
    row["has_medication_evidence"] = med_ev_ok
    row["label_evidence_count"] = n_labels
    n_norm = 0
    if normed_p.exists():
        try:
            nm = _load_json(normed_p)
            n_norm = len(nm) if isinstance(nm, list) else 0
        except (json.JSONDecodeError, ValueError):
            n_norm = 0
    row["normalized_med_count"] = n_norm
    row["completeness_score"] = (
        (quality or {}).get("overall_completeness_score")
    )
    row["linkage_type"] = (manifest or {}).get("linkage_type")

    # --- Warnings that downgrade an otherwise-eligible case ---
    warns = list((quality or {}).get("missingness_warnings", []) or [])
    if row["status"] == STATUS_ELIGIBLE:
        if not med_ev_ok:
            warns.append("no_medication_label_evidence")
        if n_norm == 0:
            warns.append("no_normalized_medications")
        cscore = row["completeness_score"]
        if isinstance(cscore, (int, float)) and cscore < 0.6:
            warns.append(f"low_completeness_{cscore:.2f}")
        if warns:
            row["status"] = STATUS_WARN
            row["status_reason"] = "; ".join(sorted(set(warns)))
    row["warnings"] = ";".join(sorted(set(warns)))
    return row


def main() -> int:
    import pandas as pd

    if not CASES_DIR.exists():
        print(f"ERROR: cases dir not found: {CASES_DIR}")
        return 1

    case_dirs = sorted(
        d for d in CASES_DIR.iterdir()
        if d.is_dir() and d.name.startswith("case-")
    )
    print(f"Indexing {len(case_dirs)} case directories under {CASES_DIR} ...")

    rows = []
    for i, d in enumerate(case_dirs, 1):
        try:
            rows.append(index_one(d))
        except Exception as exc:  # unexpected — record as corrupt, don't drop
            rows.append({
                "case_id": d.name,
                "status": STATUS_CORRUPT,
                "status_reason": f"unexpected: {exc!r}",
                "warnings": "",
            })
        if i % 200 == 0:
            print(f"  ... {i}/{len(case_dirs)}")

    df = pd.DataFrame(rows)
    # stable column order
    cols = [
        "case_id", "status", "status_reason", "source_type",
        "selection_tier", "real_or_synthetic", "cardiac_category",
        "noncardiac_organ_systems", "organ_system_count", "medication_count",
        "allergy_count", "lab_count", "vital_count", "has_fhir", "has_report",
        "has_pdf", "has_ccda", "has_tabular", "has_ecg",
        "has_medication_evidence", "label_evidence_count",
        "normalized_med_count", "completeness_score", "linkage_type",
        "warnings",
    ]
    cols = [c for c in cols if c in df.columns] + \
           [c for c in df.columns if c not in cols]
    df = df[cols]

    pq = RESULTS_DIR / "case_index.parquet"
    csv = RESULTS_DIR / "case_index.csv"
    try:
        df.to_parquet(pq, index=False)
    except Exception as exc:
        print(f"  (parquet write skipped: {exc})")
    df.to_csv(csv, index=False)

    counts = df["status"].value_counts().to_dict()
    summary = {
        "total_cases": int(len(df)),
        "status_counts": {k: int(v) for k, v in counts.items()},
        "eligible_for_run": int(
            df["status"].isin([STATUS_ELIGIBLE, STATUS_WARN]).sum()
        ),
        "with_medication_evidence": int(
            df.get("has_medication_evidence",
                   pd.Series(dtype=bool)).fillna(False).sum()
        ),
    }
    (RESULTS_DIR / "case_index_summary.json").write_text(
        json.dumps(summary, indent=2)
    )

    print(f"\nWrote {csv}")
    print(f"Wrote {pq}")
    print("\nEligibility breakdown:")
    for k, v in sorted(counts.items()):
        print(f"  {k:32s} {v}")
    print(f"\nEligible for run (eligible + warning): "
          f"{summary['eligible_for_run']}")
    print(f"Cases with medication label evidence: "
          f"{summary['with_medication_evidence']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
