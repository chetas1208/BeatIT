# Campaign Agent 07 — Local Data Inventory and Identity Boundary

**Audit date:** 2026-09-26 UTC  
**Scope:** local files under `/home/923873155/BeatIT`; BeatIT data, fixtures,
existing real/public-derived artifacts, FHIR, ECG, echo, CT/imaging, manifests,
and provenance.  
**Change boundary:** this audit adds only this document. No code, fixture,
dataset, model, credential, or external data was changed or downloaded.

## Executive disposition

The repository contains three materially different data surfaces and they must
not be described as one cohort:

1. **Synthetic BeatIT data is the strongest locally reproducible surface.** The
   checked-in `data/synthetic_cohort_500/` contains 500 profiles, 500 FHIR
   bundles, 500 derived pipeline results, 166 synthetic ECG CSVs, and a
   SQLite persistence copy. Every profile is explicitly synthetic and the
   cohort verifier passes all checks.
2. **Real/public source-derived cohort artifacts are present as aggregate and
   assignment tables, not as a locally complete raw corpus.** The 1,000-row
   `data/cohort/` tables identify the main source as real eICU data and attach
   PTB-XL ECG and EchoNet-Dynamic echo as matched external modalities. However,
   the current checkout has no `data/raw/`, `data/staging/`, or `data/cases/`
   tree and no local WFDB, echo-video, or per-case FHIR payload for that
   1,000-case surface. These are provenance-backed derived claims, not a
   locally re-runnable raw-data inventory.
3. **Standalone real/public imaging is locally packaged but identity-isolated.**
   Three real, deidentified TotalSegmentator CT cases and three reference masks
   are present with imaging-only FHIR bundles. Each explicitly has
   `same_subject_as_clinical_record=false`; none is linked to an eICU or
   synthetic clinical identity. VISTA predictions were not produced because
   the endpoint was unavailable.

The safe current language is therefore: **synthetic cohort locally executable;
real/public-derived clinical tables locally inspectable; standalone real CT
benchmark locally present; cross-modal identity linkage absent and prohibited.**

## Classification rule

This report uses the following labels:

| Label | Meaning in this audit | Identity rule |
|---|---|---|
| **Synthetic** | Values generated for tests, demos, deterministic cohort generation, or explicitly synthetic stand-ins. | Synthetic IDs are not real people and are never linked to real/public IDs. |
| **Real/public** | A local artifact declares that it derives from a deidentified public corpus or is a packaged deidentified public image. | A source-native identifier is not evidence of identity across datasets. |
| **Reference** | A source citation, validation summary, source manifest, canonical URL, license record, or benchmark reference used for provenance or comparison. | Reference metadata is not a patient record and does not imply that the source payload is local. |
| **Derived/aggregate** | A table, report, assignment, chart, or validation result generated from another data surface. | It inherits the upstream provenance claim but cannot substitute for missing raw payloads. |

## Inventory matrix

