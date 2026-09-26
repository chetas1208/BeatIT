#!/usr/bin/env python3
"""Imaging stage 08 — validate DICOM CT series (spec §11).

Validates every imported DICOM series: modality CT, single Series/Study UID, no
mixed patients, unique SOP UIDs, pixel data present, coherent orientation and
slice ordering, valid spacing/thickness, rescale slope/intercept handling (HU
preserved), PHI check, no corrupt/undecodable slices. Corrupt series are
quarantined. Writes analysis/imaging/dicom_validation.{csv,json}.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402


def _dicom_series_dirs() -> list[Path]:
    base = I.RAW_TOTALSEG / "dicom"
    if not base.exists():
        return []
    return [d for d in base.iterdir() if d.is_dir() and any(d.glob("*.dcm"))]


def validate_series(sdir: Path, log) -> dict:
    import numpy as np
    import pydicom
    issues, warnings = [], []
    files = sorted(sdir.glob("*.dcm"))
    slices, series_uids, study_uids, patients, sop_uids, inst_nums = [], set(), set(), set(), [], []
    for f in files:
        try:
            ds = pydicom.dcmread(str(f))
        except Exception as e:
            issues.append(f"corrupt/undecodable slice {f.name}: {e}")
            continue
        if getattr(ds, "Modality", None) != "CT":
            issues.append(f"non-CT modality {getattr(ds, 'Modality', None)} in {f.name}")
        series_uids.add(getattr(ds, "SeriesInstanceUID", None))
        study_uids.add(getattr(ds, "StudyInstanceUID", None))
        patients.add(getattr(ds, "PatientID", None))
        sop = getattr(ds, "SOPInstanceUID", None)
        sop_uids.append(str(sop) if sop else "")
        inst_nums.append(getattr(ds, "InstanceNumber", None))
        try:
            _ = ds.pixel_array
        except Exception as e:
            issues.append(f"no/invalid pixel data in {f.name}: {e}")
        slices.append(ds)

    if len(series_uids) > 1:
        issues.append(f"mixed SeriesInstanceUID ({len(series_uids)})")
    if len(study_uids) > 1:
        issues.append(f"mixed StudyInstanceUID ({len(study_uids)})")
    if len([p for p in patients if p]) > 1:
        issues.append(f"mixed patients ({len(patients)})")
    nonempty_sop = [u for u in sop_uids if u]
    if not nonempty_sop:
        warnings.append("SOPInstanceUID blanked on all slices (deidentification) — "
                        "verifying uniqueness/ordering via InstanceNumber instead")
        inums = [i for i in inst_nums if i is not None]
        if len(inums) != len(set(inums)):
            issues.append("duplicate InstanceNumber with blanked SOP UIDs")
    elif len(nonempty_sop) != len(set(nonempty_sop)):
        issues.append("duplicate SOPInstanceUID")

    # orientation + ordering + spacing
    spacing = thickness = None
    if slices:
        s0 = slices[0]
        iops = {tuple(round(x, 4) for x in getattr(sl, "ImageOrientationPatient", []) or [])
                for sl in slices if getattr(sl, "ImageOrientationPatient", None)}
        if len(iops) > 1:
            warnings.append("inconsistent ImageOrientationPatient across slices")
        positions = [getattr(sl, "ImagePositionPatient", None) for sl in slices]
        zs = [float(p[2]) for p in positions if p]
        if zs and sorted(zs) != zs and sorted(zs, reverse=True) != zs:
            warnings.append("slice z-positions not monotonic (need reordering)")
        ps = getattr(s0, "PixelSpacing", None)
        thickness = float(getattr(s0, "SliceThickness", 0) or 0)
        if ps:
            spacing = [float(ps[0]), float(ps[1]), thickness]
            if spacing[0] <= 0 or spacing[1] <= 0:
                issues.append("invalid in-plane spacing")
        else:
            issues.append("missing PixelSpacing")
        if thickness and not (0.1 <= thickness <= 10.0):
            warnings.append(f"implausible slice thickness {thickness}mm")
        # HU / rescale handling
        slope = getattr(s0, "RescaleSlope", None)
        intercept = getattr(s0, "RescaleIntercept", None)
        if slope is None or intercept is None:
            warnings.append("RescaleSlope/Intercept absent — HU assumed identity")
        else:
            arr = s0.pixel_array.astype("float32") * float(slope) + float(intercept)
            if float(np.min(arr)) > -100:
                warnings.append("HU minimum unusually high — verify rescale")
        # PHI check per source policy (TotalSegmentator examples are deidentified)
        name = str(getattr(s0, "PatientName", "") or "")
        if name and name.lower() not in ("", "anonymous", "anonymized"):
            warnings.append(f"PatientName present ('{name}') — verify source deid policy")

    valid = len(issues) == 0
    return {"series": sdir.name, "n_slices": len(files), "readable_slices": len(slices),
            "modality": "CT", "series_uids": len(series_uids), "study_uids": len(study_uids),
            "patients": len([p for p in patients if p]), "spacing": spacing,
            "slice_thickness": thickness, "valid": valid,
            "n_issues": len(issues), "issues": "; ".join(issues[:8]),
            "n_warnings": len(warnings), "warnings": "; ".join(warnings[:8])}


def main() -> None:
    import csv
    I.ensure_dirs()
    log = I.C.get_logger("imaging_08_dicom")
    log.info("=== Imaging 08: validate DICOM ===")
    dirs = _dicom_series_dirs()
    log.info("found %d DICOM series", len(dirs))
    rows = []
    for sdir in dirs:
        r = validate_series(sdir, log)
        rows.append(r)
        log.info("series %s valid=%s issues=%d warnings=%d", r["series"], r["valid"],
                 r["n_issues"], r["n_warnings"])
        if not r["valid"]:
            dest = I.QUAR_CORRUPT / sdir.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(sdir, dest)
            log.warning("quarantined invalid series %s (copy)", sdir.name)

    if rows:
        with open(I.ANALYSIS_IMAGING / "dicom_validation.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    I.C.write_json(I.ANALYSIS_IMAGING / "dicom_validation.json",
                   {"generated_at": I.C.now_iso(), "series": rows})
    log.info("=== Imaging 08 complete: %d/%d valid ===",
             sum(1 for r in rows if r["valid"]), len(rows))
    print(f"dicom_valid={sum(1 for r in rows if r['valid'])}/{len(rows)}")


if __name__ == "__main__":
    main()
