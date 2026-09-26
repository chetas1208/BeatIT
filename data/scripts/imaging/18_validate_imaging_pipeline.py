#!/usr/bin/env python3
"""Imaging stage 18 — end-to-end validation of the imaging extension (spec §31).

Asserts the acceptance criteria and emits a verdict. The strongest claim the
pipeline is allowed to make is bounded by what actually ran (gated VISTA, no
same-subject CT for eICU). Writes analysis/imaging/imaging_pipeline_validation.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _imaging as I  # noqa: E402
from python.hearttwin.careguard.imaging import linkage as L  # noqa: E402


def _load(p, d):
    return I.C.read_json(p) if Path(p).exists() else d


def main() -> None:
    I.ensure_dirs()
    log = I.C.get_logger("imaging_18_validate")
    log.info("=== Imaging 18: validate imaging pipeline ===")
    checks = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})
        log.info("[%s] %s %s", "PASS" if ok else "FAIL", name, detail)

    # 1. every clinical case has a ct_imaging status
    cases = sorted(I.CASES.glob("case-*"))
    stamped = 0
    bad_link = 0
    for cdir in cases:
        m = _load(cdir / "manifest.json", {})
        ct = m.get("ct_imaging")
        if ct and ct.get("status") in L.ALL_STATUSES:
            stamped += 1
            # no clinical case may claim same-subject without verification
            if ct.get("same_subject_as_clinical_record") and ct.get("status") not in L.FUSION_ALLOWED_STATUSES:
                bad_link += 1
    check("every clinical case has ct_imaging status", stamped == len(cases) and len(cases) > 0,
          f"{stamped}/{len(cases)}")
    check("no clinical case claims unverified same-subject CT", bad_link == 0, f"{bad_link} violations")

    # 2. audit found no prohibited pairings
    audit = _load(I.AI_LINKAGE / "existing_ct_audit_summary.json", {})
    check("no prohibited cross-dataset pairings", audit.get("prohibited_cross_dataset", 0) == 0)

    # 3. imaging cases: provenance + checksum + subject id + correct label
    imaging_idx = _load(I.IMAGING_CASES / "imaging_cases_index.json", {"cases": []})
    imcases = imaging_idx.get("cases", [])
    im_ok = 0
    for c in imcases:
        icid = c["imaging_case_id"]
        man = _load(I.IMAGING_CASES / icid / "manifest.json", {})
        src = _load(I.IMAGING_CASES / icid / "imaging" / "source" / "source-metadata.json", {})
        has_prov = (I.IMAGING_CASES / icid / "fhir" / "provenance.json").exists()
        if (man.get("source_subject_id") and src.get("sha256") and has_prov
                and man.get("ct_imaging", {}).get("status") == L.IMAGING_ONLY
                and man.get("ct_imaging", {}).get("same_subject_as_clinical_record") is False):
            im_ok += 1
    check("imaging cases have subject id + checksum + provenance + correct label",
          im_ok == len(imcases), f"{im_ok}/{len(imcases)}")

    # 4. MultiD4CAD access status recorded
    m4 = _load(I.RAW_MULTID4CAD / "import_summary.json", {})
    check("MultiD4CAD access status recorded", m4.get("status") in (L.ACCESS_PENDING, "ready_to_import"),
          m4.get("status", "missing"))

    # 5. DICOM + NIfTI validation passed
    dv = _load(I.ANALYSIS_IMAGING / "dicom_validation.json", {"series": []})
    check("DICOM validation passed", all(s.get("valid") for s in dv.get("series", [])) and dv.get("series"),
          f"{sum(1 for s in dv.get('series', []) if s.get('valid'))}/{len(dv.get('series', []))}")
    import csv as _csv
    nifti_ok = nifti_tot = 0
    nvp = I.ANALYSIS_IMAGING / "nifti_validation.csv"
    if nvp.exists():
        for r in _csv.DictReader(open(nvp)):
            nifti_tot += 1
            nifti_ok += 1 if r["valid"] in ("True", "true", True) else 0
    check("NIfTI validation passed", nifti_tot > 0 and nifti_ok == nifti_tot, f"{nifti_ok}/{nifti_tot}")

    # 6. VISTA capabilities queried + unsupported classes never requested
    caps = _load(I.STG_VISTA_JOBS / "capabilities.json", {})
    supported = {c.lower() for c in caps.get("supported_classes", [])}
    unsup_requested = 0
    confidence_invented = 0
    for jp in I.STG_VISTA_JOBS.glob("job-*.json"):
        j = _load(jp, {})
        for rc in j.get("requested_classes", []):
            if rc.lower() not in supported:
                unsup_requested += 1
    check("VISTA capabilities queried", bool(caps), caps.get("source", ""))
    check("no unsupported class requested", unsup_requested == 0, f"{unsup_requested} violations")
    # no invented confidence: gated jobs carry no confidence values
    for c in imcases:
        job = _load(I.IMAGING_CASES / c["imaging_case_id"] / "imaging" / "vista" / "job.json", {})
        if "confidence" in str(job.get("vista_result", {})):
            confidence_invented += 1
    check("no invented VISTA confidence", confidence_invented == 0)

    # 7. fusion gate: no verified fusion in gated mode + adversarial demo blocked
    fusion = _load(I.AI_FUSION / "fusion_report.json", {})
    demo = fusion.get("adversarial_prohibited_demo", {})
    check("no unverified fusion occurred", fusion.get("verified_fusions", 0) == 0,
          f"{fusion.get('blocked_fusions', 0)} blocked")
    check("adversarial demographic match blocked as prohibited",
          demo.get("resulting_status") == L.PROHIBITED and demo.get("fusion_allowed") is False)

    # 8. FHIR imaging resources valid (structural)
    fhir_ok = 0
    for c in imcases:
        st = _load(I.IMAGING_CASES / c["imaging_case_id"] / "fhir" / "imaging-study.json", {})
        pv = _load(I.IMAGING_CASES / c["imaging_case_id"] / "fhir" / "provenance.json", {})
        if st.get("resourceType") == "ImagingStudy" and pv.get("resourceType") == "Provenance":
            fhir_ok += 1
    check("FHIR ImagingStudy + Provenance valid", fhir_ok == len(imcases), f"{fhir_ok}/{len(imcases)}")

    # 9. existing 1000-case pipeline still intact
    val = _load(I.C.ANALYSIS / "validation_summary.json", {})
    check("existing clinical pipeline still valid", val.get("valid", 0) == len(cases) and len(cases) > 0,
          f"{val.get('valid', 0)} valid cases")

    all_pass = all(c["pass"] for c in checks)
    verdict = "VERIFIED CT/VISTA PIPELINE READY" if all_pass else "VERIFIED CT/VISTA PIPELINE NOT READY"
    I.C.write_json(I.ANALYSIS_IMAGING / "imaging_pipeline_validation.json", {
        "generated_at": I.C.now_iso(), "all_pass": all_pass, "verdict": verdict,
        "checks": checks,
        "note": "Readiness reflects the pipeline's linkage safety, real CT ingestion/validation, "
                "capability handshake, and fusion gating. Live VISTA segmentation is gated (no endpoint) "
                "and same-subject CT for eICU is unavailable — both are honestly reported, not faked."})
    log.info("=== Imaging 18 complete: %s (%d/%d checks pass) ===", verdict,
             sum(1 for c in checks if c["pass"]), len(checks))
    print(f"verdict={verdict} checks={sum(1 for c in checks if c['pass'])}/{len(checks)}")


if __name__ == "__main__":
    main()