| Local surface | Classification | Present locally | Identity/provenance finding | Audit status |
|---|---|---:|---|---|
| `data/synthetic_cohort_500/` | Synthetic | Yes; 500 profiles plus derived/FHIR/SQLite/ECG artifacts | `manifest.json` says synthetic, seed `20260926`, 500 unique profiles, 250 longitudinal profiles, and no cross-source identity mixing. | **PASS** for local synthetic use |
| `fixtures/hearttwin/`, `fixtures/golden/`, `fixtures/longitudinal/` | Synthetic | Yes | The fixture README says all values are synthetic; public dataset names are structural inspiration only. | **PASS**; do not call public data |
| `fixtures/careguard/cardiorenal-bundle.json` | Synthetic | Yes | Explicit `synthetic` bundle tag; contains intentionally fake patient-like fields for parser testing. | **PASS** as a synthetic fixture; not PHI or a real patient |
| `fixtures/careguard/corpus/` | Synthetic/reference stand-ins | Yes | The corpus notice says passages and medication-source entries are synthetic stand-ins with canonical URLs, not copied official text. | **PASS** only for offline demo retrieval |
| `data/cohort/` | Real/public-derived aggregate | Yes; 1,000-row manifest and long tables | `source_type=real`, eICU fields, PTB-XL assignments, and EchoNet assignments are recorded, but source payload trees are absent from this checkout. | **PARTIAL**; provenance present, raw re-verification unavailable |
| `data/analysis/` | Derived/reference | Yes | Contains cohort summaries, validation reports, and a MIMIC validation summary. These are outputs, not raw source datasets. | **PARTIAL**; distinguish report claims from local payload presence |
| `data/imaging-cases/` | Real/public standalone imaging | Yes; 3 CTs, 3 masks, 3 imaging FHIR bundles | TotalSegmentator source and subject IDs are recorded; all cases are `imaging_only` and explicitly not linked to clinical records. | **PASS** for isolated imaging benchmark |
| `data/vista-benchmark/` | Reference/benchmark metadata | Yes | Manifests point to the three packaged CT cases; metrics show no VISTA prediction and no computed Dice/HD95 values. | **PASS** for honest unavailable-endpoint state |
| `data/source_manifest.json`, `data/CITATIONS.md`, `data/LICENSES.md` | Reference/provenance | Yes | They document eICU, PTB-XL, MIMIC-IV, and Synthea roles/licenses; citations do not prove current payload presence. | **PASS** as documentation; reconcile with filesystem before claiming availability |

## Synthetic BeatIT cohort

The checked-in synthetic cohort is the only broad multimodal data surface that
is self-contained enough for a local inventory and restart check:

- `data/synthetic_cohort_500/manifest.json` records 500 profiles, 500 persisted
  rows, 500 FHIR-valid bundles, 500 successful BeatIT ingestions, 166 synthetic
  ECG cases, and 250 longitudinal profiles.
- The category counts are 200 baseline, 100 hemodynamic, 70 electrical, 60
  structural, 40 mixed, and 30 stress-test profiles.
- `profiles/` has 500 synthetic profiles; `fhir/` has 500 FHIR R4-shaped
  collection bundles; `derived/` has 500 pipeline result JSON files; and
  `beatit_cohort.sqlite3` has one `profiles` table with 500 rows.
- The 166 ECG files are generated CSV waveforms. The other 334 profiles have no
  ECG waveform and explicitly use the no-waveform path. All 500 profiles carry
  synthetic provenance; no profile carries an external source identifier.
- The profile surface includes synthetic echo metadata, but it does not contain
  500 echo videos. The FHIR resource inventory is 500 `Patient`, 500
  `Encounter`, and 3,000 `Observation` resources; no synthetic echo video or
  DICOM echo payload was found.
- `data/synthetic_cohort_500/checksums.json` covers the SQLite database and the
  500 derived result files. The repository verifier re-read the database from a
  separate process and checked physiological volume/EF invariants.

The synthetic FHIR bundles use `https://beatit.local/synthetic` coding and a
`synthetic_demo` bundle tag. These are contract-test resources, not claims about
an observed patient. The `seed` field is a generator seed, not a patient or
source identifier.

## Existing real/public-derived clinical corpus

### eICU-derived EHR tables

`data/cohort/cohort_manifest.csv` has 1,000 rows and marks all rows
`source_type=real` and `real_patient_data=True`. The associated tables include
diagnoses, medications, labs, vitals, allergies, patient features, provenance,
and FHIR validation summaries. `data/analysis/cohort_summary.json` reports
1,000 real eICU cases, 100% FHIR bundle validity, and zero reference-resolution
failures in the historical pipeline output.

Those facts must be qualified by the current filesystem state. There is no
`data/raw/`, `data/staging/`, or `data/cases/` directory in this checkout. The
individual eICU FHIR bundles, source SQLite, per-case EHR exports, and source
license files described by `data/README.md` are therefore not locally
available now. The aggregate CSV/JSON/Parquet tables are useful for schema and
analysis inspection, but they do not prove that the underlying raw corpus can
be regenerated from this checkout.

