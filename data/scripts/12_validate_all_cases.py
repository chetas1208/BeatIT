#!/usr/bin/env python3
"""Stage 12 — validate every packaged case (spec §15).

Asserts directory/format presence, parseability of every format, ECG/DICOM/PDF
loadability, FHIR structural validity, provenance coverage, absence of PHI, the
ECG donor warning, that same-patient linkage is never claimed, the safety
disclaimer, and source license + identifier. Invalid cases are moved to
quarantine/. Writes analysis/validation_failures.csv and validation_summary.json.
"""
from __future__ import annotations

import csv
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import fhir_build as FB  # noqa: E402

# Optional: validate against the REAL CareGuard ingestion validator when the app
# package is importable. Proves genuine ingestion compatibility; skipped otherwise.
_CAREGUARD_VALIDATE = None
try:
    sys.path.insert(0, str(C.REPO_ROOT / "python"))
    from hearttwin.careguard.fhir import bundle_validator as _bv  # type: ignore
    _CAREGUARD_VALIDATE = _bv.validate_bundle
except Exception:
    _CAREGUARD_VALIDATE = None

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")
PHI_PATIENT_KEYS = {"name", "address", "telecom", "identifier"}
REQUIRED = {
    "": ["README.md", "manifest.json", "provenance.json", "quality.json"],
    "clinical": ["fhir-bundle.json", "fhir-resources.ndjson", "patient-summary.json",
                 "patient-summary.yaml", "patient-summary.csv", "patient-summary.parquet",
                 "patient-report.txt", "patient-report.pdf", "ccda.xml"],
    "ehr": ["patient.csv", "diagnoses.csv", "medications.csv", "allergies.csv",
            "labs.csv", "vitals.csv", "treatments.csv", "notes.csv", "past-history.csv"],
    "medication-evidence": ["normalized-medications.json", "label-evidence.json",
                            "unresolved-medications.json"],
    "analysis": ["organ-profile.json", "cardiovascular-profile.json",
                 "multimorbidity-profile.json", "timeline.json", "completeness.json"],
}


