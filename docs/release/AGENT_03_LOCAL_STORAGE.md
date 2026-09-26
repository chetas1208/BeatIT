# M10.5 Agent 03 — Local Storage Architecture Audit

**Date:** 2026-09-26
**Scope:** Actual repository data directories, artifact roots, SQLite stores,
fixture conventions, provenance fields, and `.gitignore`.
**Change boundary:** Documentation only. No data was moved, deleted, rewritten,
or migrated during this audit.

## Verdict

The local demo has a real, file-backed SQLite persistence boundary, but it does
not have a populated local artifact root. The application can also fall back to
process-local memory for case state when Redis is not configured. These are
different guarantees and must not be presented as one durable storage system.

The checked-in `data/` tree is not equivalent to runtime storage: it contains
tracked research/analysis and imaging outputs, while raw, staging, case, cache,
log, artifact, and SQLite runtime locations are intended to remain outside Git.
The repository is therefore suitable for a synthetic/local demo only; a public
or patient-data deployment still needs explicit authentication, retention,
backup, access control, and persistent-volume verification.

## Observed filesystem inventory

All paths below were inspected from `/home/923873155/BeatIT`.

| Path | Observed state | Storage meaning |
|---|---|---|
| `data/beatit-ensembles.sqlite3` | Present; 221,184 bytes; mode `0600`; owner `923873155:domain users` | Live local SQLite database used by ensemble, Shadow Trial, and Missing Piece stores by default. |
| `data/artifacts/` | Absent | Default local artifact destination; it is created lazily by `LocalArtifactStore` on the first write. |
| `data/cases/` | Absent | Ignored runtime/raw case location; no local case files were observed. |
| `data/cache/` | Absent | Ignored runtime cache location. |
| `data/staging/` | Absent | Ignored ingestion/intermediate location. |
| `data/raw/` | Absent | Ignored raw-data location. |
| `data/logs/` | Absent | Ignored runtime log location. |
| `data/demo/state.json` | Present; 584 bytes; mode `0644` | Generated M10 demo metadata containing fixture hashes and synthetic-demo labels; not an application backup. |
| `fixtures/` | Present and populated | Versioned test/golden inputs, including synthetic cardiac fixtures and Shadow Trial contracts. |
| `data/cohort/`, `data/analysis/`, `data/imaging-cases/`, `data/vista-benchmark/` | Present and tracked | Research/benchmark outputs and manifests with their own source, license, linkage, and provenance boundaries. |
| `models/manifest.json` | Tracked; model weights are not | Provider/path metadata only; local weights are excluded by ignore rules. |

No additional `.sqlite`, `.sqlite3`, `.db`, WAL, or rollback database files
were found in the repository working tree. The audit was read-only; the absence
of `data/artifacts/` does not prove that an externally configured S3 bucket or
another deployment volume is empty.

## Runtime storage map

| Data surface | Default implementation | Configuration | Restart behavior | Release interpretation |
|---|---|---|---|---|
| Ensemble records | `SQLiteEnsembleStore` | `BEATIT_ENSEMBLE_STORE=sqlite`; `BEATIT_ENSEMBLE_DB_PATH` defaults to `data/beatit-ensembles.sqlite3` | Durable if the exact file and parent volume are retained | File-backed and tested locally; not authenticated multi-user storage. |
| Shadow Trial records | `SQLiteShadowTrialStore` | Shares `BEATIT_ENSEMBLE_DB_PATH` by default | Durable and create-once/immutable for a retained file | Must be backed up with ensembles as one SQLite consistency boundary. |
| Missing Piece records | `SQLiteMissingPieceStore` | `BEATIT_MISSING_PIECE_DB_PATH`, otherwise the ensemble path | Durable if the configured file is retained | May share the ensemble database or use a separate file; deployment must declare which. |
| Uploaded artifacts | `LocalArtifactStore` | `ARTIFACT_ROOT`, default `data/artifacts` | Durable only while the same filesystem/root is retained | Path traversal is rejected; writes are direct and lack a verified temp-file/rename protocol. |
| Optional uploaded artifacts | `S3ArtifactStore` | `AWS_ENABLED=true`, `AWS_REGION`, `AWS_S3_BUCKET`, deployment credentials | Depends on bucket policy, versioning, retention, and availability | Configuration is an adapter choice, not evidence that S3 is configured or reachable. |
| Case state | Redis when configured; `_MEMORY_STORE` otherwise | Redis configuration plus memory-enable policy | Redis may survive restart; process-local fallback is lost on restart | Readiness must not call the fallback durable. |
| CareGuard memory/audit state | Redis when configured; bounded process-local fallback otherwise | Redis configuration and TTL behavior | Fallback is not restart durable | Requires separate retention and deletion verification. |
| Demo metadata | `data/demo/state.json` | `scripts/seed-demo.sh` and `scripts/reset-demo.sh` | Regenerable from fixtures; not a record store | Safe synthetic fixture index, not a backup or patient-data export. |

