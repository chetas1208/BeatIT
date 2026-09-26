#!/usr/bin/env python3
"""Imaging stage 14 — build imaging-native / benchmark cases (spec §7 Cohort B/C).

Each imported CT subject becomes an imaging case under data/imaging-cases/ with its
own linkage status. TotalSegmentator subjects are `imaging_only` (real CT, no
same-subject clinical record) and are NEVER attached to an eICU patient. They also
register into the VISTA benchmark (Cohort C). Idempotent.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402
from python.hearttwin.careguard.imaging import linkage as L  # noqa: E402

DISC_IMAGING_ONLY = ("This CT is an imaging benchmark record and is not linked to any "
                     "clinical case. It is a real, deidentified scan used only for VISTA "
                     "segmentation/anatomy benchmarking.")


def build_case(idx: int, subj: dict, cfg) -> dict:
    sid = subj["subject_id"]
    icid = f"imaging-case-{idx:06d}"
    cdir = I.IMAGING_CASES / icid
    (cdir / "imaging" / "source").mkdir(parents=True, exist_ok=True)
    (cdir / "imaging" / "normalized").mkdir(parents=True, exist_ok=True)
    (cdir / "imaging" / "references").mkdir(parents=True, exist_ok=True)

    norm_dir = I.STG_NORMALIZED / sid
    if (norm_dir / "ct.nii.gz").exists():
        shutil.copyfile(norm_dir / "ct.nii.gz", cdir / "imaging" / "normalized" / "ct.nii.gz")
    if (norm_dir / "conversion.json").exists():
        shutil.copyfile(norm_dir / "conversion.json", cdir / "imaging" / "normalized" / "conversion.json")
    ref = norm_dir / "reference_mask.nii.gz"
    has_ref = ref.exists()
    if has_ref:
        shutil.copyfile(ref, cdir / "imaging" / "references" / "reference_mask.nii.gz")

    # linkage: imaging_only (real CT, no verified same-subject clinical record)
    link = L.CtImagingLinkage(
        status=L.IMAGING_ONLY, source_dataset="totalsegmentator",
        source_subject_id=sid, source_study_id=sid, source_series_id=sid,
        same_subject_as_clinical_record=False, linkage_confidence="unavailable",
        vista_eligible=True,
        reason="Real TotalSegmentator CT; no same-subject clinical record — segmentation-only.")

    src_meta = {"subject_id": sid, "source_dataset": "TotalSegmentator dataset",
                "license": cfg["sources"]["ptbxl"]["license"] if False else
                I.SOURCES["totalsegmentator"]["license"],
                "doi": I.SOURCES["totalsegmentator"]["doi"], "format": subj["format"],
                "sha256": subj.get("sha256"), "n_slices": subj.get("n_slices"),
                "has_reference_mask": has_ref, "modality": "CT"}
    I.C.write_json(cdir / "imaging" / "source" / "source-metadata.json", src_meta)

    manifest = {
        "imaging_case_id": icid, "case_type": "imaging_only",
        "source_dataset": "totalsegmentator", "source_subject_id": sid,
        "real_ct": True, **link.to_dict(),
        "disclaimer": DISC_IMAGING_ONLY,
        "chatbot_contract": ("This is a real coronary/thoracic CT used to demonstrate VISTA "
                             "segmentation. It is not fused with an unrelated EHR patient "
                             "because no verified same-subject clinical record is available."),
        "license": I.SOURCES["totalsegmentator"]["license"],
        "has_reference_mask": has_ref,
    }
    I.C.write_json(cdir / "manifest.json", manifest)
    (cdir / "README.md").write_text(
        f"# {icid} — imaging-only benchmark case\n\n> {DISC_IMAGING_ONLY}\n\n"
        f"- Source: TotalSegmentator subject `{sid}` (real, deidentified CT).\n"
        f"- Linkage: **{L.IMAGING_ONLY}** — never attached to an eICU patient.\n"
        f"- Reference mask available: {has_ref}\n")

    # register in vista-benchmark
    I.C.write_json(I.VB_MANIFESTS / f"{icid}.json", {
        "imaging_case_id": icid, "cohort": "vista_benchmark", "subtype": "imaging_only",
        "source_dataset": "totalsegmentator", "source_subject_id": sid,
        "input_nifti": f"imaging-cases/{icid}/imaging/normalized/ct.nii.gz",
        "reference_mask": f"imaging-cases/{icid}/imaging/references/reference_mask.nii.gz" if has_ref else None,
        "vista_eligible": True, "linkage_status": L.IMAGING_ONLY})
    return {"imaging_case_id": icid, "source_dataset": "totalsegmentator",
            "source_subject_id": sid, "case_type": "imaging_only",
            "linkage_status": L.IMAGING_ONLY, "has_reference_mask": has_ref,
            "vista_eligible": True}


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_14_native_cases")
    cfg = I.C.load_config()
    log.info("=== Imaging 14: build imaging-native / benchmark cases ===")
    summary = I.C.read_json(I.RAW_TOTALSEG / "import_summary.json") \
        if (I.RAW_TOTALSEG / "import_summary.json").exists() else {"subjects": []}
    rows = []
    for i, subj in enumerate(summary.get("subjects", []), 1):
        rows.append(build_case(i, subj, cfg))
        log.info("built %s from %s", rows[-1]["imaging_case_id"], subj["subject_id"])
    I.C.write_json(I.IMAGING_CASES / "imaging_cases_index.json",
                   {"generated_at": I.C.now_iso(), "count": len(rows), "cases": rows})
    log.info("=== Imaging 14 complete: %d imaging cases (all imaging_only) ===", len(rows))
    print(f"imaging_cases={len(rows)}")


if __name__ == "__main__":
    main()
