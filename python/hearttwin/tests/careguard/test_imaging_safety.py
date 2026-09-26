"""Safety + correctness tests for the CT imaging + VISTA extension (spec §27).

Covers the absolute linkage rule, fusion gating, segmentation metrics, and the
VISTA capability handshake. These are the load-bearing safety guarantees: no CT is
fused into a clinical case without independently verified same-subject linkage, and
demographic/phenotype/similarity matching is provably rejected.
"""
from __future__ import annotations

import numpy as np
import pytest

from python.hearttwin.careguard.imaging import linkage as L
from python.hearttwin.careguard.imaging import metrics as M


# --------------------------------------------------------------------------- #
# Linkage rule
# --------------------------------------------------------------------------- #
def _eval(method, native=False, sub="P1", clin="P1", access=True, vol=True):
    return L.evaluate_linkage(method=method, source_dataset="ds", source_subject_id=sub,
                              linked_clinical_subject_id=clin, access_approved=access,
                              has_actual_volume=vol, native_same_subject=native)


def test_native_same_subject_accepted():
    r = _eval("native_same_subject_dataset", native=True)
    assert r.status == L.IMAGING_NATIVE_SAME_SUBJECT
    assert r.same_subject_as_clinical_record is True
    assert L.is_fusion_allowed(r.status)


def test_official_mapping_same_subject_accepted():
    r = _eval("official_cross_dataset_mapping", sub="X9", clin="X9")
    assert r.status == L.SAME_SUBJECT_VERIFIED
    assert L.is_fusion_allowed(r.status)


@pytest.mark.parametrize("method", [
    "same_age", "same_sex", "same_diagnosis", "same_cardiac_category", "similar_labs",
    "similar_medications", "nearest_neighbor", "embedding", "matching_phenotype",
    "matching_ecg_class", "same_hospital_type", "random_assignment",
    "model_generated_matching", "filename_similarity"])
def test_prohibited_methods_rejected(method):
    r = _eval(method)
    assert r.status == L.PROHIBITED
    assert r.linkage_confidence == "prohibited"
    assert not L.is_fusion_allowed(r.status)


def test_unrelated_subject_ids_not_verified():
    # valid method but subject ids differ -> not same_subject_verified
    r = _eval("official_cross_dataset_mapping", sub="A", clin="B")
    assert r.status == L.IMAGING_ONLY
    assert not L.is_fusion_allowed(r.status)


def test_missing_volume_is_no_linked_ct():
    r = _eval("official_cross_dataset_mapping", vol=False)
    assert r.status == L.NO_LINKED_CT
    assert not L.is_fusion_allowed(r.status)


def test_access_pending_when_not_approved():
    r = _eval("official_cross_dataset_mapping", access=False)
    assert r.status == L.ACCESS_PENDING
    assert not L.is_fusion_allowed(r.status)


def test_imaging_only_fusion_rejected():
    allowed, msg = L.assert_fusion_permitted({"status": L.IMAGING_ONLY})
    assert allowed is False
    assert "same-subject linkage has not been verified" in msg


def test_verified_fusion_permitted():
    allowed, _ = L.assert_fusion_permitted({"status": L.SAME_SUBJECT_VERIFIED})
    assert allowed is True


# --------------------------------------------------------------------------- #
# Segmentation metrics
# --------------------------------------------------------------------------- #
def test_identical_masks_dice_one():
    a = np.zeros((10, 10, 10), dtype=np.uint8)
    a[2:8, 2:8, 2:8] = 1
    assert M.dice(a, a) == pytest.approx(1.0)
    assert M.jaccard(a, a) == pytest.approx(1.0)


def test_non_overlapping_masks_dice_zero():
    a = np.zeros((10, 10, 10), dtype=np.uint8); a[0:3] = 1
    b = np.zeros((10, 10, 10), dtype=np.uint8); b[7:10] = 1
    assert M.dice(a, b) == pytest.approx(0.0)


def test_both_empty_masks_dice_one():
    z = np.zeros((5, 5, 5), dtype=np.uint8)
    assert M.dice(z, z) == pytest.approx(1.0)


def test_empty_prediction_vs_nonempty_ref():
    pred = np.zeros((6, 6, 6), dtype=np.uint8)
    ref = np.zeros((6, 6, 6), dtype=np.uint8); ref[1:4, 1:4, 1:4] = 1
    assert M.dice(pred, ref) == pytest.approx(0.0)
    assert M.sensitivity(pred, ref) == pytest.approx(0.0)


def test_spacing_used_in_distance():
    a = np.zeros((10, 10, 10), dtype=np.uint8); a[2:8, 2:8, 2:8] = 1
    b = np.zeros((10, 10, 10), dtype=np.uint8); b[3:9, 2:8, 2:8] = 1
    d_iso = M.hd95(a, b, (1.0, 1.0, 1.0))
    d_aniso = M.hd95(a, b, (3.0, 1.0, 1.0))
    assert d_aniso > d_iso  # larger z-spacing scales distances


def test_volume_error_scales_with_spacing():
    m = np.zeros((10, 10, 10), dtype=np.uint8); m[0:5, 0:5, 0:5] = 1  # 125 voxels
    vol = M.volume_ml(m, (2.0, 2.0, 2.0))  # 125 * 8mm3 = 1000mm3 = 1mL
    assert vol == pytest.approx(1.0, rel=1e-6)


# --------------------------------------------------------------------------- #
# VISTA capability handshake (gated)
# --------------------------------------------------------------------------- #
def test_capability_handshake_gated(monkeypatch):
    monkeypatch.delenv("VISTA3D_API_BASE", raising=False)
    monkeypatch.setenv("VISTA3D_ENABLED", "false")
    from python.hearttwin.careguard.imaging import vista_endpoint_adapter as A
    caps = A.discover_capabilities_sync()
    assert caps.reachable is False
    assert caps.source == "static_fallback"
    # never claims coronary / EAT / PAT
    lc = [c.lower() for c in caps.supported_classes]
    assert "coronary arteries" not in lc
    assert "epicardial adipose tissue" not in lc


def test_unsupported_class_not_requested():
    from python.hearttwin.careguard.imaging import vista_endpoint_adapter as A
    from python.hearttwin.careguard.imaging.schemas import EndpointCapabilities
    caps = EndpointCapabilities(supported_classes=["heart", "aorta"])
    acc, rej, warns = A.resolve_requested_classes(
        ["heart", "coronary arteries", "left ventricle", "liver"], caps)
    assert acc == ["heart"]
    assert "coronary arteries" in rej and "left ventricle" in rej


def test_no_invented_confidence_in_structure_result():
    from python.hearttwin.careguard.imaging.schemas import VistaStructureResult
    r = VistaStructureResult(structure_id="heart", requested_label="heart",
                             endpoint_label="heart", status="not_found")
    assert r.confidence is None  # never invented from mask size
    assert "clinician review" in r.label
