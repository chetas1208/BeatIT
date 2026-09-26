# MIMIC-IV Clinical — BeatIT Field Map

**Source:** [MIMIC-IV](https://physionet.org/content/mimiciv/) · [Documentation](https://mimic.mit.edu/docs/iv/)  
**Linkage key:** `subject_id` (integer) — same id used by MIMIC-IV-ECG and MIMIC-IV-ECHO when those modules are licensed.

## BeatIT target → MIMIC-IV tables (hosp / icu)

| BeatIT need | MIMIC location | Notes |
|---|---|---|
| Age | `hosp/patients.csv` → `anchor_age`, `anchor_year_group` | De-identified age; use policy for year group |
| Sex | `hosp/patients.csv` → `gender` | |
| Height / weight | `hosp/omr.csv` (LOINC height/weight) or charted values | Often sparse; **MISSING** if absent |
| HR | `icu/chartevents.csv` (e.g. heart rate itemids) or `vitalsign` derived views | Prefer documented itemids; time-stamped |
| SBP / DBP | `icu/chartevents.csv` / vitals | Non-invasive BP itemids |
| Diagnoses | `hosp/diagnoses_icd.csv` + `hosp/d_icd_diagnoses.csv` | ICD codes + titles; cardiac filter by ICD/chapter |
| Medications | `hosp/prescriptions.csv`, `hosp/emar.csv`, `hosp/pharmacy.csv` | Map to BeatIT med list with start/stop times |
| Admissions / timeline | `hosp/admissions.csv`, `icu/icustays.csv` | Anchor encounters for temporal policy |
| Labs (optional) | `hosp/labevents.csv` | Not required for minimum demo |

## Temporal policy (required before case build)

For each BeatIT snapshot define an **anchor_time** (e.g. echo study time or ICU admit). Select vitals/ECG/meds/dx with documented windows; **no future leakage** (nothing recorded after anchor used for that snapshot).

## Existing repo touchpoints

- `data/scripts/mimic_validation_cohort.py` — aggregate stats on **MIMIC-IV Demo** only; separate validation cohort, not BeatIT demo identity.
- `data/raw/mimic-demo/` — expected demo layout (`core/patients.csv.gz`, `hosp/...`); **currently empty on this host**.

## Access on this machine

See Wave 1 handoff: **full MIMIC-IV not present**; credentialed download required before any real case mining.