The API constructs the three SQLite stores at import time. Each store opens a
connection per operation, rejects `:memory:`, creates its parent directory with
mode `0700`, and attempts to set the database file to mode `0600`. The default
SQLite path is relative, so a service definition must set an absolute path or
pin the working directory before treating it as a deployment contract.

## Observed SQLite contents

The existing database was opened read-only through SQLite's `mode=ro` URI. The
inventory was:

| Table | Rows | Notes |
|---|---:|---|
| `twin_ensembles` | 4 | JSON payloads include IDs, samples, distributions, warnings, and `provenance`. |
| `shadow_trials` | 2 | JSON payloads include immutable definition/pairing data, effects, fingerprint, warnings, and `provenance`. |
| `missing_piece_results` | 0 | The table exists, but no persisted Missing Piece analysis was present at audit time. |

The database is ignored by Git, so its rows cannot be restored from a checkout.
No backup copy, backup checksum, or restore drill was established by this
audit. SQLite mode protection is local filesystem hygiene only; it does not
provide encryption at rest, tenant isolation, authorization, or retention
enforcement.

## Artifact-root findings

`LocalArtifactStore` resolves keys below `ARTIFACT_ROOT` and rejects traversal
outside the resolved root. `store_file` generates a UUID file ID and writes
through the configured artifact provider. With no active blob/S3 provider, the
default target is `data/artifacts/<file-id>`.

The default root was absent during inspection, so there were no local uploaded
artifacts to inventory or restore. `LocalArtifactStore.put` creates parent
directories and writes the destination directly; an interrupted write or
concurrent read has not been proven safe. The legacy Vercel Blob branch also
builds a provider URL using the incoming filename, so filename validation and
upload limits remain deployment/security concerns documented elsewhere.

## Fixture conventions

The repository uses several intentionally different fixture classes:

1. `fixtures/hearttwin/` is generated by
   `scripts/create_synthetic_fixtures.py`, is synthetic/non-PHI, and carries
   `fixture_id`, descriptive labels, expected deterministic outputs, and safety
   notes. Generation is idempotent.
2. `fixtures/golden/probabilistic/` contains deterministic ensemble request and
   response contracts. Inputs carry origin snapshot/state, seed, sample count,
   parameter distribution families/bounds, sources, evidence IDs, rationale,
   and version fields.
3. `fixtures/golden/shadow_trials/` binds a baseline fixture to a bounded
   scenario. The checked-in `fixed-baseline-afterload.json` records engine
   version, expected trial ID/fingerprint, pair counts, deltas, and effect
   medians. `synthetic-demo-case.json` explicitly labels its origin synthetic
   and requires the safety disclaimer.
4. `fixtures/longitudinal/` defines replay streams as synthetic events with
   `synthetic_replay` and `REPLAY`/`DEMO STREAM` provenance.
5. `data/` research and imaging manifests are not interchangeable with the
   synthetic demo fixtures. For example, the inspected imaging manifest marks
   `real_ct: true`, records the source dataset/subject, states that the scan is
   not linked to a clinical record, and includes a deidentified-benchmark
   disclaimer. The composite cohort README separately warns that modalities
   may come from different deidentified individuals.

`data/demo/state.json` hashes only the three canonical M10 demo inputs:
`fixtures/hearttwin/manual_baseline.json`,
`fixtures/golden/probabilistic/fixed-only.json`, and
`fixtures/golden/shadow_trials/synthetic-demo-case.json`. It does not hash the
SQLite database, uploaded files, research datasets, or model weights.

## Provenance fields audited

The storage layer persists JSON payloads without flattening their application
lineage. The principal contracts expose:

