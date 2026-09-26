# Data lineage

The benchmark reads, but never modifies, the ~1,000 case directories under
`data/cases/`. Cases are composite research artifacts assembled from open
datasets by the repo's data pipeline (`data/source_manifest.json`).

## Source datasets

| Source | Version | License | Role in a case |
|---|---|---|---|
| eICU-CRD Demo | 2.0.1 | Open Database License (ODbL) 1.0 | EHR: diagnoses, medications, allergies, labs, vitals, treatments |
| PTB-XL | 1.0.1 | CC BY 4.0 | ECG modality (matched external — different individual) |
| EchoNet-Dynamic | — | research use | Echo modality (matched external — different individual) |
| RxNorm | (case snapshot) | UMLS terms | medication normalization in `medication-evidence/` |
| openFDA drug/label | (per-label effective dates) | public domain | drug-label evidence in `medication-evidence/label-evidence.json` |

## Per-case files used by the benchmark

- `manifest.json` — case metadata, source identifiers, tiers, disclaimers.
- `provenance.json` — field-level provenance (source table/row/column) for
  every fact; `provenance_coverage`.
- `quality.json` — completeness score and component coverage.
- `clinical/fhir-bundle.json`, `clinical/patient-summary.json` — normalized
  patient context.
- `ehr/*.csv` — diagnoses, medications, allergies, labs, vitals, treatments.
- `medication-evidence/normalized-medications.json` — RxNorm normalization.
- `medication-evidence/label-evidence.json` — openFDA label evidence (source
  for contraindication reference signals and the evidence packet).
- `analysis/multimorbidity-profile.json`, `organ-profile.json` — deterministic
  organ-system reconstruction.

## Provenance discipline

The reference set records, for every assertion, the source file and row/id it
was derived from (`reference/reference_provenance.ndjson`). The evidence packet
records source authority, title, version, effective date, section, exact
passage, identifier, retrieval timestamp, and a content hash. No answer label
is ever placed inside the evidence packet.

## Data boundary statement (must appear in every report)

> Research benchmark using deidentified, synthetic, or composite open-data
> cases. Not a clinical-validation study and not for diagnosis or treatment
> decisions. Where a case links a PTB-XL ECG to an eICU record, the ECG and EHR
> originate from different deidentified individuals and are combined only for
> multimodal software testing.
