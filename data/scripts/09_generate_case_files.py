#!/usr/bin/env python3
"""Stage 09 — materialize every per-case directory with the full format contract.

Reads assembled records (04), FHIR bundles (08), ECG cache (06), and medication
normalization (07); writes cases/<case_id>/ with clinical/ ehr/ ecg/
medication-evidence/ analysis/ plus manifest/provenance/quality/README.
Idempotent: files are overwritten in place.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import case_writer as W  # noqa: E402
import quality as Q  # noqa: E402

ASM = C.STAGING / "assembled"
FHIR_OUT = C.STAGING / "fhir"
ECG_CACHE = C.CACHE / "ecg"
ECHO_CACHE = C.CACHE / "echo"


def load_meds():
    p = C.STAGING / "medication-normalization" / "normalized.json"
    return C.read_json(p) if p.exists() else {}


def _load_assignments(name):
    import pandas as pd
    p = C.COHORT / name
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    out = {}
    for _, r in df.iterrows():
        d = {k: (None if pd.isna(r[k]) else r[k]) for k in df.columns}
        d["assigned"] = bool(d.get("assigned"))
        out[r["case_id"]] = d
    return out


def load_ecg():
    return _load_assignments("ecg_assignments.csv")


def load_echo():
    return _load_assignments("echo_assignments.csv")


def write_case(cid, cfg, meds, ecg_map, log, echo_map=None):
    import pandas as pd
    import yaml
    echo_map = echo_map or {}
    asm = C.read_json(ASM / f"{cid}.json")
    bundle_path = FHIR_OUT / f"{cid}.json"
    bundle = C.read_json(bundle_path) if bundle_path.exists() else {"entry": []}
    fhir_meta = C.read_json(FHIR_OUT / f"{cid}.meta.json") if (FHIR_OUT / f"{cid}.meta.json").exists() else {}
    ecg = ecg_map.get(cid, {"assigned": False})
    echo = echo_map.get(cid, {"assigned": False})

    cdir = C.CASES / cid
    clinical = cdir / "clinical"
    ehr = cdir / "ehr"
    ecgd = cdir / "ecg"
    echod = cdir / "echo"
    medev = cdir / "medication-evidence"
    analysis = cdir / "analysis"
    for d in (clinical, ehr, ecgd, echod, medev, analysis):
        d.mkdir(parents=True, exist_ok=True)

    # quality
    q = Q.compute_case_quality(asm, fhir_meta, ecg.get("assigned"), bundle)

    # clinical/
    shutil.copyfile(bundle_path, clinical / "fhir-bundle.json") if bundle_path.exists() else None
    C.write_ndjson(clinical / "fhir-resources.ndjson", [e["resource"] for e in bundle.get("entry", [])])
    summ = W.patient_summary(asm, fhir_meta, ecg, q)
    C.write_json(clinical / "patient-summary.json", summ)
    (clinical / "patient-summary.yaml").write_text(yaml.safe_dump(summ, sort_keys=False))
    flat = W.summary_flat_row(asm, fhir_meta, ecg, q)
    pd.DataFrame([flat]).to_csv(clinical / "patient-summary.csv", index=False)
    pd.DataFrame([flat]).to_parquet(clinical / "patient-summary.parquet", index=False)
    rpt = W.report_text(asm, cfg, ecg, q, echo=echo)
    (clinical / "patient-report.txt").write_text(rpt)
    W.write_pdf(rpt, clinical / "patient-report.pdf")
    (clinical / "ccda.xml").write_bytes(W.ccda_xml(asm, cfg))

    # ehr/
    W.write_ehr_csvs(asm, ehr)

    # ecg/
    if ecg.get("assigned") and (ECG_CACHE / str(int(float(ecg["ecg_record_id"])))).exists():
        src = ECG_CACHE / str(int(float(ecg["ecg_record_id"])))
        for f in ("ecg.hea", "ecg.dat", "ecg.csv", "ecg.json", "ecg.png"):
            if (src / f).exists():
                shutil.copyfile(src / f, ecgd / f)
        if (ecgd / "ecg.png").exists():
            try:
                W.write_dicom_sc(ecgd / "ecg.png", ecgd / "ecg-secondary-capture.dcm", cfg, ecg, asm)
            except Exception as e:
                log.warning("%s: DICOM SC failed: %s", cid, e)
        C.write_json(ecgd / "ecg-provenance.json", {
            "ecg_source": "PTB-XL", "ecg_record_id": str(ecg.get("ecg_record_id")),
            "linkage_type": "matched_external_modality", "same_patient_as_ehr": False,
            "match_features": (ecg.get("match_features") or "").split("|") if ecg.get("match_features") else [],
            "warning": cfg["disclaimers"]["ecg_donor"],
            "sampling_rate_hz": ecg.get("sampling_rate_hz"), "n_samples": ecg.get("n_samples"),
            "duration_seconds": ecg.get("duration_seconds"),
            "license": cfg["sources"]["ptbxl"]["license"]})

    # echo/ (matched external modality — EchoNet-Dynamic; NOT the eICU patient)
    if echo.get("assigned") and (ECHO_CACHE / str(echo["echo_id"])).exists():
        src = ECHO_CACHE / str(echo["echo_id"])
        for f in ("echo.avi", "echo-frame.png", "echo.gif", "echo.json", "echo-provenance.json"):
            if (src / f).exists():
                shutil.copyfile(src / f, echod / f)

    # medication-evidence/
    norm_out, labels, unresolved = W.medication_evidence(asm, meds)
    C.write_json(medev / "normalized-medications.json", norm_out)
    C.write_json(medev / "label-evidence.json", labels)
    C.write_json(medev / "unresolved-medications.json", unresolved)

    # analysis/
    organ_p, cv_p, mm_p, timeline = W.profiles(asm, ecg)
    C.write_json(analysis / "organ-profile.json", organ_p)
    C.write_json(analysis / "cardiovascular-profile.json", cv_p)
    C.write_json(analysis / "multimorbidity-profile.json", mm_p)
    C.write_json(analysis / "timeline.json", timeline)
    C.write_json(analysis / "completeness.json", q)

    # root files
    C.write_json(cdir / "quality.json", q)
    files = {
        "clinical": ["fhir-bundle.json", "fhir-resources.ndjson", "patient-summary.json",
                     "patient-summary.yaml", "patient-summary.csv", "patient-summary.parquet",
                     "patient-report.txt", "patient-report.pdf", "ccda.xml"],
        "ehr": ["patient.csv", "diagnoses.csv", "past-history.csv", "medications.csv",
                "allergies.csv", "labs.csv", "vitals.csv", "treatments.csv", "notes.csv"],
        "ecg": (["ecg.hea", "ecg.dat", "ecg.csv", "ecg.json", "ecg.png",
                 "ecg-secondary-capture.dcm", "ecg-provenance.json"] if ecg.get("assigned") else []),
        "echo": (["echo.avi", "echo-frame.png", "echo.gif", "echo.json", "echo-provenance.json"]
                 if echo.get("assigned") else []),
        "medication-evidence": ["normalized-medications.json", "label-evidence.json",
                                "unresolved-medications.json"],
        "analysis": ["organ-profile.json", "cardiovascular-profile.json",
                     "multimorbidity-profile.json", "timeline.json", "completeness.json"],
    }
    C.write_json(cdir / "manifest.json", W.manifest(asm, cfg, ecg, fhir_meta, files, echo=echo))
    C.write_json(cdir / "provenance.json", W.provenance(asm, cfg))
    (cdir / "README.md").write_text(W.readme(asm, cfg, ecg, echo=echo))
    return q["overall_completeness_score"]


def main() -> None:
    import pandas as pd
    C.ensure_dirs()
    log = C.get_logger("09_generate_case_files")
    cfg = C.load_config()
    log.info("=== Stage 09: generate case files ===")
    sel = pd.read_csv(C.STAGING / "eicu" / "cohort_selection.csv")
    for a in sys.argv:
        if a.startswith("--limit="):
            sel = sel.head(int(a.split("=", 1)[1]))
    meds = load_meds()
    ecg_map = load_ecg()
    echo_map = load_echo()
    log.info("cases=%d meds=%d ecg=%d echo=%d", len(sel), len(meds),
             sum(1 for v in ecg_map.values() if v.get("assigned")),
             sum(1 for v in echo_map.values() if v.get("assigned")))

    scores = []
    for i, cid in enumerate(sel["case_id"], 1):
        try:
            scores.append(write_case(cid, cfg, meds, ecg_map, log, echo_map=echo_map))
        except Exception as e:
            log.error("case %s failed: %s", cid, e)
            raise
        if i % 100 == 0:
            log.info("packaged %d/%d cases", i, len(sel))
    C.write_json(C.STAGING / "case_build_summary.json", {
        "generated_at": C.now_iso(), "cases": len(scores),
        "mean_completeness": round(sum(scores) / max(len(scores), 1), 4)})
    log.info("=== Stage 09 complete: %d cases, mean completeness %.3f ===",
             len(scores), sum(scores) / max(len(scores), 1))
    print(f"cases_packaged={len(scores)}")


if __name__ == "__main__":
    main()
