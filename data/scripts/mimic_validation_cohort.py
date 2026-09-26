#!/usr/bin/env python3
"""Supplementary — summarize the MIMIC-IV Demo 1.0 as a SEPARATE validation cohort.

This cohort is NEVER counted toward the 1,000-case eICU cohort. It exists only to
cross-check that the classification/organ-mapping generalizes to a second real,
deidentified ICU source. Writes analysis/mimic_validation_cohort.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import classify as X  # noqa: E402

M = C.RAW_MIMIC


def main() -> None:
    import pandas as pd
    log = C.get_logger("mimic_validation_cohort")
    pats = M / "core" / "patients.csv.gz"
    if not pats.exists():
        log.warning("MIMIC demo not present; skipping validation cohort")
        C.write_json(C.ANALYSIS / "mimic_validation_cohort.json",
                     {"available": False, "note": "MIMIC-IV demo not downloaded"})
        return
    patients = pd.read_csv(pats)
    dx = pd.read_csv(M / "hosp" / "diagnoses_icd.csv.gz")
    dref = pd.read_csv(M / "hosp" / "d_icd_diagnoses.csv.gz")
    title = dict(zip(dref.icd_code.astype(str), dref.long_title.astype(str)))

    dx["title"] = dx.icd_code.astype(str).map(title).fillna("")
    # cardiovascular + organ classification via shared classifier
    cv_subject = set()
    organ_counts = {}
    for _, r in dx.iterrows():
        t = r["title"]
        if X.cardiovascular_categories(t):
            cv_subject.add(r["subject_id"])
        for o in X.organ_systems(text=t):
            organ_counts[o] = organ_counts.get(o, 0) + 1

    summary = {
        "available": True,
        "role": "separate_validation_cohort_NOT_counted_in_eicu_main_cohort",
        "generated_at": C.now_iso(),
        "n_patients": int(patients.subject_id.nunique()),
        "sex_distribution": patients.gender.value_counts().to_dict(),
        "anchor_age_summary": {"min": int(patients.anchor_age.min()),
                               "max": int(patients.anchor_age.max()),
                               "mean": round(float(patients.anchor_age.mean()), 1)},
        "n_diagnosis_rows": int(len(dx)),
        "patients_with_cardiovascular_dx": len(cv_subject),
        "noncardiac_organ_diagnosis_counts": dict(sorted(organ_counts.items(),
                                                         key=lambda x: -x[1])),
        "top_diagnoses": dx.title[dx.title != ""].value_counts().head(15).to_dict(),
        "note": "Real, deidentified MIMIC-IV Demo 1.0. Kept strictly separate from "
                "the eICU main cohort; used only to sanity-check classification.",
    }
    C.write_json(C.ANALYSIS / "mimic_validation_cohort.json", summary)
    log.info("MIMIC validation cohort: %d patients, %d with CV dx",
             summary["n_patients"], summary["patients_with_cardiovascular_dx"])
    print(f"mimic_patients={summary['n_patients']} cv={summary['patients_with_cardiovascular_dx']}")


if __name__ == "__main__":
    main()