### PTB-XL ECG assignment table

`data/cohort/ecg_assignments.csv` contains 1,000 assigned records, all marked
`ecg_source=PTB-XL`, `linkage_type=matched_external_modality`, and
`same_patient_as_ehr=False`. The historical analysis reports broad matching on
age band, sex, and cardiac category, not patient linkage.

No PTB-XL WFDB record is locally present under `data/` or `fixtures/`: no
`.hea`/`.dat` pair was found. The two ECG waveform CSVs under
`fixtures/hearttwin/` and the 166 CSVs under the synthetic cohort are synthetic
and must not be substituted for PTB-XL records.

### EchoNet-Dynamic assignment table

`data/cohort/echo_assignments.csv` contains 1,000 assigned EchoNet-Dynamic
records, all marked as matched external modalities with
`same_patient_as_ehr=False`. The table carries donor EF/EDV/ESV and a warning
that these measurements belong to the echo donor, not the eICU record.

No EchoNet-Dynamic video, frame, GIF, or per-case echo provenance file was
found locally. The `echo_metadata_*.json` files in `fixtures/hearttwin/` are
synthetic metadata fixtures, not EchoNet source content. The echo assignment
table therefore supports an explicit external-donor boundary, not local echo
payload availability.

### MIMIC-IV reference cohort

`data/analysis/mimic_validation_cohort.json` records a 100-patient MIMIC-IV
Demo validation summary and explicitly says it is separate from the eICU main
cohort. It is a **reference/validation summary**, not a second BeatIT clinical
cohort. No local MIMIC raw tree is present. MIMIC counts must not be added to
the 1,000-row eICU-derived manifest.

## Standalone real/public CT and imaging

Three packaged cases are present under `data/imaging-cases/`, all from
TotalSegmentator:

- Each case contains a normalized `ct.nii.gz`, a `reference_mask.nii.gz`, an
  imaging-only FHIR bundle, an imaging provenance resource, source metadata, and
  a case manifest.
- The case manifests set `real_ct=true`, `has_reference_mask=true`,
  `case_type=imaging_only`, `linkage_status=imaging_only`, and
  `same_subject_as_clinical_record=false`.
- The source metadata identifies a deidentified TotalSegmentator subject and
  records CC BY 4.0 attribution information. The clinical FHIR subject label
  says it is not an eICU patient.
- The associated VISTA job records `endpoint_reachable=false`, a gated failure,
  no output paths, and no invented masks or measurements. The benchmark metrics
  consequently mark whole-heart/aorta comparisons `not_computed`; unsupported
  structures are `not_applicable`.

There is a manifest reconciliation item here: `data/imaging_source_manifest.json`
and its CSV set `local_present=false` for the TotalSegmentator source, while
the three packaged case payloads are present. This is consistent only if
`local_present` means “original source tree available,” not “derived benchmark
payload available.” The distinction should be retained until the source-level
manifest is updated by its owner; this audit does not modify it.

The CT cases are not evidence of same-patient cardiac imaging, and their
reference masks are not clinical diagnoses. They are safe to use only as an
isolated imaging/VISTA benchmark surface.

## FHIR inventory and identity separation

| FHIR surface | Local count | Classification | Identity boundary |
|---|---:|---|---|
| Synthetic cohort bundles | 500 | Synthetic | `synthetic_demo` tag; synthetic profile IDs only |
| Standalone imaging bundles | 3 | Real/public imaging benchmark | Imaging subject only; not linked to clinical record |
| eICU-derived clinical bundles | Not present as individual files | Real/public-derived claim | Only aggregate validation and manifest artifacts remain locally |
| `fixtures/careguard/cardiorenal-bundle.json` | 1 | Synthetic fixture | Explicit synthetic tag; patient-like fields are fake parser inputs |

The historical 1,000-case eICU FHIR resource counts in
`data/analysis/cohort_summary.json` must not be confused with 1,000 local FHIR
files. Likewise, the synthetic FHIR bundles use BeatIT-local coding and cannot
be mixed into the eICU-derived `data/cohort/` tables without an explicit
synthetic source label.

