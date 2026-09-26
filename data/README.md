# HeartTwin CareGuard — Composite Cardiovascular Multimorbidity Dataset

A reproducible, provenance-preserving research dataset of up to **1,000 complete
cases** centered on cardiovascular disease with multimorbidity, assembled from
**real, deidentified open datasets** and packaged for the HeartTwin CareGuard
ingestion pipeline.

> **Research and software-testing dataset. Not for diagnosis or treatment decisions.**
> Composite modalities may originate from different deidentified individuals.
> This package is **not** clinically validated and is **not** a medical device.

---

## 1. Data contract for the CareGuard chatbot

### What is real
- **eICU structured EHR** — real, deidentified ICU stays from the
  eICU Collaborative Research Database Demo 2.0.1 (PhysioNet). Diagnoses,
  medications, labs, vitals, allergies, and treatments are the recorded source
  facts.
- **PTB-XL ECG signals** — real, deidentified 12-lead ECG recordings (PhysioNet).
- **EchoNet-Dynamic echo** — real, deidentified apical-4-chamber echocardiography video
  (Stanford). Attached per case as a **matched external modality** (`same_patient_as_ehr:
  false`); its EF/EDV/ESV are the **echo donor's** measurements, never the eICU patient's.

### What is synthetic or transformed
- **FHIR R4 bundles** (`clinical/fhir-bundle.json`) are deterministic
  transformations of the eICU record.
- **C-CDA files** (`clinical/ccda.xml`) are deterministic exports.
- **PDF/TXT reports** are source-grounded generated summaries (no advice, no
  invented facts).
- **DICOM Secondary Capture** (`ecg/ecg-secondary-capture.dcm`) is a generated
  ECG-image wrapper for format testing — *not a diagnostic image*.
- **ECG-to-EHR pairing** is an artificial software-testing match on broad,
  non-identifying features. It is **not** patient linkage.
- **Synthea** records (only if used to fill a shortfall) are synthetic and
  labeled `source_type: synthetic`, `real_patient_data: false`.

### What must NEVER be claimed
The chatbot must never state that:
- the ECG belongs to the eICU patient, or that all modalities came from one patient;
- an absent morbidity is ruled out, or that missing data means normal;
- the dataset proves clinical safety or is suitable for real patient care;
- a medication caused an outcome, or is contraindicated without supporting evidence.

### Required phrasing
- General: *"This is a composite research case assembled from deidentified open
  datasets for software testing."*
- When an ECG is present: *"The ECG is a matched external modality from PTB-XL and
  does not originate from the same individual as the eICU record."*
- For any synthetic fallback case: *"This case was generated with Synthea and is
  not a real patient record."*

---

## 2. How CareGuard ingests this dataset

The CareGuard pipeline ingests **FHIR R4 Bundles** via `POST /api/v1/careguard/fhir/import`
(the `bundle` field), or by dropping a bundle into `fixtures/careguard/<id>.json`
and importing by `fixture_id`. Each case's `clinical/fhir-bundle.json` is a
ready-to-ingest bundle:

- One `Patient` (gender + age-band only — **no PHI**), one `Encounter`.
- `Condition`, `Observation` (labs + vitals), `MedicationStatement`,
  `AllergyIntolerance`, `Procedure`, `CarePlan`/`Goal`, and a `DiagnosticReport`
  for the external ECG.
- Standard code systems only (`icd-10-cm`/`icd-9-cm`, `loinc`, `rxnorm`, `ucum`);
  codes are never invented — unmapped concepts use `{"coding": [], "text": ...}`.
- Provenance on every clinical resource via a `careguard/provenance` extension,
  and dataset labeling via `Bundle.meta.tag`.

A convenience manifest of all bundle paths is written to
`cohort/cohort_manifest.json`.

---

## 3. Directory layout

```
data/
  README.md  DATA_DICTIONARY.md  LICENSES.md  CITATIONS.md
  source_manifest.json  pipeline_config.yaml  requirements-data.txt
  raw/        eicu-demo/ ptb-xl/ mimic-demo/ synthea/     (downloaded sources + licenses)
  staging/    intermediate parquet/json (eicu, ptb-xl, fhir, medication-normalization)
  cases/      case-000001 ... case-00NNNN   (packaged multimodal cases)
  cohort/     cohort_manifest.* patient_features.* diagnoses/medications/labs/vitals/allergies/ecg/provenance.csv
  analysis/   cohort_summary.* charts/ *.csv cohort_quality_report.html validation_*
  scripts/    00..12 pipeline stages + run_all.sh
  logs/ cache/ quarantine/
```

Each `cases/<id>/` contains `clinical/`, `ehr/`, `ecg/`, `medication-evidence/`,
`analysis/`, plus `manifest.json`, `provenance.json`, `quality.json`, `README.md`.
See `DATA_DICTIONARY.md` for every field.

---

## 4. Reproducing the dataset

```bash
cd data
./scripts/run_all.sh          # bootstraps venv, downloads, builds, validates
```

The pipeline is idempotent and resumable: verified downloads and cached
normalizations/ECGs are skipped. Fixed seeds (see `pipeline_config.yaml`) make
selection deterministic. Final counts and the analysis report path are printed at
the end and captured in `logs/run_all.log`.

## 5. Sources & licenses

- **eICU-CRD Demo 2.0.1** — Open Database License (ODbL) 1.0.
- **PTB-XL 1.0.1** — Creative Commons Attribution 4.0 (CC BY 4.0).
- **MIMIC-IV Demo 1.0** — separate validation cohort only (never mixed into the
  eICU cohort).
- **Synthea** — Apache 2.0 (synthetic fallback only).

See `LICENSES.md` and `CITATIONS.md`. Cohort statistics are in
`analysis/cohort_summary.md` / `analysis/cohort_quality_report.html`.

---

## 6. Known limitations

- **Composite modality linkage** — ECG and EHR are different deidentified
  individuals, matched on broad features only.
- **ICU population bias** — eICU is critical-care data; not representative of
  ambulatory populations.
- **Incomplete data** — missing values are common and do not imply "normal".
- **Medication normalization uncertainty** — RxNorm mapping is best-effort;
  unresolved strings are recorded, not guessed.
- **No same-patient imaging** — no CT/MRI/echo is fabricated or claimed.
- **Synthetic fallback** — count reported separately; the whole cohort is never
  described as fully real if any synthetic cases are present.
