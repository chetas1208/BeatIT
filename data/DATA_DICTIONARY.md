# Data Dictionary

Every field the HeartTwin CareGuard pipeline (and chatbot) may encounter.

## 1. Per-case directory — `cases/<case_id>/`

`case_id` is `case-NNNNNN` (zero-padded). One directory per packaged case.

### Root files
| File | Contents |
|---|---|
| `README.md` | Human-readable case description + disclaimers. |
| `manifest.json` | Case metadata, source labels, ECG linkage warning, file inventory. |
| `provenance.json` | Per-field provenance (source table/row/column, assertion type, confidence). |
| `quality.json` | Component + overall completeness scores and missingness warnings. |

**`manifest.json`** key fields: `case_id`, `source_type` (`real`/`synthetic`),
`real_patient_data` (bool), `source_dataset`, `source_identifier`
{`dataset`, `patientunitstayid`}, `license`, `selection_tier` (A/B/C),
`ecg_source`, `ecg_record_id`, `linkage_type` (`matched_external_modality`),
`same_patient_as_ehr` (**always false**), `match_features`, `ecg_warning`,
`fhir` {`resource_count`, `valid`}, `disclaimers`, `chatbot_contract`, `files`.

### `clinical/`
| File | Contents |
|---|---|
| `fhir-bundle.json` | **FHIR R4 Bundle** — the CareGuard ingestion payload. |
| `fhir-resources.ndjson` | One FHIR resource per line. |
| `patient-summary.{json,yaml,csv,parquet}` | Structured case summary (same data, four formats). |
| `patient-report.{txt,pdf}` | Source-grounded narrative report with disclaimers. |
| `ccda.xml` | Deterministic C-CDA-style export (problems/meds/allergies/results/vitals/procedures). |

### `ehr/` (full-fidelity source rows)
`patient.csv`, `diagnoses.csv`, `past-history.csv`, `medications.csv`,
`allergies.csv`, `labs.csv`, `vitals.csv`, `treatments.csv`, `notes.csv`.
- `diagnoses.csv`: `text, icd_code, priority, clinical_status,
  active_upon_discharge, offset, source_table, source_row_id, cv_categories,
  organ_systems`.
- `medications.csv`: `text, dosage, route, frequency, start_offset, stop_offset,
  status, source_table, source_row_id` (doses are copied verbatim, never inferred).
- `labs.csv`: `labname, canonical, loinc, group, value, text, unit, offset, …`.
- `vitals.csv`: `vital, loinc, unit, count, min, max, mean` (summary of the series).

### `ecg/` (present only when an ECG was assigned)
| File | Contents |
|---|---|
| `ecg.hea`, `ecg.dat` | Original PTB-XL WFDB record (100 Hz, 12-lead, mV) — waveform unmodified. |
| `ecg.csv` | `time_seconds, lead_I, lead_II, lead_III, aVR, aVL, aVF, V1..V6`. |
| `ecg.json` | Waveform arrays + sampling metadata. |
| `ecg.png` | 12-lead plot. |
| `ecg-secondary-capture.dcm` | Generated DICOM SC of the plot (Modality `OT`, not diagnostic). |
| `ecg-provenance.json` | `ecg_source, ecg_record_id, linkage_type, same_patient_as_ehr=false, match_features, warning, sampling_rate_hz, n_samples, duration_seconds, license`. |

### `medication-evidence/`
- `normalized-medications.json`: RxNorm normalization per unique med (`normalized_name,
  rxcui, tty, ingredients[], confidence, normalization_method, unresolved`).
- `label-evidence.json`: openFDA label evidence (`rxcui, label_id, set_id,
  effective_time, has_boxed_warning, has_contraindications, has_drug_interactions,
  excerpts`). Evidence only — never a recommendation.
- `unresolved-medications.json`: strings RxNorm could not confidently map.

### `analysis/`
`organ-profile.json`, `cardiovascular-profile.json`, `multimorbidity-profile.json`,
`timeline.json`, `completeness.json`.

