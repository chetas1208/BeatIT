"""Deterministic segmentation metrics (spec §19).

Pure functions over binary masks (numpy). Distance metrics use physical voxel
spacing. Only identical structures should be compared — the caller supplies an
explicit, reviewed label map; these functions never decide comparability.
"""
from __future__ import annotations

import numpy as np


def _binimg(m):
    return np.asarray(m) > 0


def dice(pred, ref) -> float:
    p, r = _binimg(pred), _binimg(ref)
    denom = p.sum() + r.sum()
    if denom == 0:
        return 1.0  # both empty -> perfect agreement
    return float(2.0 * np.logical_and(p, r).sum() / denom)


def jaccard(pred, ref) -> float:
    p, r = _binimg(pred), _binimg(ref)
    union = np.logical_or(p, r).sum()
    if union == 0:
        return 1.0
    return float(np.logical_and(p, r).sum() / union)


def sensitivity(pred, ref) -> float:
    p, r = _binimg(pred), _binimg(ref)
    if r.sum() == 0:
        return float("nan")
    return float(np.logical_and(p, r).sum() / r.sum())


def precision(pred, ref) -> float:
    p, r = _binimg(pred), _binimg(ref)
    if p.sum() == 0:
        return float("nan")
    return float(np.logical_and(p, r).sum() / p.sum())


def volume_ml(mask, spacing_mm) -> float:
    voxel_ml = float(np.prod(spacing_mm)) / 1000.0
    return float(_binimg(mask).sum() * voxel_ml)


def volume_error(pred, ref, spacing_mm) -> tuple[float, float]:
    vp, vr = volume_ml(pred, spacing_mm), volume_ml(ref, spacing_mm)
    abs_err = abs(vp - vr)
    rel_err = abs_err / vr if vr > 0 else float("nan")
    return abs_err, rel_err


def _surface_distances(pred, ref, spacing_mm):
    from scipy import ndimage
    p, r = _binimg(pred), _binimg(ref)
    if p.sum() == 0 or r.sum() == 0:
        return None
    # surface = voxels adjacent to background
    def surface(m):
        er = ndimage.binary_erosion(m)
        return m & ~er
    sp, sr = surface(p), surface(r)
    dt_r = ndimage.distance_transform_edt(~sr, sampling=spacing_mm)
    dt_p = ndimage.distance_transform_edt(~sp, sampling=spacing_mm)
    d_p2r = dt_r[sp]   # distances from pred surface to ref surface
    d_r2p = dt_p[sr]
    return np.concatenate([d_p2r, d_r2p]), d_p2r, d_r2p


def hd95(pred, ref, spacing_mm) -> float:
    sd = _surface_distances(pred, ref, spacing_mm)
    if sd is None:
        return float("nan")
    alld, dp, dr = sd
    return float(max(np.percentile(dp, 95), np.percentile(dr, 95)))


def assd(pred, ref, spacing_mm) -> float:
    sd = _surface_distances(pred, ref, spacing_mm)
    if sd is None:
        return float("nan")
    alld, dp, dr = sd
    return float(alld.mean())


def compare(pred, ref, spacing_mm) -> dict:
    """Full metric bundle for identical structures. Caller must confirm the
    label map is comparison_allowed before calling."""
    abs_e, rel_e = volume_error(pred, ref, spacing_mm)
    return {
        "dice": round(dice(pred, ref), 4),
        "jaccard": round(jaccard(pred, ref), 4),
        "sensitivity": round(sensitivity(pred, ref), 4),
        "precision": round(precision(pred, ref), 4),
        "hd95_mm": round(hd95(pred, ref, spacing_mm), 3),
        "assd_mm": round(assd(pred, ref, spacing_mm), 3),
        "abs_volume_error_ml": round(abs_e, 3),
        "rel_volume_error": round(rel_e, 4),
    }