| Contract | Important identity/lineage fields |
|---|---|
| `EnsembleProvenance` | `origin_snapshot_id`, `origin_timestamp`, `origin_quality`, `origin_provenance`, `parent_scenario_id`, `evidence_ids`, `seed`, `physiology_version`, `distribution_config_version`, `prior_version`, `created_at`, and assumptions. |
| `ShadowTrialProvenance` | Origin quality/provenance, evidence IDs, seed, physiology/ensemble/prior versions, creation time, assumptions, provenance schema version, engine/effect-metrics versions, and pairing policy. |
| `SensitivityProvenance` | Source, `analysis_id`, `ensemble_id`, optional `shadow_trial_id`, model version, sensitivity method, and assumptions. |
| `EvidenceValueProvenance` | Source, evidence-map version, optional analysis ID, and assumptions. |
| `MissingPieceProvenance` | Analysis ID, linked ensemble/Shadow Trial IDs, method/version fields, assumptions, and limitations on the response. |
| CareGuard/FHIR provenance | Resource target, recorded time, activity, software agent, source dataset/subject metadata, assertion type, and linkage status where applicable. |

The storage audit found no evidence that these fields are encrypted,
authorization-filtered, or uniformly scrubbed before persistence. The Missing
Piece store rejects a defined set of sensitive key names, but that is not a
general privacy boundary for all stores or uploaded bytes. Provenance must
remain visible and truthful: `synthetic`, `synthetic_replay`, real
deidentified benchmark, and model-derived states must not be collapsed into a
single patient-like record.

## `.gitignore` and trackedness

The ignore rules correctly exclude or protect the main runtime/data hazards:

- `data/cases/`, `data/cache/`, `data/staging/`, `data/raw/`, `data/logs/`, and
  `data/artifacts/` are ignored.
- `data/beatit-ensembles.sqlite3` and its SQLite sidecars are ignored.
- Model directories are ignored except `models/manifest.json`; weight formats
  such as `.pt`, `.safetensors`, `.gguf`, and `.onnx` are ignored.
- Upload-like formats (`*.pdf`, `*.dcm`, `*.nii`) and environment/credential
  files are ignored.

The rules do not make every existing `data/` file private: tracked files remain
tracked even if later rules would ignore their path. The current checkout
tracks research/analysis manifests, cohort tables, imaging-case metadata, and
benchmark outputs under `data/`. Their licensing, deidentification, and
composite-linkage claims must therefore be reviewed independently of the local
runtime storage policy. `data/demo/state.json` is currently an untracked
generated file and is not covered by a dedicated ignore rule.

## Release actions and open risks

Before any deployment handling non-synthetic or user-uploaded data:

- Set absolute paths for the SQLite database and artifact root on explicitly
  persistent volumes.
- Decide whether ensembles, Shadow Trials, and Missing Piece records share one
  SQLite consistency boundary or use separate files; back up the declared
  boundary atomically.
- Prove a write/restart/read round trip against the actual service, plus a
  backup/restore drill and disk-full behavior.
- Configure authenticated ownership/tenant checks, restricted CORS, upload
  size/type validation, retention/deletion policy, and encrypted transport and
  storage as appropriate.
- Treat Redis and S3 reachability, retention, and backup as deployment gates;
  do not promote in-process fallbacks to durable status.
- Add a deliberate policy for generated `data/demo/state.json` (keep as a
  disposable local artifact or ignore it) and ensure release archives do not
  accidentally include runtime stores or raw data.
- Validate all provenance fields and safety disclaimers after persistence and
  rehydration, including synthetic/composite/deidentified labels.

**Final storage gate:** PASS for the bounded synthetic local demo primitives;
OPEN for public, multi-user, patient-data, or disaster-recovery deployment.

## Evidence commands

Read-only commands used for this audit included:

```bash
find . -type f \( -name '*.sqlite' -o -name '*.sqlite3' -o -name '*.db' -o -name '*.db-*' \)
git ls-files data fixtures models/manifest.json
git check-ignore -v --no-index data/beatit-ensembles.sqlite3 data/artifacts/foo
```

The SQLite inventory used a read-only URI (`file:<path>?mode=ro`) and queried
table names, row counts, and payload keys only; no row or filesystem mutation
was performed.
