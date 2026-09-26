# Licenses & Attribution

This dataset redistributes and transforms data from the sources below. Their
license files are preserved under `raw/<source>/LICENSE.txt`. Downstream users
must honour each source's terms and cite the original works (see `CITATIONS.md`).

## eICU Collaborative Research Database Demo, v2.0.1
- **License:** Open Database License (ODbL) v1.0.
- **Source:** https://physionet.org/content/eicu-crd-demo/2.0.1/
- **Preserved:** `raw/eicu-demo/LICENSE.txt`, `raw/eicu-demo/SHA256SUMS.txt`.
- **Use here:** primary real, deidentified structured EHR (diagnoses, medications,
  labs, vitals, allergies, treatments, care plans).
- **Attribution requirement:** attribute the eICU-CRD and preserve the ODbL notice
  in any redistribution.

## PTB-XL, a large publicly available electrocardiography dataset, v1.0.1
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Source:** https://physionet.org/content/ptb-xl/1.0.1/
- **Preserved:** `raw/ptb-xl/LICENSE.txt`, `raw/ptb-xl/SHA256SUMS.txt`.
- **Use here:** real, deidentified 12-lead ECG signals, matched to cases as an
  **external modality** (different individuals than the eICU records).
- **Attribution requirement:** credit the PTB-XL authors (CC BY 4.0).

## MIMIC-IV Clinical Database Demo, v1.0
- **License:** Open Data Commons Open Database License v1.0.
- **Source:** https://physionet.org/content/mimic-iv-demo/1.0/
- **Preserved:** `raw/mimic-demo/LICENSE.txt`, `raw/mimic-demo/SHA256SUMS.txt`.
- **Use here:** SEPARATE validation cohort only — its patients are **never** counted
  in the eICU main cohort.

## Synthea
- **License:** Apache License 2.0.
- **Source:** https://github.com/synthetichealth/synthea
- **Use here:** synthetic fallback only (if the real cohort falls short of target).
  Any Synthea record is labeled `source_type: synthetic`, `real_patient_data: false`.

## Terminology / API services (metadata only)
- **RxNorm / RxNav** (U.S. National Library of Medicine) — medication normalization.
- **openFDA drug label API** (U.S. FDA) — public label evidence (contraindications,
  boxed warnings, interactions). Evidence is stored, never interpreted as a
  patient-specific recommendation during dataset construction.

## This packaged dataset
Transformations (FHIR, C-CDA, reports, DICOM SC, analysis) are deterministic
derivatives of the above sources. They inherit the source licenses; the derived
FHIR/analysis code and scripts may be used under the same terms as the parent
HeartTwin CareGuard repository.
