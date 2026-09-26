"""Imaging stage 09 — convert DICOM series to NIfTI + validate all NIfTI (spec §11).

DICOM→NIfTI uses pydicom + nibabel (dcm2niix used if present) preserving voxel
spacing, orientation, affine, and HU (rescale slope/intercept). Originals are never
overwritten; normalized volumes go to staging/imaging/normalized/<subject>/.
Existing NIfTI subjects are validated in place and copied to normalized/.

NIfTI validation: 3D dimensionality, finite affine, spacing, finite voxels,
plausible CT intensity distribution, non-empty volume, non-all-zero mask.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402


def dicom_to_nifti(sdir: Path, out: Path, log) -> dict:
    import numpy as np
    import nibabel as nib
    import pydicom
    files = sorted(sdir.glob("*.dcm"))
    slices = []
    for f in files:
        try:
            ds = pydicom.dcmread(str(f))
            if hasattr(ds, "ImagePositionPatient") and hasattr(ds, "pixel_array"):
                slices.append(ds)
        except Exception as e:
            log.warning("skip slice %s: %s", f.name, e)
    if not slices:
        return {"ok": False, "reason": "no readable slices"}
    # sort along slice normal
    iop = [float(x) for x in slices[0].ImageOrientationPatient]
    normal = np.cross(iop[:3], iop[3:])
    slices.sort(key=lambda s: float(np.dot(normal, [float(x) for x in s.ImagePositionPatient])))
    slope = float(getattr(slices[0], "RescaleSlope", 1) or 1)
    intercept = float(getattr(slices[0], "RescaleIntercept", 0) or 0)
    vol = np.stack([s.pixel_array.astype("float32") * slope + intercept for s in slices], axis=-1)

    ps = [float(x) for x in slices[0].PixelSpacing]
    if len(slices) > 1:
        p0 = np.array([float(x) for x in slices[0].ImagePositionPatient])
        p1 = np.array([float(x) for x in slices[1].ImagePositionPatient])
        dz = float(np.linalg.norm(p1 - p0))
    else:
        dz = float(getattr(slices[0], "SliceThickness", 1) or 1)
    # affine from orientation vectors + spacing + origin
    row = np.array(iop[:3]) * ps[0]
    col = np.array(iop[3:]) * ps[1]
    slc = normal * dz
    origin = np.array([float(x) for x in slices[0].ImagePositionPatient])
    affine = np.eye(4)
    affine[:3, 0], affine[:3, 1], affine[:3, 2], affine[:3, 3] = row, col, slc, origin
    img = nib.Nifti1Image(vol.astype("float32"), affine)
    out.parent.mkdir(parents=True, exist_ok=True)
    nib.save(img, str(out))
    return {"ok": True, "shape": list(vol.shape), "spacing": [ps[0], ps[1], dz],
            "affine": affine.tolist(), "hu_min": float(vol.min()), "hu_max": float(vol.max()),
            "rescale_slope": slope, "rescale_intercept": intercept, "n_slices": len(slices)}


def validate_nifti(path: Path, is_mask: bool = False) -> dict:
    import numpy as np
    import nibabel as nib
    issues = []
    try:
        img = nib.load(str(path))
    except Exception as e:
        return {"path": str(path), "valid": False, "issues": f"load failed: {e}"}
    data = img.get_fdata()
    aff = img.affine
    zooms = img.header.get_zooms()
    if data.ndim != 3:
        issues.append(f"expected 3D, got {data.ndim}D")
    if not np.all(np.isfinite(aff)):
        issues.append("non-finite affine")
    if any(z <= 0 for z in zooms[:3]):
        issues.append(f"invalid spacing {zooms[:3]}")
    if not np.all(np.isfinite(data)):
        issues.append("non-finite voxel values (NaN/Inf)")
    if float(np.ptp(data)) == 0:
        issues.append("empty volume (all identical voxels)")
    if is_mask:
        if float(np.count_nonzero(data)) == 0:
            issues.append("all-zero mask")
    else:
        # plausible CT intensity distribution (HU): should span air..soft tissue
        if float(data.min()) > -200 or float(data.max()) < 100:
            issues.append(f"unexpected CT intensity range [{data.min():.0f},{data.max():.0f}]")
    return {"path": str(path.relative_to(I.C.DATA_DIR)), "shape": list(data.shape),
            "spacing": [round(float(z), 3) for z in zooms[:3]],
            "n_labels": int(len(np.unique(data))) if is_mask else None,
            "intensity_min": round(float(data.min()), 1), "intensity_max": round(float(data.max()), 1),
            "valid": len(issues) == 0, "issues": "; ".join(issues)}


def main() -> None:
    import csv
    import shutil as sh
    if which_dcm2niix := shutil.which("dcm2niix"):
        pass
    I.ensure_dirs()
    log = I.C.get_logger("imaging_09_convert")
    log.info("=== Imaging 09: DICOM->NIfTI + validate NIfTI ===")

    summary = I.C.read_json(I.RAW_TOTALSEG / "import_summary.json") \
        if (I.RAW_TOTALSEG / "import_summary.json").exists() else {"subjects": []}
    conv_rows, val_rows = [], []
    for s in summary.get("subjects", []):
        sid = s["subject_id"]
        norm_dir = I.STG_NORMALIZED / sid
        norm_dir.mkdir(parents=True, exist_ok=True)
        ct_out = norm_dir / "ct.nii.gz"
        if s["format"] == "dicom":
            conv = dicom_to_nifti(Path(s["ct_path"]), ct_out, log)
            conv["subject_id"] = sid
            conv["dcm2niix_available"] = bool(which_dcm2niix)
            conv["method"] = "dcm2niix" if which_dcm2niix else "pydicom+nibabel"
            conv_rows.append(conv)
            I.C.write_json(norm_dir / "conversion.json", conv)
        else:
            # already NIfTI: copy to normalized (never overwrite original)
            sh.copyfile(s["ct_path"], ct_out)
            I.C.write_json(norm_dir / "conversion.json",
                           {"subject_id": sid, "method": "passthrough_nifti",
                            "source": s["ct_path"], "converted_sha256": I.C.sha256_file(ct_out)})
        # copy reference mask
        if s.get("ref_mask_path") and Path(s["ref_mask_path"]).exists():
            sh.copyfile(s["ref_mask_path"], norm_dir / "reference_mask.nii.gz")
        # validate
        vc = validate_nifti(ct_out, is_mask=False)
        vc["subject_id"] = sid
        vc["kind"] = "ct"
        val_rows.append(vc)
        if (norm_dir / "reference_mask.nii.gz").exists():
            vm = validate_nifti(norm_dir / "reference_mask.nii.gz", is_mask=True)
            vm["subject_id"] = sid
            vm["kind"] = "reference_mask"
            val_rows.append(vm)
        log.info("subject %s ct_valid=%s", sid, vc["valid"])

    if conv_rows:
        I.C.write_json(I.ANALYSIS_IMAGING / "dicom_to_nifti_conversion.json", conv_rows)
    if val_rows:
        cols = ["subject_id", "kind", "path", "shape", "spacing", "n_labels",
                "intensity_min", "intensity_max", "valid", "issues"]
        with open(I.ANALYSIS_IMAGING / "nifti_validation.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader(); w.writerows(val_rows)
    log.info("=== Imaging 09 complete: %d converted, %d NIfTI validated (%d valid) ===",
             len(conv_rows), len(val_rows), sum(1 for r in val_rows if r["valid"]))
    print(f"converted={len(conv_rows)} nifti_valid={sum(1 for r in val_rows if r['valid'])}/{len(val_rows)}")


if __name__ == "__main__":
    main()
