# M10.5 Agent 11 — Shadow Trial API E2E Verification

**Scope:** exercise the real FastAPI Shadow Trial creation and read routes over
temporary persistence, including same-sample pair identity, effect retrieval,
invalid scenario handling, and repeated-create idempotence.

**Audit date:** 2026-09-26 UTC

**Disposition:** **PASS for the isolated local API and SQLite path; OPEN for
browser, deployed-host, external-provider, and concurrent-request verification.**

## Safety boundary

The probe used Python's `TemporaryDirectory` for the ensemble and Shadow Trial
SQLite databases. It did not open, modify, delete, or restart the repository's
existing databases, Docker services, artifact roots, or application processes.
The temporary directory was removed automatically after the probe completed.

The baseline came from the checked-in
`fixtures/golden/probabilistic/synthetic-replay.json` fixture. The generated
scenario and all resulting records were synthetic educational data. No patient
data, credentials, or external services were used.

## API procedure

In a fresh Python process, the probe:

1. Configured `BEATIT_ENSEMBLE_DB_PATH` and
   `BEATIT_MISSING_PIECE_DB_PATH` to temporary SQLite files.
2. Imported the real `python.hearttwin.api:app` and opened a FastAPI
   `TestClient`.
3. Created a baseline ensemble through `POST /api/v1/twin/ensemble`.
4. Created a bounded afterload scenario through
   `POST /api/v1/shadow-trials`.
5. Retrieved the complete trial, its effect projection, and one individual
   pair through the corresponding GET routes.
6. Submitted an out-of-bounds `afterload_index` scenario and checked the
   validation response.
7. Repeated the original create request and required an exactly equal JSON
   response, then loaded the record through a newly constructed
   `SQLiteShadowTrialStore` against the same temporary file.

## Evidence

```text
AGENT 11 SHADOW TRIAL E2E PASS
temporary_db=shadow-e2e.sqlite3 db_exists=True mode=0o600
ensemble_id=ensemble-6f5f02cd6a84 trial_id=shadow-trial-1156ce70f37a pairs=3
pair_identity=PASS sample_ids_unique=3 effects=7
retrieval=PASS persisted_store_reload=PASS invalid_scenario_status=422 idempotent_replay=PASS
```

## Verified assertions

| Check | Result | Evidence |
| --- | --- | --- |
| Real API ensemble creation | PASS | `POST /api/v1/twin/ensemble` returned `200` and produced `ensemble-6f5f02cd6a84` |
| Real API Shadow Trial creation | PASS | `POST /api/v1/shadow-trials` returned `200` and produced `shadow-trial-1156ce70f37a` |
| Pair identity | PASS | 3 unique sample IDs; every `baseline_twin_id` equals its sample ID; every scenario twin is distinct and trial-namespaced |
| Effects projection | PASS | `GET /api/v1/shadow-trials/{trial_id}/effects` returned 7 non-empty effect distributions and reconciled valid-pair counts |
| Individual pair retrieval | PASS | `GET /api/v1/shadow-trials/{trial_id}/pairs/{sample_id}` returned the requested pair with matching trial and sample IDs |
| Complete trial retrieval | PASS | `GET /api/v1/shadow-trials/{trial_id}` returned JSON exactly equal to the creation response |
| Invalid scenario | PASS | `afterload_index=2.5` returned `422` with an explicit `[0.0, 2.0]` bounds message and the canonical safety disclaimer |
| Idempotent replay | PASS | Repeating the identical create request returned `200` and equal parsed JSON; no duplicate identity was created |
| Temporary persistence reload | PASS | A newly constructed `SQLiteShadowTrialStore` loaded the persisted trial equal to the API creation payload |
| Database permissions | PASS | Temporary SQLite file was created with mode `0600` |

The created trial had `requested_pairs=3`, `valid_pairs=3`, and
`invalid_pairs=0`. The API response retained the canonical educational safety
disclaimer on successful and invalid requests.

## Release boundary

This verifies the application routes and local file-backed persistence in an
isolated process. It does not prove browser-to-API wiring, a live reverse
proxy, a deployed restart, PostgreSQL or Valkey/Redis persistence, backup and
restore, authentication or tenant isolation, rate limiting, concurrent writes,
or behavior under a process crash. Those remain open M10.5 release checks.

**Final result: PASS for this Agent 11 scope; overall release certification is
not implied.**
