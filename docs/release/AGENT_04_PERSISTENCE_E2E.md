# M10.5 Agent 04 — Persistence E2E Verification

**Scope:** safe local write/read/reload verification for the ensemble, Shadow
Trial, Missing Piece, and artifact stores.

**Date:** 2026-09-26

**Disposition:** **PASS for isolated local file-backed persistence; OPEN for
deployed and external-provider persistence.**

## Safety boundary

The verification used Python's `TemporaryDirectory` only. The probe did not
open, modify, delete, or restart the repository's existing databases, artifact
roots, Docker services, or application processes. Temporary targets were
automatically removed after the probe completed.

The payloads were generated from the checked-in synthetic replay fixture and
the synthetic Shadow Trial fixture. No patient data, credentials, or external
services were used.

## E2E procedure

The writer process:

1. Loaded `fixtures/golden/probabilistic/synthetic-replay.json`.
2. Ran the deterministic ensemble engine and validated an `EnsembleResponse`.
3. Ran the synthetic afterload Shadow Trial with three effect metrics.
4. Ran Missing Piece for `stroke_volume_ml`.
5. Persisted all three JSON records into a temporary SQLite database.
6. Wrote a JSON report through `LocalArtifactStore` under a temporary artifact
   root.

A separate reader process then constructed new store instances against those
same temporary paths, read every record, revalidated the ensemble contract,
read the artifact, and checked artifact existence.

## Evidence

The isolated writer/reader probe produced:

```text
writer returncode= 0
{"phase": "write", "ensemble_id": "ensemble-6f5f02cd6a84", "trial_id": "shadow-trial-7c63f8759730", "analysis_id": "missing-piece-bbdee9fc2ce3", "ensemble_samples": 3, "shadow_trial_records": 3, "missing_piece_sensitivities": 5}
reader returncode= 0
{"phase": "separate-process-reload", "ensemble_read": true, "shadow_trial_read": true, "missing_piece_read": true, "artifact_read": true, "artifact_exists": true, "validated_ensemble": true}
{"database_mode": "0o600", "artifact_mode": "0o644", "temporary_root_cleaned": true}
```

The temporary SQLite database was therefore readable by a new process and had
the store's expected owner-only mode. The local artifact store successfully
round-tripped the bytes and existence check. Artifact file mode remains the
platform's normal file-creation mode (`0644` in this probe); deployments must
place the artifact root behind appropriate filesystem permissions and access
controls.

## Supporting regression coverage

```text
python -m pytest -q \
  python/hearttwin/tests/test_ensemble_store.py \
  python/hearttwin/tests/test_shadow_trial_store.py \
  python/hearttwin/tests/test_missing_piece_store.py

21 passed in 1.09s
```

Those focused tests additionally cover store recreation, ensemble replacement,
Shadow Trial and Missing Piece immutability, JSON validation, invalid IDs,
non-finite payload rejection, and rejection of `:memory:` databases where
durability would be misleading.

## Verified storage paths

| Surface | Local implementation | Result |
| --- | --- | --- |
| Ensemble | `SQLiteEnsembleStore` | PASS: generated record survived separate-process reload and contract validation |
| Shadow Trial | `SQLiteShadowTrialStore` | PASS: generated paired record survived separate-process reload |
| Missing Piece | `SQLiteMissingPieceStore` | PASS: generated analysis survived separate-process reload and canonical validation |
| Artifact | `LocalArtifactStore` | PASS: bytes and existence survived a new store instance and separate-process boundary |

## Release boundary

This evidence does not prove PostgreSQL, Valkey/Redis, S3, container-volume,
reverse-proxy, backup/restore, disk-full, concurrent-writer, or deployed
restart behavior. It also does not establish authentication, tenant isolation,
retention, deletion, or patient-data suitability. The overall release remains
**DO NOT SHIP** until the selected deployment persistence configuration is
exercised with a controlled restart and recovery/backup drill.