## Provenance and manifest reconciliation

The main provenance risk is not an observed identity collision; it is a stale
or relocated-source claim:

- `data/source_manifest.json` contains historical download records with
  absolute paths rooted at another machine (`/Users/.../data/raw/...`). Those
  paths do not resolve under this checkout.
- `data/analysis/download_verification.csv` reports historical source files as
  present and officially checksum-verified, but a current filesystem check finds
  no `data/raw/` directory. Treat those rows as historical pipeline evidence,
  not current local availability.
- `data/README.md`, `data/FINAL_REPORT.md`, and the analysis summaries describe
  a 1,000-case eICU/PTB-XL/EchoNet package. Their claims are useful provenance
  context, but the absent raw/per-case payloads lower the current local audit
  status to **PARTIAL** for that surface.
- `data/imaging_source_manifest.json` records controlled-access candidates
  (MultiD4CAD, ImageCAS, TCIA, RAD-ChestCT) as unavailable or access-pending.
  Those datasets are not local and must not be implied by the three
  TotalSegmentator benchmark cases.
- `data/CITATIONS.md` and `data/LICENSES.md` are attribution references. They
  do not grant access to missing source payloads and do not change synthetic
  fixtures into real data.

No local file inspected in this audit establishes a cross-source identity link.
The eICU `patientunitstayid`, PTB-XL `ecg_record_id`, EchoNet `echo_id`, and
TotalSegmentator subject IDs are separate namespaces. They must remain separate
even when aggregate tables use broad matching features or shared case rows.

## Local verification evidence

Commands were run from `/home/923873155/BeatIT` without printing credential or
secret values:

```text
python scripts/verify_cohort_500.py
PROFILES                 PASS
UNIQUE_IDS               PASS
SYNTHETIC                PASS
MANIFEST_COUNT           PASS
FHIR                     PASS
INGESTION                PASS
DATABASE                 PASS
RESTART_READBACK         PASS
PROVENANCE               PASS
PHYSIOLOGICAL_INVARIANTS PASS
CHECKSUMS                PASS
COHORT READY
```

Additional read-only inventory checks established:

- `data/synthetic_cohort_500/`: 500 profiles, 500 FHIR bundles, 500 derived
  results, 166 ECG CSVs, and one SQLite database with 500 rows.
- `data/cohort/cohort_manifest.csv`: 1,000 rows, all marked real; ECG and echo
  assignment tables each contain 1,000 rows and mark same-patient linkage
  false.
- `data/imaging-cases/`: three CT volumes, three reference masks, and three
  imaging-only FHIR bundles; no live VISTA prediction files.
- Filesystem presence: `data/raw/`, `data/staging/`, `data/cases/`,
  `data/logs/`, `data/cache/`, and `data/quarantine/` are absent.

## Handoff boundaries

For downstream agents and demos:

- Use `data/synthetic_cohort_500/` and `fixtures/` for deterministic local
  execution, replay, parser, and schema tests.
- Use `data/cohort/` only as a provenance-backed derived-table surface unless
  the missing raw/per-case source payloads are restored and independently
  verified.
- Use `data/imaging-cases/` only as three standalone real CT benchmark cases;
  never attach them to eICU, MIMIC, or synthetic profiles.
- Keep PTB-XL and EchoNet donor warnings visible whenever the derived assignment
  tables are used.
- Keep MIMIC in the reference/validation namespace and keep Synthea in the
  synthetic-fallback namespace. Neither is part of the local 1,000-row eICU
  manifest.
- Do not infer normality from absent ECG, echo, imaging, FHIR, laboratory, or
  longitudinal payloads. Missing local source files are an inventory gap, not a
  clinical negative.

**Final status:** **PASS** for synthetic and isolated imaging inventory;
**PARTIAL** for the real/public-derived clinical corpus because its aggregate
manifests and reports are present but its raw and per-case payload trees are not
present in the current local checkout.
