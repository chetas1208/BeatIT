#!/usr/bin/env python3
"""Stage 04 — assemble per-stay structured records and select the cohort.

Reads staging parquet (from 03), assembles one structured record per ICU stay
with organ-system + cardiovascular classification and provenance-ready rows,
computes eligibility tiers (A/B/C), and deterministically selects up to the
target number of REAL eICU cases. If fewer real cases qualify than the target
and synthetic fallback is enabled, records the shortfall for stage 04b/Synthea.

Assembled records are written to staging/eicu/assembled/<stay>.json and consumed
verbatim by later stages (07 meds, 08 FHIR, 09 case files).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402
import classify as X  # noqa: E402

STAGE = C.STAGING / "eicu"
ASM = STAGE / "assembled"


def _load(name):
    import pandas as pd
    p = STAGE / f"{name}.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    # Normalize pandas NA/NaN -> Python None (object dtype) so `x or ""` idioms
    # and dict .get() are safe throughout assembly.
    if not df.empty:
        df = df.astype(object).where(pd.notna(df), None)
    return df


def parse_age(raw):
    if raw is None:
        return None, "unknown"
    s = str(raw).strip()
    if not s or s.lower() == "nan":
        return None, "unknown"
    if ">" in s:  # ">89" deidentified cap
        return 90, "90+"
    try:
        a = int(float(s))
    except ValueError:
        return None, "unknown"
    bands = [(30, "18-29"), (40, "30-39"), (50, "40-49"), (60, "50-59"),
             (70, "60-69"), (80, "70-79"), (90, "80-89")]
    for hi, label in bands:
        if a < hi:
            return a, label
    return a, "90+"


def _num(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _truthy(v):
    """Parse eICU string flags (columns arrive as strings from stage 03)."""
    if v is None:
        return None
    return str(v).strip().lower() in ("true", "1", "yes", "t")


def build_diagnoses(stay, dx, adx, ph, tx):
    """Collect diagnosis-like rows from diagnosis, admissiondx, pastHistory,
    treatment; classify each. Returns (rows, cv_categories, organ_systems)."""
    rows, cv, organs = [], set(), set()

    def add(text, table, row_id, *, offset=None, icd=None, priority=None,
            active=None, path=None, status="active"):
        text = (text or "").strip()
        if not text:
            return
        cats = X.cardiovascular_categories(text, path)
        orgs = X.organ_systems(diagnosisstring=text, path=path, text=text)
        cv.update(cats)
        organs.update(orgs)
        rows.append({
            "text": text, "source_table": table, "source_row_id": str(row_id),
            "offset": None if offset is None else int(offset) if _num(offset) is not None else None,
            "icd_code": icd or None, "priority": priority or None,
            "active_upon_discharge": active, "clinical_status": status,
            "cv_categories": cats, "organ_systems": sorted(orgs),
            "is_cardiovascular": bool(cats) or X.eicu_prefix_organ(text) == "cardiovascular"
                                 or X.eicu_prefix_organ(path) == "cardiovascular",
        })

    for _, r in dx.iterrows():
        add(r.get("diagnosisstring"), "diagnosis", r.get("diagnosisid"),
            offset=r.get("diagnosisoffset"), icd=r.get("icd9code"),
            priority=r.get("diagnosispriority"),
            active=_truthy(r.get("activeupondischarge")))
    for _, r in adx.iterrows():
        add(r.get("admitdxname") or r.get("admitdxtext"), "admissiondx", r.get("admissiondxid"),
            offset=r.get("admitdxenteredoffset"), path=r.get("admitdxpath"))
    for _, r in ph.iterrows():
        add(r.get("pasthistoryvalue") or r.get("pasthistoryvaluetext"), "pastHistory",
            r.get("pasthistoryid"), offset=r.get("pasthistoryoffset"),
            path=r.get("pasthistorypath"), status="historical")
    for _, r in tx.iterrows():
        add(r.get("treatmentstring"), "treatment", r.get("treatmentid"),
            offset=r.get("treatmentoffset"), path=r.get("treatmentstring"),
            active=_truthy(r.get("activeupondischarge")))
    return rows, sorted(cv), sorted(organs)


def build_meds(med, adr, inf):
    rows = []
    for _, r in med.iterrows():
        name = (r.get("drugname") or "").strip()
        if not name:
            continue
        rows.append({"text": name, "dosage": r.get("dosage"), "route": r.get("routeadmin"),
                     "frequency": r.get("frequency"), "start_offset": r.get("drugstartoffset"),
                     "stop_offset": r.get("drugstopoffset"), "source_table": "medication",
                     "source_row_id": str(r.get("medicationid")),
                     "status": "stopped" if r.get("drugstopoffset") not in (None, "") else "active"})
    for _, r in adr.iterrows():
        name = (r.get("drugname") or "").strip()
        if not name:
            continue
        rows.append({"text": name, "dosage": r.get("drugdosage"), "route": None,
                     "frequency": r.get("drugadmitfrequency"), "start_offset": r.get("drugoffset"),
                     "stop_offset": None, "source_table": "admissiondrug",
                     "source_row_id": str(r.get("admissiondrugid")), "status": "admission"})
    for _, r in inf.iterrows():
        name = (r.get("drugname") or "").strip()
        if not name:
            continue
        rows.append({"text": name, "dosage": r.get("drugamount"), "route": "IV infusion",
                     "frequency": None, "start_offset": r.get("infusionoffset"),
                     "stop_offset": None, "source_table": "infusionDrug",
                     "source_row_id": f"{r.get('patientunitstayid')}:{r.get('infusionoffset')}:{name}",
                     "status": "infusion"})
    return rows


def build_allergies(al):
    rows = []
    for _, r in al.iterrows():
        name = (r.get("allergyname") or r.get("drugname") or "").strip()
        if not name:
            continue
        rows.append({"name": name, "type": r.get("allergytype"),
                     "offset": r.get("allergyoffset"), "source_table": "allergy",
                     "source_row_id": str(r.get("allergyid"))})
    return rows


def build_labs(lab):
    rows = []
    for _, r in lab.iterrows():
        canon = X.canon_lab(r.get("labname"))
        if not canon:
            continue
        disp, loinc, group = canon
        val = _num(r.get("labresult"))
        rows.append({"labname": r.get("labname"), "canonical": disp, "loinc": loinc,
                     "group": group, "value": val, "text": r.get("labresulttext"),
                     "unit": r.get("labmeasurenamesystem"), "offset": r.get("labresultoffset"),
                     "source_table": "lab", "source_row_id": f"{r.get('patientunitstayid')}:{r.get('labresultoffset')}:{r.get('labname')}"})
    return rows


def summarize_vitals(vp, va):
    """Per-vital summary + a capped, evenly-spaced sample for case CSVs."""
    import pandas as pd
    summary, samples = {}, []
    present = False
    for df, colmap in [(vp, {"heartrate": "heartrate", "systemicsystolic": "systemicsystolic",
                             "systemicdiastolic": "systemicdiastolic", "systemicmean": "systemicmean",
                             "respiration": "respiration", "sao2": "sao2", "temperature": "temperature"}),
                       (va, {"noninvasivesystolic": "noninvasivesystolic",
                             "noninvasivediastolic": "noninvasivediastolic",
                             "noninvasivemean": "noninvasivemean"})]:
        if df.empty:
            continue
        present = True
        for col in colmap:
            if col not in df.columns:
                continue
            ser = pd.to_numeric(df[col], errors="coerce").dropna()
            if ser.empty:
                continue
            key = X.VITAL_LOINC.get(col, (col, "", ""))[0]
            s = summary.setdefault(key, {"count": 0, "min": None, "max": None,
                                         "mean": None, "loinc": X.VITAL_LOINC.get(col, ("", "", ""))[1],
                                         "unit": X.VITAL_LOINC.get(col, ("", "", ""))[2]})
            s["count"] += int(ser.count())
            s["min"] = float(ser.min()) if s["min"] is None else min(s["min"], float(ser.min()))
            s["max"] = float(ser.max()) if s["max"] is None else max(s["max"], float(ser.max()))
            s["mean"] = round(float(ser.mean()), 2)
    # sampled rows (periodic first, capped)
    if not vp.empty:
        vv = vp.sort_values("observationoffset")
        step = max(1, len(vv) // 300)
        for _, r in vv.iloc[::step].head(300).iterrows():
            samples.append({k: (None if pd.isna(r.get(k)) else r.get(k))
                            for k in ["observationoffset", "heartrate", "systemicsystolic",
                                      "systemicdiastolic", "systemicmean", "respiration",
                                      "sao2", "temperature"]})
    return {"present": present, "summary": summary, "samples": samples}


def eligibility(cv, organs, meds, labs, vitals, allergies_or_hist, treatments):
    has_cv = bool(cv)
    n_org = len(organs)
    has_med = len(meds) > 0
    has_lab = len(labs) > 0
    has_vital = vitals["present"]
    has_allergy_hist = allergies_or_hist
    has_tx = treatments > 0
    tier = None
    if has_cv and n_org >= 2 and has_med and has_lab and has_vital:
        tier = "A"
    elif has_cv and n_org >= 1 and has_med and has_lab and has_vital:
        tier = "B"
    elif has_cv and n_org >= 1 and (sum([has_med, has_lab, has_vital, has_allergy_hist, has_tx]) >= 2):
        tier = "C"
    return {"has_cv": has_cv, "n_noncardiac_organs": n_org, "has_med": has_med,
            "has_lab": has_lab, "has_vital": has_vital,
            "has_allergy_or_history": has_allergy_hist, "has_treatment": has_tx,
            "tier": tier}


def completeness(el, meds, labs, vitals, allergies, treatments):
    """Selection-ordering score in [0,1] (the authoritative quality score is
    recomputed in stage 10 from packaged artifacts)."""
    parts = {
        "cardiac_context": 1.0 if el["has_cv"] else 0.0,
        "noncardiac_morbidity": min(el["n_noncardiac_organs"] / 3.0, 1.0),
        "medication": min(len(meds) / 5.0, 1.0),
        "lab": min(len(labs) / 8.0, 1.0),
        "vital": 1.0 if vitals["present"] else 0.0,
        "allergy": 1.0 if allergies else 0.0,
        "treatment": min(treatments / 3.0, 1.0),
    }
    w = {"cardiac_context": 0.22, "noncardiac_morbidity": 0.20, "medication": 0.15,
         "lab": 0.15, "vital": 0.12, "allergy": 0.06, "treatment": 0.10}
    score = sum(parts[k] * w[k] for k in w)
    return round(min(max(score, 0.0), 1.0), 4), parts


def main() -> None:
    import pandas as pd
    C.ensure_dirs()
    ASM.mkdir(parents=True, exist_ok=True)
    log = C.get_logger("04_select_cohort")
    cfg = C.load_config()
    target = cfg["cohort"]["target_cases"]
    log.info("=== Stage 04: assemble + select (target=%d) ===", target)

    patient = _load("patient")
    if patient.empty:
        sys.exit("FATAL: no patient table — run 03 first")
    diagnosis = _load("diagnosis")
    admissiondx = _load("admissiondx")
    pasthistory = _load("pasthistory")
    treatment = _load("treatment")
    medication = _load("medication")
    admissiondrug = _load("admissiondrug")
    infusiondrug = _load("infusiondrug")
    allergy = _load("allergy")
    lab = _load("lab")
    vitalp = _load("vitalperiodic")
    vitala = _load("vitalaperiodic")
    careplang = _load("careplangeneral")
    careplangoal = _load("careplangoal")
    note = _load("note")

    def by_stay(df):
        if df.empty or "patientunitstayid" not in df.columns:
            return {}
        return {int(k): v for k, v in df.groupby("patientunitstayid")}

    pt_g = by_stay(patient)
    dx_g, adx_g, ph_g, tx_g = by_stay(diagnosis), by_stay(admissiondx), by_stay(pasthistory), by_stay(treatment)
    med_g, adr_g, inf_g = by_stay(medication), by_stay(admissiondrug), by_stay(infusiondrug)
    al_g, lab_g, vp_g, va_g = by_stay(allergy), by_stay(lab), by_stay(vitalp), by_stay(vitala)
    cpg_g, cpgo_g, note_g = by_stay(careplang), by_stay(careplangoal), by_stay(note)

    empty = pd.DataFrame()
    assembled_index = []
    stays = sorted(pt_g.keys())
    log.info("assembling %d stays", len(stays))

    for stay in stays:
        prow = pt_g[stay].iloc[0]
        age, band = parse_age(prow.get("age"))
        dxrows, cv, organs = build_diagnoses(
            stay, dx_g.get(stay, empty), adx_g.get(stay, empty),
            ph_g.get(stay, empty), tx_g.get(stay, empty))
        meds = build_meds(med_g.get(stay, empty), adr_g.get(stay, empty), inf_g.get(stay, empty))
        allergies = build_allergies(al_g.get(stay, empty))
        labs = build_labs(lab_g.get(stay, empty))
        vitals = summarize_vitals(vp_g.get(stay, empty), va_g.get(stay, empty))
        treatments = tx_g.get(stay, empty)
        n_tx = 0 if treatments is empty or treatments.empty else len(treatments)
        careplan = []
        for _, r in cpg_g.get(stay, empty).iterrows():
            careplan.append({"group": r.get("cplgroup"), "value": r.get("cplitemvalue"),
                             "type": "general", "source_row_id": str(r.get("cplgeneralid"))})
        for _, r in cpgo_g.get(stay, empty).iterrows():
            careplan.append({"group": r.get("cplgoalcategory"), "value": r.get("cplgoalvalue"),
                             "type": "goal", "status": r.get("cplgoalstatus"),
                             "source_row_id": str(r.get("cplgoalid"))})
        notes = []
        for _, r in note_g.get(stay, empty).head(20).iterrows():
            v = (r.get("notevalue") or "").strip()
            if v:
                notes.append({"type": r.get("notetype"), "offset": r.get("noteoffset"),
                              "value": v[:2000], "source_row_id": f"{stay}:{r.get('noteoffset')}"})

        el = eligibility(cv, organs, meds, labs, vitals,
                         bool(allergies) or not ph_g.get(stay, empty).empty, n_tx)
        score, parts = completeness(el, meds, labs, vitals, allergies, n_tx)

        los = _num(prow.get("unitdischargeoffset"))
        rec = {
            "patientunitstayid": stay,
            "uniquepid": prow.get("uniquepid"),
            "source_type": "real",
            "real_patient_data": True,
            "source_dataset": "eICU-CRD Demo 2.0.1",
            "demographics": {
                "age": age, "age_band": band, "gender": (prow.get("gender") or "").lower() or None,
                "ethnicity": prow.get("ethnicity") or None,
                "admission_height_cm": _num(prow.get("admissionheight")),
                "admission_weight_kg": _num(prow.get("admissionweight")),
                "unit_type": prow.get("unittype"), "unit_admit_source": prow.get("unitadmitsource"),
                "hospital_admit_source": prow.get("hospitaladmitsource"),
                "hospital_discharge_status": prow.get("hospitaldischargestatus"),
                "unit_discharge_status": prow.get("unitdischargestatus"),
                "icu_los_days": round(los / 1440.0, 2) if los is not None else None,
                "apache_admission_dx": prow.get("apacheadmissiondx"),
            },
            "diagnoses": dxrows,
            "cv_categories": cv,
            "noncardiac_organ_systems": organs,
            "medications": meds,
            "allergies": allergies,
            "labs": labs,
            "vitals": vitals,
            "careplan": careplan,
            "notes": notes,
            "n_treatments": n_tx,
            "eligibility": el,
            "completeness_score": score,
            "completeness_parts": parts,
        }
        if el["tier"]:  # only persist eligible stays
            C.write_json(ASM / f"{stay}.json", rec)
            assembled_index.append({
                "patientunitstayid": stay, "tier": el["tier"], "score": score,
                "n_cv": len(cv), "n_organs": len(organs), "n_meds": len(meds),
                "n_labs": len(labs), "has_vital": vitals["present"],
                "has_renal": "renal" in organs, "has_hepatic": "hepatic" in organs,
                "has_pulmonary": "pulmonary" in organs,
                "has_cardiac_labs": any(l["group"] == "cardiac" for l in labs),
                "age_band": band, "gender": rec["demographics"]["gender"],
            })

    idx = pd.DataFrame(assembled_index)
    log.info("eligible stays: %d (A=%d B=%d C=%d)", len(idx),
             (idx.tier == "A").sum() if len(idx) else 0,
             (idx.tier == "B").sum() if len(idx) else 0,
             (idx.tier == "C").sum() if len(idx) else 0)

    # Deterministic selection ordering (spec §7).
    tier_rank = {"A": 0, "B": 1, "C": 2}
    if len(idx):
        idx["tier_rank"] = idx["tier"].map(tier_rank)
        idx = idx.sort_values(
            by=["tier_rank", "score", "n_organs", "n_meds", "has_renal",
                "has_hepatic", "has_pulmonary", "has_cardiac_labs", "patientunitstayid"],
            ascending=[True, False, False, False, False, False, False, False, True],
        ).reset_index(drop=True)
        selected = idx.head(target).copy()
    else:
        selected = idx

    real_n = len(selected)
    shortfall = max(0, target - real_n)
    log.info("selected %d real cases; shortfall vs target = %d", real_n, shortfall)

    # assign sequential case numbers to real cases now (1..real_n)
    selected = selected.reset_index(drop=True)
    selected["case_number"] = selected.index + 1
    selected["case_id"] = selected["case_number"].map(C.case_id)
    selected["source_type"] = "real"

    selected.to_csv(STAGE / "cohort_selection.csv", index=False)
    if len(idx):
        idx.to_csv(STAGE / "eligible_index.csv", index=False)

    # Finalize: copy each selected stay's assembled record to a case-keyed file
    # under staging/assembled/<case_id>.json so all downstream stages key off
    # case_id (works uniformly for real and synthetic cases).
    final_dir = C.STAGING / "assembled"
    final_dir.mkdir(parents=True, exist_ok=True)
    for _, row in selected.iterrows():
        rec = C.read_json(ASM / f"{int(row['patientunitstayid'])}.json")
        rec["case_id"] = row["case_id"]
        rec["case_number"] = int(row["case_number"])
        C.write_json(final_dir / f"{row['case_id']}.json", rec)

    C.write_json(STAGE / "selection_summary.json", {
        "generated_at": C.now_iso(),
        "target": target,
        "eligible_total": int(len(idx)),
        "tier_counts": {t: int((idx.tier == t).sum()) if len(idx) else 0 for t in ("A", "B", "C")},
        "real_selected": int(real_n),
        "synthetic_shortfall": int(shortfall),
        "synthetic_fallback_allowed": bool(cfg["cohort"]["allow_synthetic_fallback"]),
    })
    log.info("=== Stage 04 complete: real=%d shortfall=%d ===", real_n, shortfall)
    print(f"real_selected={real_n} shortfall={shortfall}")


if __name__ == "__main__":
    main()