def validate_case(cdir: Path, cfg) -> list[str]:
    import pandas as pd
    import yaml
    from lxml import etree
    issues = []

    def need(p):
        if not p.exists():
            issues.append(f"missing {p.relative_to(cdir)}")
            return False
        if p.stat().st_size == 0:
            issues.append(f"empty {p.relative_to(cdir)}")
            return False
        return True

    for sub, files in REQUIRED.items():
        for f in files:
            need(cdir / sub / f if sub else cdir / f)

    # JSON parse
    bundle = None
    for jp in list(cdir.glob("*.json")) + list((cdir / "clinical").glob("*.json")) + \
            list((cdir / "analysis").glob("*.json")) + list((cdir / "medication-evidence").glob("*.json")):
        try:
            obj = C.read_json(jp)
            if jp.name == "fhir-bundle.json":
                bundle = obj
        except Exception as e:
            issues.append(f"json parse {jp.name}: {e}")

    # YAML / CSV / Parquet / XML / PDF
    try:
        yaml.safe_load((cdir / "clinical" / "patient-summary.yaml").read_text())
    except Exception as e:
        issues.append(f"yaml parse: {e}")
    for cp in (cdir / "ehr").glob("*.csv"):
        try:
            pd.read_csv(cp)
        except Exception as e:
            issues.append(f"csv parse {cp.name}: {e}")
    try:
        pd.read_parquet(cdir / "clinical" / "patient-summary.parquet")
    except Exception as e:
        issues.append(f"parquet parse: {e}")
    try:
        etree.parse(str(cdir / "clinical" / "ccda.xml"))
    except Exception as e:
        issues.append(f"xml parse: {e}")
    pdf = cdir / "clinical" / "patient-report.pdf"
    if pdf.exists() and not pdf.read_bytes()[:5].startswith(b"%PDF"):
        issues.append("pdf not a valid PDF")

    # FHIR structural
    if bundle is None:
        issues.append("no fhir bundle to validate")
    else:
        ok, bissues = FB.validate_bundle_struct(bundle)
        if not ok:
            issues.append("fhir invalid: " + "; ".join(bissues[:4]))
        # real CareGuard ingestion validator (optional)
        if _CAREGUARD_VALIDATE is not None:
            try:
                res = _CAREGUARD_VALIDATE(bundle)
                if not getattr(res, "valid", False):
                    issues.append("careguard validate_bundle rejected: "
                                  + "; ".join(getattr(res, "issues", [])[:4]))
            except Exception as e:
                issues.append(f"careguard validator error: {e}")
        # provenance coverage: every clinical fact resource carries provenance ext
        clinical_rt = {"Condition", "Observation", "MedicationStatement", "AllergyIntolerance",
                       "Procedure"}
        for e in bundle.get("entry", []):
            r = e.get("resource", {})
            if r.get("resourceType") in clinical_rt:
                if not any(x.get("url", "").endswith("/provenance")
                           for x in (r.get("extension") or [])):
                    issues.append(f"resource {r.get('id')} missing provenance"); break
        # PHI: Patient must not carry PHI keys
        for e in bundle.get("entry", []):
            r = e.get("resource", {})
            if r.get("resourceType") == "Patient":
                for k in PHI_PATIENT_KEYS:
                    if k in r:
                        issues.append(f"PHI key '{k}' in Patient")
        # no email / phone anywhere in the bundle text
        btxt = C.read_json(cdir / "clinical" / "fhir-bundle.json") and \
            (cdir / "clinical" / "fhir-bundle.json").read_text()
        if EMAIL.search(btxt):
            issues.append("email pattern in bundle")
        if PHONE.search(btxt):
            issues.append("phone pattern in bundle")

    # ECG (if present in manifest)
    manifest = C.read_json(cdir / "manifest.json") if (cdir / "manifest.json").exists() else {}
    if manifest.get("ecg_source") == "PTB-XL":
        ecgd = cdir / "ecg"
        for f in ("ecg.hea", "ecg.dat", "ecg.csv", "ecg.png", "ecg-secondary-capture.dcm",
                  "ecg-provenance.json"):
            need(ecgd / f)
        try:
            import wfdb
            rec = wfdb.rdrecord(str(ecgd / "ecg"))
            if rec.p_signal is None or rec.p_signal.shape[0] < 100 or rec.p_signal.shape[1] != 12:
                issues.append("ecg waveform shape unexpected")
        except Exception as e:
            issues.append(f"ecg wfdb load: {e}")
        try:
            rows = sum(1 for _ in open(ecgd / "ecg.csv")) - 1
            if not (500 <= rows <= 20000):
                issues.append(f"ecg csv length {rows} out of range")
        except Exception as e:
            issues.append(f"ecg csv read: {e}")
        try:
            from PIL import Image
            Image.open(ecgd / "ecg.png").verify()
        except Exception as e:
            issues.append(f"ecg png open: {e}")
        try:
            import pydicom
            ds = pydicom.dcmread(str(ecgd / "ecg-secondary-capture.dcm"))
            if "Not a clinical diagnostic image" not in (ds.get("ImageComments", "") or ""):
                issues.append("DICOM missing not-clinical statement")
        except Exception as e:
            issues.append(f"dicom parse: {e}")
        # donor warning + no same-patient claim
        prov = C.read_json(ecgd / "ecg-provenance.json") if (ecgd / "ecg-provenance.json").exists() else {}
        warn = (prov.get("warning") or "").lower()
        if not ("different deidentified individuals" in warn
                or "does not originate from the same individual" in warn):
            issues.append("ecg donor warning missing")
        if prov.get("same_patient_as_ehr") is not False:
            issues.append("ecg same_patient_as_ehr not False")
        if manifest.get("same_patient_as_ehr") is not False:
            issues.append("manifest same_patient_as_ehr not False")

    # Echo (if present in manifest) — matched external modality, never same-subject
    if manifest.get("echo_source") == "EchoNet-Dynamic":
        echod = cdir / "echo"
        for f in ("echo.avi", "echo-frame.png", "echo.gif", "echo.json", "echo-provenance.json"):
            need(echod / f)
        if manifest.get("echo_same_patient_as_ehr") is not False:
            issues.append("echo same_patient_as_ehr not False in manifest")
        eprov = C.read_json(echod / "echo-provenance.json") if (echod / "echo-provenance.json").exists() else {}
        if eprov.get("same_patient_as_ehr") is not False:
            issues.append("echo provenance same_patient_as_ehr not False")
        if "does not originate from the same individual" not in (eprov.get("warning") or "").lower():
            issues.append("echo donor warning missing")
        ejson = C.read_json(echod / "echo.json") if (echod / "echo.json").exists() else {}
        if "not the eicu patient" not in str(ejson.get("donor_measurements", {})).lower():
            issues.append("echo donor measurements not labeled as donor's")
        try:
            from PIL import Image
            Image.open(echod / "echo-frame.png").verify()
        except Exception as e:
            issues.append(f"echo frame open: {e}")

    # safety disclaimer present in report + README
    rpt = (cdir / "clinical" / "patient-report.txt")
    if rpt.exists() and "Not for diagnosis or treatment" not in rpt.read_text():
        issues.append("safety disclaimer missing in report")
    readme = cdir / "README.md"
    if readme.exists() and "software testing" not in readme.read_text().lower():
        issues.append("composite disclaimer missing in README")

    # source license + identifier
    if not manifest.get("license"):
        issues.append("source license missing in manifest")
    if not manifest.get("source_identifier"):
        issues.append("source identifier missing in manifest")

    return issues


def main() -> None:
    C.ensure_dirs()
    log = C.get_logger("12_validate_all_cases")
    cfg = C.load_config()
    log.info("=== Stage 12: validate all cases ===")
    case_dirs = sorted([d for d in C.CASES.glob("case-*") if d.is_dir()])
    log.info("validating %d case directories", len(case_dirs))

    rows, quarantined, valid = [], 0, 0
    for i, cdir in enumerate(case_dirs, 1):
        try:
            issues = validate_case(cdir, cfg)
        except Exception as e:
            issues = [f"validator exception: {e}"]
        if issues:
            rows.append({"case_id": cdir.name, "n_issues": len(issues),
                         "issues": " | ".join(issues[:12])})
            dest = C.QUARANTINE / cdir.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(cdir), str(dest))
            quarantined += 1
            log.warning("QUARANTINED %s: %s", cdir.name, issues[:3])
        else:
            valid += 1
        if i % 200 == 0:
            log.info("validated %d/%d (%d valid, %d quarantined)", i, len(case_dirs), valid, quarantined)

    with open(C.ANALYSIS / "validation_failures.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["case_id", "n_issues", "issues"])
        w.writeheader(); w.writerows(rows)
    C.write_json(C.ANALYSIS / "validation_summary.json", {
        "generated_at": C.now_iso(), "validated": len(case_dirs),
        "valid": valid, "quarantined": quarantined,
        "pass_rate": round(valid / max(len(case_dirs), 1), 4)})
    log.info("=== Stage 12 complete: %d valid, %d quarantined ===", valid, quarantined)
    print(f"valid={valid} quarantined={quarantined}")


if __name__ == "__main__":
    main()
