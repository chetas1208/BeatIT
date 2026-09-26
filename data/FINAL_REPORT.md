# HeartTwin CareGuard — Final Dataset Report

**Target directory:** `/Users/shradha/hackathon/AbridgexClaude Hack/data`

## Source downloads
- **eICU Demo 2.0.1** — SQLite (82 MB gz → 296 MB), all relevant tables extracted (2,520 stays). ODbL.
- **PTB-XL 1.0.1** — metadata + 1,000 selected 100 Hz records (`.hea`/`.dat`). CC BY 4.0.
- **MIMIC-IV Demo 1.0** — separate validation cohort (100 patients; 83 with CV dx). Never mixed into the eICU cohort.
- **Synthea** — not required (0 synthetic; the real cohort met the target).

## Licenses & checksums
- 5/5 downloaded files SHA-256 verified against official `SHA256SUMS.txt` (incl. the eICU SQLite gz).
- License files preserved under `raw/*/LICENSE.txt`; see `LICENSES.md`, `CITATIONS.md`, `source_manifest.json`.

## Cohort selection
| Metric | Count |
|---|---|
| Eligible stays | 1,839 |
| Tier A / B / C | 1,429 / 106 / 304 |
| **Real eICU cases selected** | **1,000 (all Tier A)** |
| Synthetic fallback | 0 |
| **Structurally valid** | **1,000 / 1,000 (0 quarantined)** |

Validation includes the **real CareGuard `validate_bundle`** — every bundle is genuinely ingestible.

## Heart-related coverage
Hypertension 696 · Arrhythmia (AF+other) 528 · MI/ACS 285 · Heart failure 255 · Cardiac surgery 153 · Cardiac arrest 76 · Cardiomyopathy 36.

## Non-cardiac morbidity coverage (cardiovascular co-occurrence)
Mean 5.46 / median 5.0 non-cardiac organ systems per case.
Renal 560 · Pulmonary 803 · Hepatic 104 · Endocrine/metabolic 652 · Neurologic 608 · Hematologic 878 · Infectious 516 · Oncologic 209 · GI 564 · Other 302.

## Medication coverage
Original unique strings 2,135 · **normalized 2,121 (99.34 %)** · unresolved 14 · openFDA label evidence 973 · mean 60.8 meds/case · RxNorm coverage in FHIR 99.5 %.

## ECG coverage
1,000 PTB-XL records selected, downloaded, converted (CSV/JSON/PNG), **1,000 assigned, 0 failed**; every composite case carries the donor-linkage warning (`same_patient_as_ehr=false`).

## Echo coverage (matched external modality)
1,000 real EchoNet-Dynamic apical-4-chamber echo videos, **1,000 assigned, 0 failed** (video + frame PNG + animated GIF + donor-labeled EF/EDV/ESV). EF-category match: preserved 627 / reduced 247 / mid 126. `same_patient_as_ehr=false`; donor EF is never presented as the eICU patient's value. Added to each FHIR bundle as a US `DiagnosticReport`.

## File formats generated (per case, 37 files)
FHIR JSON · NDJSON · JSON · YAML · CSV · Parquet · TXT · PDF · C-CDA XML · WFDB HEA/DAT · ECG CSV · ECG PNG · DICOM Secondary Capture.

## Analysis outputs
`analysis/cohort_summary.{json,md}`, `cohort_quality_report.html`, 8 charts, plus organ/heart/medication/lab/ECG/FHIR/source CSVs. Mean completeness **0.927** (min 0.737, max 1.0).

## Validation results
1,000 / 1,000 pass structural + PHI + disclaimer + donor-warning + provenance + real-ingestion checks. **0 quarantined.**

## Known limitations
Composite modality linkage (ECG ≠ same patient as EHR) · ICU population bias · incomplete data (missing ≠ normal) · medication-normalization uncertainty (14 unresolved) · no same-patient imaging · 0 synthetic fallback.

## Final verdict
**DATASET READY FOR HEARTTWIN CAREGUARD SOFTWARE TESTING** — not clinically validated.
