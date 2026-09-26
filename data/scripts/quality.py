"""Deterministic per-case data-quality scoring (spec §13).

Every component score is a documented formula in [0,1]; the overall score is the
weighted sum, clamped to [0,1]. Scores are computed from packaged artifacts, not
inflated. Missingness warnings are surfaced explicitly.
"""
from __future__ import annotations

WEIGHTS = {
    "cardiac_context": 0.18,
    "noncardiac_morbidity": 0.15,
    "medication_coverage": 0.12,
    "lab_coverage": 0.12,
    "vital_coverage": 0.10,
    "allergy_coverage": 0.06,
    "treatment_coverage": 0.07,
    "ecg_coverage": 0.08,
    "fhir_validation": 0.06,
    "provenance_coverage": 0.06,
}
CORE_VITALS = {"Heart rate", "Systolic blood pressure", "Diastolic blood pressure",
               "Respiratory rate", "Oxygen saturation", "Body temperature"}
CARDIAC_LABS = {"Troponin I", "Troponin T", "BNP"}


def _clamp(x):
    return round(min(max(float(x), 0.0), 1.0), 4)


def compute_case_quality(asm, fhir_meta, ecg_assigned, bundle):
    dx = asm.get("diagnoses", [])
    cv = asm.get("cv_categories", [])
    organs = asm.get("noncardiac_organ_systems", [])
    meds = {(m.get("text") or "").lower() for m in asm.get("medications", [])}
    labs = asm.get("labs", [])
    lab_names = {l["canonical"] for l in labs}
    vital_types = set(asm.get("vitals", {}).get("summary", {}).keys())
    allergies = asm.get("allergies", [])
    n_tx = asm.get("n_treatments", 0)

    # provenance coverage from the bundle: clinical resources carrying our ext.
    clinical_rt = {"Condition", "Observation", "MedicationStatement", "MedicationRequest",
                   "AllergyIntolerance", "Procedure", "Goal", "CarePlan", "Encounter"}
    total = withprov = 0
    for e in bundle.get("entry", []):
        r = e.get("resource", {})
        if r.get("resourceType") in clinical_rt:
            total += 1
            exts = r.get("extension", []) or []
            if any(x.get("url", "").endswith("/provenance") for x in exts):
                withprov += 1

    comp = {
        "cardiac_context": _clamp(min(len(cv) / 2.0, 1.0) if cv else 0.0),
        "noncardiac_morbidity": _clamp(len(organs) / 3.0),
        "medication_coverage": _clamp(len(meds) / 5.0),
        "lab_coverage": _clamp(len(lab_names) / 8.0),
        "vital_coverage": _clamp(len(vital_types & CORE_VITALS) / len(CORE_VITALS)),
        "allergy_coverage": 1.0 if allergies else 0.0,
        "treatment_coverage": _clamp(n_tx / 3.0),
        "ecg_coverage": 1.0 if ecg_assigned else 0.0,
        "fhir_validation": 1.0 if (fhir_meta or {}).get("valid") else 0.0,
        "provenance_coverage": _clamp(withprov / total) if total else 0.0,
    }
    overall = _clamp(sum(comp[k] * WEIGHTS[k] for k in WEIGHTS))

    warnings = []
    if not cv:
        warnings.append("no explicit cardiovascular category detected")
    if len(organs) < 2:
        warnings.append("fewer than 2 non-cardiac organ systems")
    if not allergies:
        warnings.append("no allergy records")
    if not ecg_assigned:
        warnings.append("no external ECG assigned")
    if not (lab_names & CARDIAC_LABS):
        warnings.append("no cardiac biomarker (troponin/BNP) recorded")
    if len(vital_types & CORE_VITALS) < 3:
        warnings.append("fewer than 3 core vital-sign types")

    return {
        "case_id": asm.get("case_id"),
        "components": comp,
        "weights": WEIGHTS,
        "overall_completeness_score": overall,
        "missingness_warnings": warnings,
        "counts": {"cv_categories": len(cv), "noncardiac_organs": len(organs),
                   "unique_medications": len(meds), "labs": len(lab_names),
                   "vital_types": len(vital_types), "allergies": len(allergies),
                   "treatments": n_tx, "ecg_assigned": bool(ecg_assigned),
                   "resources_with_provenance": withprov, "clinical_resources": total},
    }
