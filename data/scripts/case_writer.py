"""Builders for every per-case artifact (spec §10/§12).

Source-grounded only: nothing here adds diagnoses, doses, advice, or predictions.
Every human-readable artifact carries the mandatory research/composite/ECG-donor
disclaimers. No PHI is emitted (no names/addresses/phones/MRNs).
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

import _common as C


# --------------------------------------------------------------------------- #
# Structured summaries
# --------------------------------------------------------------------------- #
def patient_summary(asm, fhir_meta, ecg, quality):
    d = asm["demographics"]
    return {
        "case_id": asm["case_id"],
        "source_dataset": asm["source_dataset"],
        "source_type": asm.get("source_type", "real"),
        "real_patient_data": asm.get("real_patient_data", True),
        "demographics": {"age": d["age"], "age_band": d["age_band"], "gender": d["gender"],
                         "ethnicity": d["ethnicity"], "icu_type": d["unit_type"],
                         "icu_los_days": d["icu_los_days"],
                         "hospital_discharge_status": d["hospital_discharge_status"]},
        "cardiovascular_context": asm["cv_categories"],
        "noncardiac_organ_systems": asm["noncardiac_organ_systems"],
        "counts": {"diagnoses": len(asm["diagnoses"]), "medications": len(asm["medications"]),
                   "allergies": len(asm["allergies"]), "labs": len(asm["labs"]),
                   "treatments": asm["n_treatments"],
                   "fhir_resources": (fhir_meta or {}).get("total_resources")},
        "ecg": {"assigned": bool(ecg.get("assigned")),
                "record_id": ecg.get("ecg_record_id"), "source": "PTB-XL" if ecg.get("assigned") else None,
                "same_patient_as_ehr": False, "linkage_type": "matched_external_modality"},
        "overall_completeness_score": (quality or {}).get("overall_completeness_score"),
    }


def summary_flat_row(asm, fhir_meta, ecg, quality):
    d = asm["demographics"]
    q = quality or {}
    return {
        "case_id": asm["case_id"], "source_dataset": asm["source_dataset"],
        "source_type": asm.get("source_type", "real"),
        "real_patient_data": asm.get("real_patient_data", True),
        "age": d["age"], "age_band": d["age_band"], "gender": d["gender"],
        "icu_type": d["unit_type"], "icu_los_days": d["icu_los_days"],
        "discharge_status": d["hospital_discharge_status"],
        "cv_categories": "|".join(asm["cv_categories"]),
        "n_cv_categories": len(asm["cv_categories"]),
        "noncardiac_organs": "|".join(asm["noncardiac_organ_systems"]),
        "n_noncardiac_organs": len(asm["noncardiac_organ_systems"]),
        "n_diagnoses": len(asm["diagnoses"]), "n_medications": len(asm["medications"]),
        "n_allergies": len(asm["allergies"]), "n_labs": len(asm["labs"]),
        "n_treatments": asm["n_treatments"],
        "fhir_resources": (fhir_meta or {}).get("total_resources"),
        "fhir_valid": (fhir_meta or {}).get("valid"),
        "ecg_assigned": bool(ecg.get("assigned")), "ecg_record_id": ecg.get("ecg_record_id"),
        "overall_completeness_score": q.get("overall_completeness_score"),
    }


# --------------------------------------------------------------------------- #
# EHR CSV exports (full fidelity)
# --------------------------------------------------------------------------- #
def _write_csv(path, rows, fields):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_ehr_csvs(asm, ehr_dir: Path):
    ehr_dir.mkdir(parents=True, exist_ok=True)
    d = asm["demographics"]
    _write_csv(ehr_dir / "patient.csv", [{
        "case_id": asm["case_id"], "patientunitstayid": asm["patientunitstayid"],
        "age": d["age"], "age_band": d["age_band"], "gender": d["gender"],
        "ethnicity": d["ethnicity"], "icu_type": d["unit_type"],
        "unit_admit_source": d["unit_admit_source"],
        "hospital_admit_source": d["hospital_admit_source"],
        "admission_height_cm": d["admission_height_cm"],
        "admission_weight_kg": d["admission_weight_kg"], "icu_los_days": d["icu_los_days"],
        "hospital_discharge_status": d["hospital_discharge_status"],
        "unit_discharge_status": d["unit_discharge_status"]}],
        ["case_id", "patientunitstayid", "age", "age_band", "gender", "ethnicity",
         "icu_type", "unit_admit_source", "hospital_admit_source", "admission_height_cm",
         "admission_weight_kg", "icu_los_days", "hospital_discharge_status", "unit_discharge_status"])

    dx = [d for d in asm["diagnoses"] if d["source_table"] != "pastHistory"]
    ph = [d for d in asm["diagnoses"] if d["source_table"] == "pastHistory"]
    dxf = ["text", "icd_code", "priority", "clinical_status", "active_upon_discharge",
           "offset", "source_table", "source_row_id", "cv_categories", "organ_systems"]
    _write_csv(ehr_dir / "diagnoses.csv",
               [{**r, "cv_categories": "|".join(r["cv_categories"]),
                 "organ_systems": "|".join(r["organ_systems"])} for r in dx], dxf)
    _write_csv(ehr_dir / "past-history.csv",
               [{**r, "cv_categories": "|".join(r["cv_categories"]),
                 "organ_systems": "|".join(r["organ_systems"])} for r in ph], dxf)
    _write_csv(ehr_dir / "medications.csv", asm["medications"],
               ["text", "dosage", "route", "frequency", "start_offset", "stop_offset",
                "status", "source_table", "source_row_id"])
    _write_csv(ehr_dir / "allergies.csv", asm["allergies"],
               ["name", "type", "offset", "source_table", "source_row_id"])
    _write_csv(ehr_dir / "labs.csv", asm["labs"],
               ["labname", "canonical", "loinc", "group", "value", "text", "unit",
                "offset", "source_table", "source_row_id"])
    # vitals: summary + samples
    vrows = []
    for name, s in asm["vitals"]["summary"].items():
        vrows.append({"vital": name, "loinc": s.get("loinc"), "unit": s.get("unit"),
                      "count": s["count"], "min": s["min"], "max": s["max"], "mean": s["mean"]})
    _write_csv(ehr_dir / "vitals.csv", vrows, ["vital", "loinc", "unit", "count", "min", "max", "mean"])
    tx = [d for d in asm["diagnoses"] if d["source_table"] == "treatment"]
    _write_csv(ehr_dir / "treatments.csv", tx,
               ["text", "offset", "active_upon_discharge", "source_table", "source_row_id"])
    _write_csv(ehr_dir / "notes.csv", asm.get("notes", []),
               ["type", "offset", "value", "source_row_id"])


# --------------------------------------------------------------------------- #
# Human-readable report (TXT + PDF)
# --------------------------------------------------------------------------- #
def report_text(asm, cfg, ecg, quality, echo=None):
    echo = echo or {}
    dis = cfg["disclaimers"]
    d = asm["demographics"]
    L = []
    L.append("HeartTwin CareGuard — Composite Research Case Report")
    L.append("=" * 60)
    L.append(f"Case identifier : {asm['case_id']}")
    L.append(f"Source dataset  : {asm['source_dataset']} (real, deidentified ICU stay)")
    L.append("")
    L.append("*** " + dis["research_only"] + " ***")
    L.append("*** Not for diagnosis or treatment decisions. ***")
    L.append("*** " + dis["composite"] + " ***")
    L.append("This is a composite research case assembled from deidentified open "
             "datasets for software testing.")
    L.append("")
    L.append("PATIENT CONTEXT (deidentified)")
    L.append(f"  Age band        : {d['age_band']}   Sex: {d['gender']}   "
             f"Ethnicity: {d['ethnicity']}")
    L.append(f"  ICU type        : {d['unit_type']}   ICU LOS (days): {d['icu_los_days']}")
    L.append(f"  Discharge status: {d['hospital_discharge_status']}")
    L.append("")
    L.append("CARDIOVASCULAR CONTEXT (source-recorded)")
    L.append("  " + (", ".join(asm["cv_categories"]) or "none categorized"))
    L.append("")
    L.append("RECORDED COMORBIDITIES BY ORGAN SYSTEM (non-cardiac)")
    L.append("  " + (", ".join(asm["noncardiac_organ_systems"]) or "none"))
    L.append("")
    L.append(f"DIAGNOSES (recorded, showing up to 25 of {len(asm['diagnoses'])})")
    for dx in asm["diagnoses"][:25]:
        L.append(f"  - {dx['text']}  [{dx['source_table']}"
                 f"{'; ICD ' + dx['icd_code'] if dx.get('icd_code') else ''}]")
    L.append("")
    L.append(f"MEDICATIONS (recorded, up to 25 of {len(asm['medications'])})")
    for m in asm["medications"][:25]:
        L.append(f"  - {m['text']}"
                 f"{' | ' + str(m['dosage']) if m.get('dosage') else ''}"
                 f"{' | ' + str(m['route']) if m.get('route') else ''}")
    L.append("")
    L.append(f"ALLERGIES (recorded, up to 15 of {len(asm['allergies'])})")
    for a in asm["allergies"][:15]:
        L.append(f"  - {a['name']}")
    if not asm["allergies"]:
        L.append("  (none recorded — absence does NOT imply no allergies)")
    L.append("")
    L.append("SELECTED LABS (latest recorded values)")
    seen = set()
    for lb in sorted(asm["labs"], key=lambda x: -(int(x['offset']) if x.get('offset') and str(x['offset']).lstrip('-').isdigit() else 0)):
        if lb["canonical"] in seen or lb.get("value") is None:
            continue
        seen.add(lb["canonical"])
        L.append(f"  - {lb['canonical']}: {lb['value']} {lb.get('unit') or ''}")
        if len(seen) >= 20:
            break
    L.append("")
    L.append("SELECTED VITAL SIGNS (mean over recorded series)")
    for name, s in asm["vitals"]["summary"].items():
        L.append(f"  - {name}: mean {s['mean']} {s.get('unit') or ''} (n={s['count']})")
    L.append("")
    tx = [d for d in asm["diagnoses"] if d["source_table"] == "treatment"]
    L.append(f"TREATMENT HISTORY (recorded, up to 15 of {len(tx)})")
    for t in tx[:15]:
        L.append(f"  - {t['text']}")
    L.append("")
    L.append("ECG (external matched modality)")
    if ecg.get("assigned"):
        L.append(f"  PTB-XL record {ecg['ecg_record_id']} | superclass "
                 f"{ecg.get('ecg_primary_superclass')} | rhythm {ecg.get('ecg_rhythm') or 'n/a'}")
        L.append("  " + dis["ecg_donor"])
    else:
        L.append("  No external ECG assigned to this case.")
    L.append("")
    L.append("ECHOCARDIOGRAM (external matched modality)")
    if echo.get("assigned"):
        L.append(f"  EchoNet-Dynamic record {echo.get('echo_id')} | apical 4-chamber | "
                 f"donor EF {echo.get('donor_ef')}% (EDV {echo.get('donor_edv')} / ESV {echo.get('donor_esv')} mL)")
        L.append("  These are the ECHO DONOR's measurements, NOT the eICU patient's.")
        L.append("  " + echo.get("warning", ""))
    else:
        L.append("  No external echocardiogram assigned to this case.")
    L.append("")
    q = quality or {}
    L.append("DATA-QUALITY")
    L.append(f"  Overall completeness score: {q.get('overall_completeness_score')}")
    for w in q.get("missingness_warnings", []):
        L.append(f"  ! missing: {w}")
    L.append("")
    L.append("MISSING INFORMATION / LIMITATIONS")
    L.append("  - Missing data does NOT mean normal or ruled-out.")
    L.append("  - Modalities may originate from different deidentified individuals.")
    L.append("")
    L.append("SOURCE ATTRIBUTION")
    L.append("  eICU-CRD Demo 2.0.1 (PhysioNet, Open Database License).")
    if ecg.get("assigned"):
        L.append("  PTB-XL 1.0.1 (PhysioNet, CC BY 4.0) — ECG donor modality.")
    return "\n".join(L)


def write_pdf(text, path):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    x, y = 0.6 * inch, height - 0.6 * inch
    c.setFont("Helvetica", 8)
    for line in text.split("\n"):
        if y < 0.6 * inch:
            c.showPage(); c.setFont("Helvetica", 8); y = height - 0.6 * inch
        c.drawString(x, y, line[:120])
        y -= 10.5
    c.save()


# --------------------------------------------------------------------------- #
# C-CDA-style XML (deterministic export)
# --------------------------------------------------------------------------- #
def ccda_xml(asm, cfg):
    from lxml import etree
    NS = "urn:hl7-org:v3"
    root = etree.Element("{%s}ClinicalDocument" % NS, nsmap={None: NS})
    etree.SubElement(root, "{%s}typeId" % NS, root="2.16.840.1.113883.1.3",
                     extension="POCD_HD000040")
    title = etree.SubElement(root, "{%s}title" % NS)
    title.text = f"HeartTwin CareGuard Composite Research Case {asm['case_id']}"
    etree.SubElement(root, "{%s}confidentialityCode" % NS, code="N",
                     codeSystem="2.16.840.1.113883.5.25")
    note = etree.SubElement(root, "{%s}notesText" % NS)
    note.text = (cfg["disclaimers"]["research_only"] + " " + cfg["disclaimers"]["composite"]
                 + " Deterministic C-CDA export of a deidentified eICU record; no PHI.")
    # record target: gender + age band only (no PHI)
    rt = etree.SubElement(root, "{%s}recordTarget" % NS)
    pr = etree.SubElement(rt, "{%s}patientRole" % NS)
    pat = etree.SubElement(pr, "{%s}patient" % NS)
    etree.SubElement(pat, "{%s}administrativeGenderCode" % NS,
                     code=(asm["demographics"]["gender"] or "UN")[0].upper())
    etree.SubElement(pat, "{%s}ageBand" % NS).text = asm["demographics"]["age_band"]

    comp = etree.SubElement(root, "{%s}component" % NS)
    struc = etree.SubElement(comp, "{%s}structuredBody" % NS)

    def section(title_txt, entries):
        csec = etree.SubElement(struc, "{%s}component" % NS)
        sec = etree.SubElement(csec, "{%s}section" % NS)
        etree.SubElement(sec, "{%s}title" % NS).text = title_txt
        txt = etree.SubElement(sec, "{%s}text" % NS)
        lst = etree.SubElement(txt, "{%s}list" % NS)
        for e in entries[:60]:
            etree.SubElement(lst, "{%s}item" % NS).text = str(e)

    section("Problems", [d["text"] for d in asm["diagnoses"] if d["source_table"] != "treatment"])
    section("Medications", [m["text"] for m in asm["medications"]])
    section("Allergies", [a["name"] for a in asm["allergies"]] or ["No known allergies recorded"])
    section("Results (labs)", [f"{l['canonical']}: {l['value']} {l.get('unit') or ''}"
                               for l in asm["labs"] if l.get("value") is not None])
    section("Vital signs", [f"{n}: mean {s['mean']} {s.get('unit') or ''}"
                            for n, s in asm["vitals"]["summary"].items()])
    section("Procedures / treatments",
            [d["text"] for d in asm["diagnoses"] if d["source_table"] == "treatment"])
    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")


# --------------------------------------------------------------------------- #
# DICOM Secondary Capture of the ECG plot (format testing only)
# --------------------------------------------------------------------------- #
DICOM_STATEMENT = ("Synthetic DICOM derivative of a deidentified PTB-XL ECG image. "
                   "Not a clinical diagnostic image. Not linked to the eICU patient.")


def write_dicom_sc(png_path: Path, out_path: Path, cfg, ecg, asm):
    import numpy as np
    from PIL import Image, ImageDraw
    import pydicom
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.uid import generate_uid, ExplicitVRLittleEndian

    img = Image.open(png_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    for i, line in enumerate([
        "SYNTHETIC DICOM SECONDARY CAPTURE - NOT A CLINICAL IMAGE",
        "Derived from deidentified PTB-XL ECG. Not linked to the eICU patient.",
        cfg["disclaimers"]["ecg_donor"][:70]]):
        draw.rectangle([0, i * 14, img.width, i * 14 + 14], fill=(0, 0, 0))
        draw.text((3, i * 14 + 2), line, fill=(255, 255, 0))
    arr = np.asarray(img, dtype=np.uint8)

    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(str(out_path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.SpecificCharacterSet = "ISO_IR 192"  # UTF-8 for any non-ASCII disclaimer chars
    ds.SOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    # NO PHI: deidentified placeholders only
    ds.PatientName = "ANONYMIZED^COMPOSITE"
    ds.PatientID = f"CAREGUARD-{asm['case_id']}"
    ds.PatientIdentityRemoved = "YES"
    ds.DeidentificationMethod = "composite research asset; no source PHI"
    ds.Modality = "OT"  # Other — explicitly NOT ECG/US/echo modality
    ds.ConversionType = "WSD"
    ds.StudyDescription = "Synthetic ECG Secondary Capture (format testing)"
    ds.SeriesDescription = "PTB-XL ECG image derivative — not diagnostic"
    ds.ImageComments = DICOM_STATEMENT
    ds.PatientComments = cfg["disclaimers"]["ecg_donor"]
    ds.Rows, ds.Columns = arr.shape[0], arr.shape[1]
    ds.SamplesPerPixel = 3
    ds.PhotometricInterpretation = "RGB"
    ds.PlanarConfiguration = 0
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    ds.PixelData = arr.tobytes()
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.save_as(str(out_path))


# --------------------------------------------------------------------------- #
# Analysis profiles
# --------------------------------------------------------------------------- #
def profiles(asm, ecg):
    organ_counts = {}
    for dx in asm["diagnoses"]:
        for o in dx["organ_systems"]:
            organ_counts[o] = organ_counts.get(o, 0) + 1
    organ_profile = {"noncardiac_organ_systems": asm["noncardiac_organ_systems"],
                     "organ_diagnosis_counts": organ_counts,
                     "n_noncardiac_organs": len(asm["noncardiac_organ_systems"])}
    cv_profile = {"cardiovascular_categories": asm["cv_categories"],
                  "n_categories": len(asm["cv_categories"]),
                  "cardiac_diagnoses": [d["text"] for d in asm["diagnoses"]
                                        if d.get("is_cardiovascular") or d.get("cv_categories")][:40]}
    multimorbidity = {"n_organ_systems_total": len(asm["noncardiac_organ_systems"]) + 1,
                      "cardiovascular_plus": {o: True for o in asm["noncardiac_organ_systems"]},
                      "three_or_more_organ_systems": len(asm["noncardiac_organ_systems"]) >= 2}
    # timeline from offsets
    events = []
    for dx in asm["diagnoses"]:
        if dx.get("offset") is not None:
            events.append({"offset_min": dx["offset"], "type": "diagnosis", "detail": dx["text"][:80]})
    for m in asm["medications"]:
        so = m.get("start_offset")
        if so not in (None, "") and str(so).lstrip("-").isdigit():
            events.append({"offset_min": int(so), "type": "medication", "detail": m["text"][:80]})
    events.sort(key=lambda e: e["offset_min"] if isinstance(e["offset_min"], int) else 0)
    timeline = {"n_events": len(events), "events": events[:200]}
    return organ_profile, cv_profile, multimorbidity, timeline


# --------------------------------------------------------------------------- #
# Manifest / provenance / README / medication evidence
# --------------------------------------------------------------------------- #
def manifest(asm, cfg, ecg, fhir_meta, files, echo=None):
    echo = echo or {}
    m = {
        "case_id": asm["case_id"], "case_number": asm.get("case_number"),
        "source_type": asm.get("source_type", "real"),
        "real_patient_data": asm.get("real_patient_data", True),
        "source_dataset": asm["source_dataset"],
        "source_identifier": {"dataset": "eICU-CRD Demo 2.0.1",
                              "patientunitstayid": asm["patientunitstayid"]},
        "license": cfg["sources"]["eicu"]["license"],
        "selection_tier": asm["eligibility"]["tier"],
        "disclaimers": [cfg["disclaimers"]["research_only"], cfg["disclaimers"]["composite"]],
        "chatbot_contract": "This is a composite research case assembled from "
                            "deidentified open datasets for software testing.",
        "fhir": {"resource_count": (fhir_meta or {}).get("total_resources"),
                 "valid": (fhir_meta or {}).get("valid")},
        "files": files,
    }
    if ecg.get("assigned"):
        m["ecg_source"] = "PTB-XL"
        m["ecg_record_id"] = str(ecg.get("ecg_record_id"))
        m["linkage_type"] = "matched_external_modality"
        m["same_patient_as_ehr"] = False
        m["match_features"] = (ecg.get("match_features") or "").split("|") if ecg.get("match_features") else []
        m["ecg_warning"] = cfg["disclaimers"]["ecg_donor"]
        m["ecg_license"] = cfg["sources"]["ptbxl"]["license"]
    else:
        m["ecg_source"] = None
        m["same_patient_as_ehr"] = False
    if echo.get("assigned"):
        m["echo_source"] = "EchoNet-Dynamic"
        m["echo_record_id"] = str(echo.get("echo_id"))
        m["echo_modality"] = "US"
        m["echo_linkage_type"] = "matched_external_modality"
        m["echo_same_patient_as_ehr"] = False
        m["echo_donor_ejection_fraction_pct"] = echo.get("donor_ef")
        m["echo_warning"] = echo.get("warning")
        m["echo_license"] = "Stanford EchoNet Research Use Agreement (via mirror)"
    else:
        m["echo_source"] = None
    return m


def provenance(asm, cfg):
    fields = []
    for dx in asm["diagnoses"]:
        fields.append({"field": "condition", "value": dx["text"][:80],
                       "source_dataset": "eICU-CRD Demo 2.0.1",
                       "source_table": dx["source_table"], "source_row_id": dx["source_row_id"],
                       "source_column": "diagnosisstring/pasthistoryvalue",
                       "assertion_type": "recorded", "confidence": 1.0})
    for m in asm["medications"]:
        fields.append({"field": "medication", "value": m["text"][:80],
                       "source_dataset": "eICU-CRD Demo 2.0.1",
                       "source_table": m["source_table"], "source_row_id": m["source_row_id"],
                       "source_column": "drugname", "assertion_type": "recorded", "confidence": 1.0})
    for lb in asm["labs"]:
        fields.append({"field": "lab", "value": f"{lb['canonical']}={lb.get('value')}",
                       "source_dataset": "eICU-CRD Demo 2.0.1", "source_table": "lab",
                       "source_row_id": lb["source_row_id"], "source_column": "labresult",
                       "assertion_type": "recorded", "confidence": 1.0})
    return {
        "case_id": asm["case_id"],
        "mapping_rule_version": cfg["mapping_rule_version"],
        "conversion_timestamp": C.now_iso(),
        "source_dataset": "eICU-CRD Demo 2.0.1",
        "field_count": len(fields),
        "provenance_coverage": 1.0,
        "fields": fields,
        "notes": "Vital-sign observations in the FHIR bundle are assertion_type="
                 "derived_deterministically (mean over the recorded series).",
    }


def readme(asm, cfg, ecg, echo=None):
    echo = echo or {}
    d = asm["demographics"]
    parts = [
        f"# {asm['case_id']} — HeartTwin CareGuard Composite Research Case", "",
        f"> {cfg['disclaimers']['research_only']}", ">",
        f"> {cfg['disclaimers']['composite']}", "",
        "This is a composite research case assembled from deidentified open datasets "
        "for software testing.", "",
        "## What is real",
        f"- Structured EHR: **real, deidentified ICU stay** from {asm['source_dataset']} "
        f"(patientunitstayid {asm['patientunitstayid']}).",
    ]
    if ecg.get("assigned"):
        parts += [
            f"- ECG: **real, deidentified** PTB-XL record {ecg['ecg_record_id']} — but a "
            "**matched external modality**.",
            "",
            "## What must never be claimed",
            f"- {cfg['disclaimers']['ecg_donor']}",
            "- The ECG does NOT belong to the eICU patient; the modalities are different individuals.",
        ]
    if echo.get("assigned"):
        parts += [
            f"- Echocardiogram: **real, deidentified** EchoNet-Dynamic record {echo.get('echo_id')} — a "
            "**matched external modality** (apical 4-chamber ultrasound video).",
            f"- The echo does NOT belong to the eICU patient. Donor EF {echo.get('donor_ef')}% "
            "(EDV/ESV are the donor's, not this patient's).",
        ]
    parts += [
        "",
        "## What is transformed / generated",
        "- `clinical/fhir-bundle.json`, `clinical/ccda.xml`: deterministic exports of the eICU record.",
        "- `clinical/patient-report.{txt,pdf}`: source-grounded generated summaries.",
        "- `ecg/ecg-secondary-capture.dcm`: generated ECG-image wrapper (not diagnostic).",
        "",
        "## Contents",
        "- `manifest.json`, `provenance.json`, `quality.json`",
        "- `clinical/` FHIR bundle + NDJSON + summaries (json/yaml/csv/parquet) + report (txt/pdf) + C-CDA",
        "- `ehr/` source-grounded CSV tables", "- `ecg/` waveform + plot + DICOM (if assigned)",
        "- `medication-evidence/` RxNorm normalization + openFDA label evidence",
        "- `analysis/` organ / cardiovascular / multimorbidity / timeline / completeness profiles",
        "",
        f"Cardiovascular context: {', '.join(asm['cv_categories']) or 'n/a'}  ",
        f"Non-cardiac organ systems: {', '.join(asm['noncardiac_organ_systems'])}  ",
        f"Age band {d['age_band']}, sex {d['gender']}, ICU {d['unit_type']}.",
    ]
    return "\n".join(parts)


def medication_evidence(asm, normalized):
    norm_out, labels, unresolved = [], [], []
    seen = set()
    for m in asm["medications"]:
        low = (m.get("text") or "").lower()
        if low in seen:
            continue
        seen.add(low)
        rec = normalized.get(low)
        if not rec:
            unresolved.append({"original_text": m["text"], "reason": "not_normalized"})
            continue
        norm_out.append({"original_text": rec.get("original_text", m["text"]),
                         "normalized_name": rec.get("normalized_name"),
                         "rxcui": rec.get("rxcui"), "tty": rec.get("tty"),
                         "ingredients": rec.get("ingredients", []),
                         "confidence": rec.get("confidence"),
                         "normalization_method": rec.get("normalization_method"),
                         "unresolved": rec.get("unresolved", True)})
        if rec.get("unresolved"):
            unresolved.append({"original_text": m["text"], "cleaned": rec.get("cleaned")})
        lab = rec.get("label")
        if lab and lab.get("found"):
            labels.append({"rxcui": rec.get("rxcui"), "normalized_name": rec.get("normalized_name"),
                           "label_id": lab.get("label_id"), "set_id": lab.get("set_id"),
                           "effective_time": lab.get("effective_time"),
                           "has_boxed_warning": bool(lab.get("boxed_warning")),
                           "has_contraindications": bool(lab.get("contraindications")),
                           "has_drug_interactions": bool(lab.get("drug_interactions")),
                           "boxed_warning_excerpt": (lab.get("boxed_warning") or "")[:600],
                           "contraindications_excerpt": (lab.get("contraindications") or "")[:600],
                           "source": lab.get("source")})
    return norm_out, labels, unresolved
