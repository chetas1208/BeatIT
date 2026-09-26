# M6 Architecture Review

**Agent:** M6 agent #28  
**Date:** 2026-09-26  
**Scope:** API, persistence, contracts, paired-engine seams, and M6 architecture
documentation. Documentation-only review; no production code was changed. M7
Split Heart and M8 Missing Piece are out of scope.

## Verdict

**CONDITIONAL PASS — the M6 trial record boundary is durable and honest, but
baseline lineage is not yet immutable by ensemble ID alone.** The Shadow Trial
store is create-once, file-backed, and restart-safe. The API exposes a coherent
terminal request/retrieval sequence and does not advertise fake asynchronous
progress. Legacy M5.5 samples without the persisted projection base are
rejected instead of being silently re-evaluated from an unsafe state.

The remaining architecture blocker is upstream: `SQLiteEnsembleStore.save()`
still replaces an existing ensemble payload under the same ID, while an M6
trial persists the baseline ensemble ID but no verified baseline content digest.
Therefore, a later replacement can change the input referenced by a previously
created trial without changing the trial record. This is a lineage-integrity
gap, not a Shadow Trial row-overwrite bug.

## Reviewed seams

### 1. Shadow Trial persistence immutability — PASS

`SQLiteShadowTrialStore` uses a file-backed SQLite database and opens a fresh
connection for each operation. Its insert uses `ON CONFLICT (trial_id) DO
NOTHING`; after the insert, the stored canonical JSON is compared with the
requested payload. An exact replay is accepted, while a same-ID/different-
payload write raises `ShadowTrialStoreError` and cannot replace the original.

Evidence: `python/hearttwin/storage/shadow_trial_store.py:51-118` and
`python/hearttwin/tests/test_shadow_trial_store.py:8-66`.

The store rejects `:memory:` and creates the database directory with restrictive
permissions. JSON is serialized before the write transaction, and non-finite or
non-serializable payloads fail before an existing record can be replaced.

### 2. Restart behavior — PASS for trial records; conditional for inputs

The store retrieves records through a new connection, so a new store instance
pointing at the same SQLite path can read the original payload. The focused
tests cover JSON round-trip, canonical key ordering, and restart retrieval.

Evidence: `shadow_trial_store.py:54-69,120-138` and
`test_shadow_trial_store.py:8-66`.

This guarantee applies to the persisted Shadow Trial record. Replaying the
computation after restart is only lineage-safe while the referenced baseline
ensemble remains the same content. The baseline store currently documents and
implements replacement semantics, so the trial record should not be treated as
a complete immutable snapshot of its input.

### 3. API ordering and terminal semantics — PASS

The M6 routes are ordered with the more specific retrieval paths before the
generic `/{trial_id}` route:

1. `POST /api/v1/shadow-trials` loads the persisted baseline, then runs and
   persists one paired result.
2. `GET /api/v1/shadow-trials/{trial_id}/effects` returns stored distributions.
3. `GET /api/v1/shadow-trials/{trial_id}/pairs/{sample_id}` returns one stored
   pair.
4. `GET /api/v1/shadow-trials/{trial_id}` returns the complete stored result.

Evidence: `python/hearttwin/api.py:202-272`.

The POST handler offloads synchronous computation and SQLite I/O with
`asyncio.to_thread`, maps missing baselines to 404, invalid contracts to 422,
and persistence failures to 503. Repeated identical requests are accepted by
the immutable trial store as idempotent replays. The API response carries a
terminal `complete` or `failed` status rather than pretending to expose a live
job state.

One operational limitation remains explicit: the request is still synchronous
from the caller's perspective. `to_thread` protects the event loop but does
not provide cancellation, a job identifier, or progress events for a long
trial. This is appropriate for the current 50–1000-pair envelope only if the
performance gate continues to hold.

### 4. No fake progress — PASS

The architecture documentation correctly states that M6 is synchronous and
does not expose a fabricated progress bar or incomplete intermediate result.
The API returns only after the paired result has been computed and persisted;
retrieval endpoints read the immutable terminal payload. A zero-valid-pair run
is represented as `status="failed"` with retained invalid pairs and reasons,
not as a successful empty distribution.

Evidence: `docs/hackathon/M6_ARCHITECTURE.md:26-36`,
`python/hearttwin/shadow_trial_engine.py:222-290`, and
`python/hearttwin/tests/test_shadow_trial_api.py:32-80`.

### 5. Legacy baseline refusal — PASS

Scenario application requires every baseline sample to carry its persisted
`projection_base`. If that field is missing, the engine raises a clear error:
`baseline ensemble sample lacks the persisted projection base; regenerate the
M5.5 ensemble`. It does not reconstruct a base from an already projected
sample state and does not silently fall back to a second sampling path.

Evidence: `python/hearttwin/shadow_trial_engine.py:114-124` and
`python/hearttwin/ensemble.py:202,431`.

This is the correct fail-closed behavior for pre-projection or legacy ensemble
records. The API maps the resulting validation failure to HTTP 422, making the
repair action visible to the caller.

## Architecture finding requiring closure

### P0 — baseline ID is not a sufficient immutable input reference

The M6 trial ID is derived from the ensemble ID, scenario, metrics, and engine
versions. The trial store then freezes the generated result. However,
`SQLiteEnsembleStore` uses `ON CONFLICT (ensemble_id) DO UPDATE`, so the
ensemble payload under that ID can later be replaced. M6 does not persist or
verify a baseline payload/content digest before accepting the reference.

Consequences:

- A historical trial remains internally immutable, but its `baseline_ensemble_id`
  may resolve to a different baseline record later.
- A replay after replacement can produce different paired outputs under the
  same logical baseline ID.
- The stored result is not sufficient to prove the exact upstream input unless
  the complete baseline was retained separately or its digest was included and
  checked.

Recommended closure before an unconditional M6 readiness claim:

1. Make baseline ensemble IDs create-once, or add a content digest to the
   persisted ensemble and reject replacement under an existing ID.
2. Include the verified baseline content digest in trial identity and
   provenance.
3. Add a test that replaces a baseline under the same ID after trial creation
   and requires an immutable-input error or digest mismatch rather than silent
   replay.

This review does not change that behavior because the requested scope is
audit-only.

## Scope boundary

The reviewed architecture contains no M7 split-heart rendering, second heart,
or M8 missing-piece/sensitivity/information-gain workflow. Those remain future
milestones and are not required to close this seam audit.

## Validation

- Focused M6 contract, engine, API, identity, golden-fixture, and persistence
  tests were reviewed; the current focused evidence reported by the campaign is
  green.
- `git diff --check` passed after adding this document.
- No Python, TypeScript, API, storage, or frontend implementation files were
  modified.

