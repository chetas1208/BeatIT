"""Per-case CT + echo modality mapping (matched external, phenotype-coherent)."""

from __future__ import annotations

from python.hearttwin.careguard.imaging import modality_map


def test_echo_never_claims_same_subject():
    echo = modality_map.map_echo("case-000018", ["Heart failure"])
    if echo.get("available"):
        assert echo["same_subject_as_clinical_record"] is False
        assert echo["linkage_type"] == "matched_external_research_modality"
        assert "NOT the same individual" in echo["label"]


def test_echo_matches_reduced_ef_for_hfref():
    echo = modality_map.map_echo("case-000018", ["Heart failure with reduced ejection fraction", "cardiomyopathy"])
    if echo.get("available"):
        assert echo["derived_measurements"]["ejection_fraction_pct"] <= 45
        assert echo["match_features"]["expected_ef_band"].startswith("reduced")


def test_echo_matches_normal_ef_for_no_hf():
    echo = modality_map.map_echo("case-000999", [])
    if echo.get("available"):
        assert echo["derived_measurements"]["ejection_fraction_pct"] >= 50


def test_echo_assignment_deterministic():
    a = modality_map.map_echo("case-abc", ["Heart failure"])
    b = modality_map.map_echo("case-abc", ["Heart failure"])
    if a.get("available"):
        assert a["source_record_id"] == b["source_record_id"]


def test_ct_map_never_same_subject():
    ct = modality_map.map_ct("case-000018")
    assert ct["same_subject_as_clinical_record"] is False
    assert ct["linkage_type"] in ("matched_external_research_modality", "no_linked_ct")


def test_echo_derives_stroke_volume():
    echo = modality_map.map_echo("case-000018", ["Heart failure"])
    if echo.get("available"):
        dm = echo["derived_measurements"]
        assert abs(dm["stroke_volume_ml"] - (dm["end_diastolic_volume_ml"] - dm["end_systolic_volume_ml"])) < 0.1


def test_build_map_has_both_modalities_and_safety_note():
    mp = modality_map.build_imaging_map("case-000018", ["Heart failure"])
    assert "echocardiography" in mp and "ct" in mp
    assert "never fused into clinical reasoning" in mp["safety_note"]
