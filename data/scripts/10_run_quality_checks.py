#!/usr/bin/env python3
"""Stage 10 — aggregate per-case quality + build the cohort/ tables.

Writes cohort_manifest.{csv,parquet,json}, patient_features.{csv,parquet}, and the
long tables diagnoses/medications/labs/vitals/allergies/provenance.csv, plus
analysis/case_completeness.csv and analysis/medication_normalization_report.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import classify as X  # noqa: E402

ASM = C.STAGING / "assembled"
FHIR_OUT = C.STAGING / "fhir"


def _load_assign(name):
    import pandas as pd
    p = C.COHORT / name
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    return {r["case_id"]: {k: (None if pd.isna(r[k]) else r[k]) for k in df.columns}
            for _, r in df.iterrows()}


def load_ecg():
    return _load_assign("ecg_assignments.csv")


def load_echo():
    return _load_assign("echo_assignments.csv")


def main() -> None:
    import pandas as pd
    C.ensure_dirs()
    log = C.get_logger("10_run_quality_checks")
    cfg = C.load_config()
    log.info("=== Stage 10: quality aggregation + cohort tables ===")

    sel = pd.read_csv(C.STAGING / "eicu" / "cohort_selection.csv")
    ecg_map = load_ecg()
    echo_map = load_echo()
    normalized = C.read_json(C.STAGING / "medication-normalization" / "normalized.json") \
        if (C.STAGING / "medication-normalization" / "normalized.json").exists() else {}

    manifest_rows, feature_rows, completeness_rows = [], [], []
    dx_rows, med_rows, lab_rows, vit_rows, alg_rows, prov_rows = [], [], [], [], [], []

    for cid in sel["case_id"]:
        asm = C.read_json(ASM / f"{cid}.json")
        q = C.read_json(C.CASES / cid / "quality.json") if (C.CASES / cid / "quality.json").exists() else {}
        fhir_meta = C.read_json(FHIR_OUT / f"{cid}.meta.json") if (FHIR_OUT / f"{cid}.meta.json").exists() else {}
        ecg = ecg_map.get(cid, {})
        echo = echo_map.get(cid, {})
        d = asm["demographics"]
        organs = asm["noncardiac_organ_systems"]
        lab_names = {l["canonical"] for l in asm["labs"]}
        vsum = asm["vitals"]["summary"]
        comp = q.get("components", {})

        manifest_rows.append({
            "case_id": cid, "patientunitstayid": asm["patientunitstayid"],
            "source_type": asm.get("source_type", "real"),
            "real_patient_data": asm.get("real_patient_data", True),
            "selection_tier": asm["eligibility"]["tier"], "age": d["age"], "age_band": d["age_band"],
            "gender": d["gender"], "icu_type": d["unit_type"], "icu_los_days": d["icu_los_days"],
            "discharge_status": d["hospital_discharge_status"],
            "cv_categories": "|".join(asm["cv_categories"]),
            "n_cv_categories": len(asm["cv_categories"]),
            "noncardiac_organs": "|".join(organs), "n_noncardiac_organs": len(organs),
            "n_diagnoses": len(asm["diagnoses"]), "n_medications": len(asm["medications"]),
            "n_allergies": len(asm["allergies"]), "n_labs": len(asm["labs"]),
            "n_treatments": asm["n_treatments"],
            "ecg_assigned": bool(ecg.get("assigned")), "ecg_record_id": ecg.get("ecg_record_id"),
            "ecg_superclass": ecg.get("ecg_primary_superclass"),
            "echo_assigned": bool(echo.get("assigned")), "echo_record_id": echo.get("echo_id"),
            "echo_donor_ef": echo.get("donor_ef"), "echo_ef_category": echo.get("echo_ef_category"),
            "fhir_resources": fhir_meta.get("total_resources"), "fhir_valid": fhir_meta.get("valid"),
            "overall_completeness_score": q.get("overall_completeness_score"),
        })

        feat = {"case_id": cid, "age": d["age"] or 0,
                "sex_female": int(d["gender"] == "female"),
                "icu_los_days": d["icu_los_days"] or 0,
                "n_cv_categories": len(asm["cv_categories"]),
                "n_noncardiac_organs": len(organs),
                "n_medications": len(asm["medications"]), "n_labs": len(lab_names),
                "died_in_hospital": int(str(d["hospital_discharge_status"]).lower() == "expired"),
                "ecg_assigned": int(bool(ecg.get("assigned"))),
                "ecg_superclass": ecg.get("ecg_primary_superclass") or "NONE",
                "overall_completeness_score": q.get("overall_completeness_score")}
        for o in X.ORGAN_SYSTEMS:
            feat[f"organ_{o}"] = int(o in organs)
        for cat in X.CV_CATEGORIES:
            feat[f"cv_{cat}"] = int(cat in asm["cv_categories"])
        for lname in ("Troponin I", "Troponin T", "BNP", "Creatinine", "Potassium",
                      "Sodium", "Lactate", "INR", "AST", "ALT"):
            feat[f"lab_{lname.replace(' ', '_')}"] = int(lname in lab_names)
        for vname, key in [("Heart rate", "mean_hr"), ("Systolic blood pressure", "mean_sbp"),
                           ("Oxygen saturation", "mean_spo2")]:
            feat[key] = vsum.get(vname, {}).get("mean")
        feature_rows.append(feat)

        crow = {"case_id": cid, "overall_completeness_score": q.get("overall_completeness_score"),
                "n_warnings": len(q.get("missingness_warnings", []))}
        crow.update({k: comp.get(k) for k in comp})
        completeness_rows.append(crow)

        for dx in asm["diagnoses"]:
            dx_rows.append({"case_id": cid, "text": dx["text"], "icd_code": dx.get("icd_code"),
                            "source_table": dx["source_table"], "clinical_status": dx.get("clinical_status"),
                            "organ_systems": "|".join(dx["organ_systems"]),
                            "cv_categories": "|".join(dx["cv_categories"])})
        seen_m = set()
        for m in asm["medications"]:
            low = (m.get("text") or "").lower()
            if low in seen_m:
                continue
            seen_m.add(low)
            n = normalized.get(low, {})
            med_rows.append({"case_id": cid, "text": m["text"],
                             "normalized_name": n.get("normalized_name"), "rxcui": n.get("rxcui"),
                             "confidence": n.get("confidence"),
                             "resolved": not n.get("unresolved", True),
                             "has_label": bool((n.get("label") or {}).get("found"))})
        for l in asm["labs"]:
            if l.get("value") is None:
                continue
            lab_rows.append({"case_id": cid, "canonical": l["canonical"], "loinc": l["loinc"],
                             "group": l["group"], "value": l["value"], "unit": l.get("unit")})
        for name, s in vsum.items():
            vit_rows.append({"case_id": cid, "vital": name, "mean": s["mean"],
                             "min": s["min"], "max": s["max"], "count": s["count"]})
        for a in asm["allergies"]:
            alg_rows.append({"case_id": cid, "name": a["name"]})
        prov_rows.append({"case_id": cid, "provenance_coverage": (q.get("components", {}) or {}).get("provenance_coverage"),
                          "mapping_rule_version": cfg["mapping_rule_version"],
                          "resources_with_provenance": (q.get("counts", {}) or {}).get("resources_with_provenance"),
                          "clinical_resources": (q.get("counts", {}) or {}).get("clinical_resources")})

    # write cohort tables
    mani = pd.DataFrame(manifest_rows)
    mani.to_csv(C.COHORT / "cohort_manifest.csv", index=False)
    mani.to_parquet(C.COHORT / "cohort_manifest.parquet", index=False)
    C.write_json(C.COHORT / "cohort_manifest.json", manifest_rows)
    feat_df = pd.DataFrame(feature_rows)
    feat_df.to_csv(C.COHORT / "patient_features.csv", index=False)
    feat_df.to_parquet(C.COHORT / "patient_features.parquet", index=False)
    pd.DataFrame(dx_rows).to_csv(C.COHORT / "diagnoses.csv", index=False)
    pd.DataFrame(med_rows).to_csv(C.COHORT / "medications.csv", index=False)
    pd.DataFrame(lab_rows).to_csv(C.COHORT / "labs.csv", index=False)
    pd.DataFrame(vit_rows).to_csv(C.COHORT / "vitals.csv", index=False)
    pd.DataFrame(alg_rows).to_csv(C.COHORT / "allergies.csv", index=False)
    pd.DataFrame(prov_rows).to_csv(C.COHORT / "provenance.csv", index=False)
    pd.DataFrame(completeness_rows).to_csv(C.ANALYSIS / "case_completeness.csv", index=False)

    # medication normalization report (unique strings)
    mn_rows = []
    for low, rec in normalized.items():
        mn_rows.append({"original_text": rec.get("original_text", low),
                        "cleaned": rec.get("cleaned"), "normalized_name": rec.get("normalized_name"),
                        "rxcui": rec.get("rxcui"), "confidence": rec.get("confidence"),
                        "resolved": not rec.get("unresolved", True),
                        "method": rec.get("normalization_method"),
                        "n_ingredients": len(rec.get("ingredients", [])),
                        "has_label": bool((rec.get("label") or {}).get("found")),
                        "boxed_warning": bool((rec.get("label") or {}).get("boxed_warning"))})
    pd.DataFrame(mn_rows, columns=["original_text", "cleaned", "normalized_name", "rxcui",
                                   "confidence", "resolved", "method", "n_ingredients",
                                   "has_label", "boxed_warning"]).to_csv(
        C.ANALYSIS / "medication_normalization_report.csv", index=False)

    scores = [r["overall_completeness_score"] for r in manifest_rows if r["overall_completeness_score"] is not None]
    C.write_json(C.ANALYSIS / "quality_summary.json", {
        "generated_at": C.now_iso(), "cases": len(manifest_rows),
        "mean_completeness": round(sum(scores) / max(len(scores), 1), 4),
        "min_completeness": min(scores) if scores else None,
        "max_completeness": max(scores) if scores else None,
        "fhir_valid": int(sum(1 for r in manifest_rows if r["fhir_valid"])),
        "ecg_assigned": int(sum(1 for r in manifest_rows if r["ecg_assigned"])),
        "echo_assigned": int(sum(1 for r in manifest_rows if r["echo_assigned"]))})
    log.info("=== Stage 10 complete: %d cases; mean completeness %.3f ===",
             len(manifest_rows), sum(scores) / max(len(scores), 1))
    print(f"cohort_rows={len(manifest_rows)}")


if __name__ == "__main__":
    main()
