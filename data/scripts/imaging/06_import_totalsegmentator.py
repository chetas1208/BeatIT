#!/usr/bin/env python3
"""Imaging stage 06 — import a small REAL open TotalSegmentator subset (spec §6 Tier 4).

Downloads the TotalSegmentator example CT volumes + reference masks + a real DICOM
series (Apache-2.0 repo; dataset CC BY 4.0) into raw/totalsegmentator/ and registers
each as an `imaging_only` benchmark subject. These are real CT scans used ONLY for
segmentation/anatomy benchmarking — never attached to an eICU patient.

Idempotent: existing files are skipped. Bounded to a few subjects.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402

RAW_BASE = "https://raw.githubusercontent.com/wasserth/TotalSegmentator/master/tests/reference_files"
API_DICOM = "https://api.github.com/repos/wasserth/TotalSegmentator/contents/tests/reference_files/example_ct_dicom"

# subject_id -> {ct (nifti), seg (nifti mask)} for the NIfTI subjects
NIFTI_SUBJECTS = {
    "ts_example_full": {"ct": "example_ct.nii.gz", "seg": "example_seg.nii.gz"},
    "ts_example_sm": {"ct": "example_ct_sm.nii.gz", "seg": "example_seg_fast.nii.gz"},
}
DICOM_SUBJECT = "ts_example_dicom"


def _dl(url: str, dest: Path, log) -> bool:
    try:
        I.C.download(url, dest, logger=log, retries=3, timeout=60)
        return True
    except Exception as e:
        log.warning("download failed %s: %s", url, e)
        return False


def import_nifti_subjects(log) -> list[dict]:
    out = []
    for sid, files in NIFTI_SUBJECTS.items():
        sdir = I.RAW_TOTALSEG / "nifti" / sid
        sdir.mkdir(parents=True, exist_ok=True)
        ct = sdir / "ct.nii.gz"
        seg = sdir / "segmentation.nii.gz"
        ok_ct = _dl(f"{RAW_BASE}/{files['ct']}", ct, log)
        ok_seg = _dl(f"{RAW_BASE}/{files['seg']}", seg, log)
        if not ok_ct:
            continue
        out.append({"subject_id": sid, "format": "nifti", "ct_path": str(ct),
                    "ref_mask_path": str(seg) if ok_seg else None,
                    "source_file": files["ct"], "ref_source_file": files["seg"] if ok_seg else None})
        log.info("imported NIfTI subject %s", sid)
    return out


def import_dicom_subject(log) -> list[dict]:
    sdir = I.RAW_TOTALSEG / "dicom" / DICOM_SUBJECT
    sdir.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(API_DICOM, headers={"User-Agent": "careguard/1.0",
                                                         "Accept": "application/vnd.github+json"})
        listing = json.load(urllib.request.urlopen(req, timeout=40))
    except Exception as e:
        log.warning("could not list DICOM series: %s", e)
        return []
    n = 0
    for entry in listing:
        if entry.get("type") != "file":
            continue
        dest = sdir / (entry["name"] + ".dcm")
        if _dl(entry["download_url"], dest, log):
            n += 1
    # reference mask for the dicom series
    seg = sdir / "segmentation.nii.gz"
    ok_seg = _dl(f"{RAW_BASE}/example_seg_dicom.nii.gz", seg, log)
    log.info("imported DICOM subject %s (%d slices)", DICOM_SUBJECT, n)
    if n == 0:
        return []
    return [{"subject_id": DICOM_SUBJECT, "format": "dicom", "ct_path": str(sdir),
             "n_slices": n, "ref_mask_path": str(seg) if ok_seg else None,
             "source_file": "example_ct_dicom/", "ref_source_file": "example_seg_dicom.nii.gz"}]


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_06_totalseg")
    log.info("=== Imaging 06: import TotalSegmentator open subset ===")

    st = I.source_access_state("totalsegmentator")
    if not st["access_verified"]:
        log.warning("TotalSegmentator disabled (TOTALSEGMENTATOR_DATASET_ENABLED); skipping")
        I.C.write_json(I.RAW_TOTALSEG / "import_summary.json",
                       {"imported": 0, "reason": "source disabled"})
        print("totalseg_imported=0 (disabled)")
        return
    subset_size = I.env_int("TOTALSEGMENTATOR_SUBSET_SIZE", 6)
    if subset_size <= 0:
        log.info("TOTALSEGMENTATOR_SUBSET_SIZE=0 -> manifest only, no downloads")
        I.C.write_json(I.RAW_TOTALSEG / "import_summary.json", {"imported": 0, "reason": "subset_size=0"})
        print("totalseg_imported=0 (manifest only)")
        return

    subjects = import_nifti_subjects(log) + import_dicom_subject(log)
    # checksum every imported CT file
    for s in subjects:
        p = Path(s["ct_path"])
        if p.is_file():
            s["sha256"] = I.C.sha256_file(p)
        elif p.is_dir():
            files = sorted(p.glob("*.dcm"))
            s["sha256"] = I.C.sha256_file(files[0]) if files else None
        if s.get("ref_mask_path") and Path(s["ref_mask_path"]).exists():
            s["ref_mask_sha256"] = I.C.sha256_file(Path(s["ref_mask_path"]))

    I.C.write_json(I.RAW_TOTALSEG / "import_summary.json", {
        "generated_at": I.C.now_iso(), "source": "totalsegmentator",
        "license": I.SOURCES["totalsegmentator"]["license"],
        "doi": I.SOURCES["totalsegmentator"]["doi"],
        "linkage": "imaging_only — real CT, no same-subject clinical record; never fused to eICU",
        "imported": len(subjects), "subjects": subjects})
    log.info("=== Imaging 06 complete: %d TotalSegmentator subjects ===", len(subjects))
    print(f"totalseg_imported={len(subjects)}")


if __name__ == "__main__":
    main()
