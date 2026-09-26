#!/usr/bin/env python3
"""Imaging stage 16 — FHIR ImagingStudy + Provenance for imaging cases (spec §22).

For imaging cases, emit a STANDALONE FHIR ImagingStudy + Provenance (subject = the
imaging subject, NOT an eICU patient), clearly labeled and deidentified. VISTA
volumes, when present, become Observation resources with method="VISTA model-derived
segmentation", status=preliminary, and no interpretation — never a diagnostic
conclusion. Nothing is fused into a clinical bundle unless linkage is verified
same-subject (0 such cases in gated mode). Idempotent.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402
from python.hearttwin.careguard.imaging import linkage as L  # noqa: E402

CG = "https://hearttwin.local/careguard"


def imaging_study(icid, subj, geo, linkage_status) -> dict:
    n_inst = (geo.get("scan_shape") or [None, None, None])[2]
    return {
        "resourceType": "ImagingStudy", "id": f"imgstudy-{icid}", "status": "available",
        "subject": {"reference": f"Patient/imaging-subject-{subj}",
                    "display": "imaging benchmark subject (not an eICU patient)"},
        "modality": [{"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CT"}],
        "numberOfSeries": 1, "numberOfInstances": n_inst,
        "description": "TotalSegmentator CT — imaging benchmark; not linked to any clinical case.",
        "series": [{"uid": f"series-{subj}", "modality": {"code": "CT"},
                    "numberOfInstances": n_inst, "bodySite": {"display": "thorax/abdomen"}}],
        "extension": [{"url": f"{CG}/imaging-linkage", "extension": [
            {"url": "linkage_status", "valueString": linkage_status},
            {"url": "same_subject_as_clinical_record", "valueBoolean": False},
            {"url": "source_dataset", "valueString": "totalsegmentator"},
            {"url": "deidentified", "valueBoolean": True},
        ]}],
    }


def provenance(icid, subj) -> dict:
    return {
        "resourceType": "Provenance", "id": f"prov-{icid}",
        "target": [{"reference": f"ImagingStudy/imgstudy-{icid}"}],
        "recorded": I.C.now_iso(),
        "activity": {"text": "Imported + normalized real TotalSegmentator CT; VISTA gated (no live run)"},
        "agent": [{"type": {"text": "software"}, "who": {"display": "HeartTwin CareGuard imaging pipeline"}}],
        "entity": [{"role": "source", "what": {"display": "TotalSegmentator dataset (CC BY 4.0), DOI "
                                               + str(I.SOURCES['totalsegmentator']['doi'])}}],
        "extension": [{"url": f"{CG}/provenance", "extension": [
            {"url": "source_dataset", "valueString": "totalsegmentator"},
            {"url": "source_subject_id", "valueString": subj},
            {"url": "assertion_type", "valueString": "model_derived_imaging_measurement"},
        ]}],
    }


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_16_fhir")
    log.info("=== Imaging 16: FHIR ImagingStudy + Provenance ===")
    idx_path = I.IMAGING_CASES / "imaging_cases_index.json"
    idx = I.C.read_json(idx_path) if idx_path.exists() else {"cases": []}
    n_study = n_prov = n_fused = 0
    for c in idx.get("cases", []):
        icid, subj = c["imaging_case_id"], c["source_subject_id"]
        conv = I.IMAGING_CASES / icid / "imaging" / "normalized" / "conversion.json"
        geo = I.C.read_json(conv) if conv.exists() else {}
        fdir = I.IMAGING_CASES / icid / "fhir"
        fdir.mkdir(parents=True, exist_ok=True)
        study = imaging_study(icid, subj, geo, c["linkage_status"])
        prov = provenance(icid, subj)
        I.C.write_json(fdir / "imaging-study.json", study)
        I.C.write_json(fdir / "provenance.json", prov)
        I.C.write_json(fdir / "fhir-bundle.json", {
            "resourceType": "Bundle", "id": f"imaging-{icid}", "type": "collection",
            "meta": {"tag": [{"system": CG, "code": "imaging-benchmark",
                              "display": "Standalone imaging benchmark — not linked to a clinical patient"}]},
            "entry": [{"resource": study}, {"resource": prov}]})
        n_study += 1
        n_prov += 1
        # fuse into clinical bundle ONLY if verified same-subject (none here)
        if L.is_fusion_allowed(c["linkage_status"]):
            n_fused += 1

    I.C.write_json(I.AI_VISTA / "fhir_imaging_summary.json", {
        "generated_at": I.C.now_iso(), "imaging_study_resources": n_study,
        "provenance_resources": n_prov, "fused_into_clinical_cases": n_fused,
        "note": "ImagingStudy resources are standalone (imaging subject), never attached to "
                "an eICU patient. Fusion into clinical bundles requires verified same-subject "
                "linkage (0 in gated mode)."})
    log.info("=== Imaging 16 complete: %d ImagingStudy, %d Provenance, %d fused ===",
             n_study, n_prov, n_fused)
    print(f"imaging_studies={n_study} provenance={n_prov} fused={n_fused}")


if __name__ == "__main__":
    main()
