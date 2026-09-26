#!/usr/bin/env python3
"""Imaging stage 03 — subject-level imaging manifest + stamp ct_imaging into every
clinical case manifest (spec §3/§10).

Builds cohort/imaging_manifest.{csv,parquet,ndjson} from imported imaging cases and
stamps the `ct_imaging` linkage block into each of the 1000 clinical case
manifests (additive, idempotent) using the read-only audit's determination.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402
from python.hearttwin.careguard.imaging import linkage as L  # noqa: E402


def nifti_geo(icid: str) -> dict:
    p = I.IMAGING_CASES / icid / "imaging" / "normalized" / "conversion.json"
    if not p.exists():
        return {}
    c = I.C.read_json(p)
    return {"scan_shape": c.get("shape"), "scan_spacing": c.get("spacing"),
            "slice_count": (c.get("shape") or [None, None, None])[2] if c.get("shape") else None}


def build_imaging_manifest(log) -> list[dict]:
    idx_path = I.IMAGING_CASES / "imaging_cases_index.json"
    if not idx_path.exists():
        return []
    idx = I.C.read_json(idx_path)
    rows = []
    for c in idx.get("cases", []):
        icid = c["imaging_case_id"]
        geo = nifti_geo(icid)
        nifti = I.IMAGING_CASES / icid / "imaging" / "normalized" / "ct.nii.gz"
        ref = I.IMAGING_CASES / icid / "imaging" / "references" / "reference_mask.nii.gz"
        rows.append({
            "imaging_case_id": icid, "source_dataset": c["source_dataset"],
            "source_version": I.SOURCES.get(c["source_dataset"], {}).get("doi"),
            "source_subject_id": c["source_subject_id"], "source_study_id": c["source_subject_id"],
            "source_series_id": c["source_subject_id"], "source_scan_id": c["source_subject_id"],
            "linked_clinical_subject_id": None, "same_subject_verified": False,
            "linkage_method": "native_imaging_only", "linkage_evidence_path": f"imaging-cases/{icid}/manifest.json",
            "modality": "CT", "body_region": "thorax_abdomen", "contrast_status": "unknown",
            "source_format": "nifti/dicom", "local_source_path": f"imaging-cases/{icid}/imaging/source",
            "normalized_nifti_path": str(nifti.relative_to(I.C.DATA_DIR)) if nifti.exists() else None,
            "reference_mask_paths": str(ref.relative_to(I.C.DATA_DIR)) if ref.exists() else None,
            "scan_spacing": geo.get("scan_spacing"), "scan_shape": geo.get("scan_shape"),
            "orientation": "RAS", "slice_count": geo.get("slice_count"),
            "file_size_bytes": nifti.stat().st_size if nifti.exists() else None,
            "sha256": I.C.sha256_file(nifti) if nifti.exists() else None,
            "license": c.get("license") or I.SOURCES["totalsegmentator"]["license"],
            "vista_eligible": c["vista_eligible"], "vista_ineligibility_reason": ""
                             if c["vista_eligible"] else "not eligible",
        })
    return rows


def stamp_case_manifests(audit_rows, log) -> int:
    by_case = {r["case_id"]: r for r in audit_rows}
    n = 0
    for cdir in sorted(I.CASES.glob("case-*")):
        mpath = cdir / "manifest.json"
        if not mpath.exists():
            continue
        m = I.C.read_json(mpath)
        a = by_case.get(cdir.name, {})
        link = L.CtImagingLinkage(
            status=a.get("linkage_status", L.NO_LINKED_CT),
            source_dataset=None, source_subject_id=None,
            same_subject_as_clinical_record=False,
            linkage_confidence="unavailable", vista_eligible=bool(a.get("vista_eligible", False)),
            reason=a.get("failure_reason", "eICU record carries no same-subject CT pixel data"))
        m["ct_imaging"] = link.to_dict()["ct_imaging"]
        I.C.write_json(mpath, m)
        n += 1
    return n


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_03_manifest")
    log.info("=== Imaging 03: build imaging manifest + stamp ct_imaging ===")

    rows = build_imaging_manifest(log)
    cols = ["imaging_case_id", "source_dataset", "source_version", "source_subject_id",
            "source_study_id", "source_series_id", "source_scan_id", "linked_clinical_subject_id",
            "same_subject_verified", "linkage_method", "linkage_evidence_path", "modality",
            "body_region", "contrast_status", "source_format", "local_source_path",
            "normalized_nifti_path", "reference_mask_paths", "scan_spacing", "scan_shape",
            "orientation", "slice_count", "file_size_bytes", "sha256", "license",
            "vista_eligible", "vista_ineligibility_reason"]
    with open(I.COHORT / "imaging_manifest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    I.C.write_ndjson(I.COHORT / "imaging_manifest.ndjson", rows)
    try:
        import pandas as pd
        pd.DataFrame(rows, columns=cols).to_parquet(I.COHORT / "imaging_manifest.parquet", index=False)
    except Exception as e:
        log.warning("parquet write skipped: %s", e)

    # stamp ct_imaging into clinical case manifests using the audit
    audit_path = I.AI_LINKAGE / "existing_ct_audit.json"
    audit_rows = I.C.read_json(audit_path) if audit_path.exists() else []
    n_stamped = stamp_case_manifests(audit_rows, log)

    log.info("=== Imaging 03 complete: %d imaging rows; stamped %d clinical manifests ===",
             len(rows), n_stamped)
    print(f"imaging_rows={len(rows)} stamped={n_stamped}")


if __name__ == "__main__":
    main()
