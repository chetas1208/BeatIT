#!/usr/bin/env python3
"""Imaging stage 00 — audit every existing case for legitimately linked CT.

READ-ONLY: never modifies a case (spec §4). Determines, per case, whether actual
CT pixels exist, whether only an imaging reference/report exists, whether a
same-subject mapping exists, and whether any CT was incorrectly matched from a
different dataset. Writes existing_ct_audit.{csv,parquet,json,md}.

For eICU-derived cases the truthful result is `no_linked_ct`: eICU distributes no
same-subject CT pixel data. A DiagnosticReport carrying the *external ECG* is NOT
counted as CT.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402
from python.hearttwin.careguard.imaging import linkage as L  # noqa: E402

VOLUME_EXTS = (".dcm", ".nii", ".nii.gz", ".nrrd", ".mha", ".mhd", ".npz")


def find_ct_volumes(cdir: Path) -> list[str]:
    """CT pixel volumes only. Excludes ECG WFDB (.dat/.hea) and DICOM SC of the ECG."""
    vols = []
    for p in cdir.rglob("*"):
        if not p.is_file():
            continue
        name = p.name.lower()
        # the ECG secondary-capture .dcm is NOT a CT volume — exclude it
        if name == "ecg-secondary-capture.dcm":
            continue
        if name.endswith(VOLUME_EXTS):
            vols.append(str(p.relative_to(cdir)))
    return vols


def bundle_has_imaging(cdir: Path) -> tuple[bool, bool]:
    """Return (has_imaging_reference, has_ct_imaging_study)."""
    bpath = cdir / "clinical" / "fhir-bundle.json"
    if not bpath.exists():
        return False, False
    try:
        bundle = I.C.read_json(bpath)
    except Exception:
        return False, False
    has_ref = has_ct_study = False
    for e in bundle.get("entry", []):
        rt = e.get("resource", {}).get("resourceType")
        if rt == "ImagingStudy":
            has_ref = True
            mods = str(e.get("resource", {})).lower()
            if "ct" in mods:
                has_ct_study = True
        if rt == "DocumentReference":
            has_ref = True
    return has_ref, has_ct_study


def audit_case(cdir: Path) -> dict:
    manifest = I.C.read_json(cdir / "manifest.json") if (cdir / "manifest.json").exists() else {}
    vols = find_ct_volumes(cdir)
    has_ref, has_ct_study = bundle_has_imaging(cdir)

    # existing ct_imaging block (if a prior run stamped one)
    existing = manifest.get("ct_imaging") or {}
    prior_status = existing.get("status")
    prohibited = prior_status == L.PROHIBITED or (
        existing.get("same_subject_as_clinical_record") and
        existing.get("linkage_confidence") == "prohibited")

    has_actual = bool(vols)
    volume_format = Path(vols[0]).suffix if vols else None

    if prohibited:
        status, reason, vista = L.PROHIBITED, "prior cross-dataset CT match detected", False
    elif has_actual:
        # a real CT volume is present — was it verified same-subject?
        srcid = existing.get("source_subject_id")
        if existing.get("status") in (L.SAME_SUBJECT_VERIFIED, L.IMAGING_NATIVE_SAME_SUBJECT):
            status, reason, vista = existing["status"], "verified same-subject linkage", True
        else:
            status, reason, vista = L.IMAGING_ONLY, "CT present without verified same-subject linkage", True
    else:
        status = L.NO_LINKED_CT
        reason = ("radiology/imaging reference only, no retrievable CT pixels"
                  if has_ref else "eICU record carries no same-subject CT pixel data")
        vista = False

    return {
        "case_id": cdir.name,
        "clinical_source": manifest.get("source_dataset", "eICU-CRD Demo 2.0.1"),
        "has_imaging_reference": has_ref,
        "has_actual_volume": has_actual,
        "volume_format": volume_format,
        "source_subject_id": existing.get("source_subject_id"),
        "source_study_id": existing.get("source_study_id"),
        "source_series_id": existing.get("source_series_id"),
        "linkage_status": status,
        "linkage_evidence": ";".join(str(e) for e in existing.get("linkage_evidence", [])) or "",
        "vista_eligible": vista,
        "failure_reason": reason,
    }


def main() -> None:
    import pandas as pd
    I.ensure_dirs()
    log = I.C.get_logger("imaging_00_audit")
    log.info("=== Imaging 00: audit existing CT linkage (READ-ONLY) ===")
    case_dirs = sorted([d for d in I.CASES.glob("case-*") if d.is_dir()])
    log.info("auditing %d existing cases", len(case_dirs))

    rows = [audit_case(d) for d in case_dirs]
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=["case_id", "clinical_source", "has_imaging_reference",
                                   "has_actual_volume", "volume_format", "source_subject_id",
                                   "source_study_id", "source_series_id", "linkage_status",
                                   "linkage_evidence", "vista_eligible", "failure_reason"])
    df.to_csv(I.AI_LINKAGE / "existing_ct_audit.csv", index=False)
    df.to_parquet(I.AI_LINKAGE / "existing_ct_audit.parquet", index=False)
    I.C.write_json(I.AI_LINKAGE / "existing_ct_audit.json", rows)

    status_counts = df["linkage_status"].value_counts().to_dict() if len(df) else {}
    summary = {
        "generated_at": I.C.now_iso(), "total_cases": len(df),
        "with_actual_ct_volume": int(df["has_actual_volume"].sum()) if len(df) else 0,
        "verified_same_subject": int((df["linkage_status"] == L.SAME_SUBJECT_VERIFIED).sum()) if len(df) else 0,
        "no_linked_ct": int((df["linkage_status"] == L.NO_LINKED_CT).sum()) if len(df) else 0,
        "prohibited_cross_dataset": int((df["linkage_status"] == L.PROHIBITED).sum()) if len(df) else 0,
        "status_counts": status_counts,
    }
    md = ["# Existing CT Linkage Audit (read-only)", "",
          f"_Generated {summary['generated_at']}_", "",
          f"- Total clinical cases audited: **{summary['total_cases']}**",
          f"- Cases with an actual CT pixel volume: **{summary['with_actual_ct_volume']}**",
          f"- Verified same-subject CT: **{summary['verified_same_subject']}**",
          f"- No linked CT: **{summary['no_linked_ct']}**",
          f"- Prohibited cross-dataset pairings: **{summary['prohibited_cross_dataset']}**", "",
          "> eICU distributes no same-subject CT pixels; the truthful default is "
          "`no_linked_ct`. No unrelated CT is ever backfilled onto a clinical case.",
          "", "## Status counts", ""]
    for k, v in status_counts.items():
        md.append(f"- `{k}`: {v}")
    (I.AI_LINKAGE / "existing_ct_audit.md").write_text("\n".join(md))
    I.C.write_json(I.AI_LINKAGE / "existing_ct_audit_summary.json", summary)
    log.info("=== Imaging 00 complete: %s ===", status_counts)
    print(f"audited={len(df)} status={status_counts}")


if __name__ == "__main__":
    main()