## 2. FHIR mapping rules
- `Patient`: `gender` + `age-band` extension only. **No** name/address/telecom/identifier.
- `Condition`: `code.coding` from eICU ICD-9/ICD-10 (split into `icd-9-cm` / `icd-10-cm`
  systems); `code.text` = original diagnosis string; `clinicalStatus` from active/historical.
- `Observation` (labs): LOINC from the documented lab map; `valueQuantity` with UCUM unit.
- `Observation` (vitals): `assertion_type = derived_deterministically` (mean over series);
  BP as `component[]`.
- `MedicationStatement`: RxNorm `coding` when normalized (else empty); `text` = original.
- `AllergyIntolerance`, `Procedure`, `CarePlan`, `Goal`: text-based, provenance-tagged.
- `DiagnosticReport`: the external ECG, with `same_patient_as_ehr = false` in its extension.
- Every clinical resource carries a `careguard/provenance` extension with
  `source_dataset, source_table, source_row_id, source_column, assertion_type,
  confidence, mapping_rule_version, conversion_timestamp`.
- `Bundle.meta.tag`: `real-ehr-eicu`/`synthetic`, `research-only`, `composite-modalities`.

## 3. Organ-system & cardiovascular classification
- Non-cardiac organ systems: `renal, hepatic, pulmonary, endocrine_metabolic,
  neurologic, hematologic_coagulation, infectious, oncologic, gastrointestinal,
  musculoskeletal, psychiatric, obstetric, allergy_immunologic, other`.
- Cardiovascular categories: `heart_failure, cardiomyopathy,
  myocardial_infarction_acs, coronary_artery_disease, atrial_fibrillation,
  other_arrhythmia, bradycardia, tachycardia, heart_block, hypertension,
  hypotension, shock, cardiac_arrest, valvular_disease, cardiac_surgery, pci,
  thromboembolic_cv`.
- Classification uses the eICU `diagnosisstring` hierarchy prefix first, then
  documented keyword matching (`scripts/classify.py`). Nothing invents a diagnosis.

## 4. Selection tiers (`scripts/04_select_cohort.py`)
- **Tier A**: cardiovascular context + ≥2 non-cardiac organ systems + medication +
  lab + vital.
- **Tier B**: cardiovascular context + ≥1 non-cardiac organ + medication + lab + vital.
- **Tier C**: cardiovascular context + ≥1 non-cardiac organ + ≥2 of
  {medication, lab, vital, allergy/history, treatment}.
Ordered by completeness, organ breadth, medication count, renal/hepatic/pulmonary
and cardiac-lab availability, with `patientunitstayid` as a deterministic tie-break.

## 5. Quality scoring (`scripts/quality.py`, spec §13)
Components (each 0–1): `cardiac_context (0.18)`, `noncardiac_morbidity (0.15)`,
`medication_coverage (0.12)`, `lab_coverage (0.12)`, `vital_coverage (0.10)`,
`allergy_coverage (0.06)`, `treatment_coverage (0.07)`, `ecg_coverage (0.08)`,
`fhir_validation (0.06)`, `provenance_coverage (0.06)`. Overall = weighted sum,
clamped to [0,1]. `missingness_warnings` lists explicit gaps.

## 6. Cohort tables — `cohort/`
- `cohort_manifest.{csv,parquet,json}` — one row per case (demographics, tier,
  CV categories, organ counts, ECG, FHIR validity, completeness).
- `patient_features.{csv,parquet}` — analysis-ready numeric/boolean features
  (`organ_*`, `cv_*`, `lab_*`, `mean_hr/sbp/spo2`, `died_in_hospital`, …).
- Long tables: `diagnoses.csv, medications.csv, labs.csv, vitals.csv,
  allergies.csv, ecg_assignments.csv, provenance.csv`.

## 7. `ecg_assignments.csv`
`case_id, patientunitstayid, ecg_record_id, assigned, ecg_source, linkage_type,
same_patient_as_ehr(false), desired_bucket, ecg_bucket, ecg_primary_superclass,
ecg_rhythm, ecg_sex, ecg_age_band, match_features, sampling_rate_hz, n_samples,
duration_seconds, warning`.
