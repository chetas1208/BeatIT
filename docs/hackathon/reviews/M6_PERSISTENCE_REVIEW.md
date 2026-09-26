# M6 Persistence, Restart, and Immutability Review

Date: 2026-09-26  
Scope: read-only review of `shadow_trial_store`, its focused tests, and the
Shadow Trial API persistence boundary. No implementation or test files were
changed by this review. M7 Split Heart and M8 Missing Piece are out of scope.

## Verdict

**PASS with bounded limitations.** The M6 trial store provides durable,
file-backed SQLite persistence; a new store instance can retrieve records after
the original store instance is gone. Replaying the same canonical JSON payload
under an existing trial ID is idempotent, while a different payload is rejected
and the original record remains unchanged.

The persistence result is strong enough for the current local M6 contract. It
should not yet be described as a complete database-level Shadow Trial schema
guard or as an API-level conflict protocol; those limitations are recorded
below.

## Implementation evidence

`python/hearttwin/storage/shadow_trial_store.py`:

- The `shadow_trials` table uses `trial_id` as its primary key and stores the
  payload as canonical JSON (`:80-92`).
- Each operation opens a fresh SQLite connection and uses a five-second busy
  timeout (`:75-78`), so retrieval is not tied to an in-memory store or a
  process-local connection.
- `save()` performs `INSERT ... ON CONFLICT (trial_id) DO NOTHING`, then reads
  the stored JSON in the same transaction and compares it with the canonical
  incoming JSON (`:94-118`). This is the create-once/immutable behavior:
  identical content is accepted; different content raises
  `ShadowTrialStoreError("shadow trial IDs are immutable")`.
- JSON encoding sorts object keys, rejects non-finite numbers, and rejects
  non-mapping payloads (`:37-48`).
- The store rejects `:memory:` and creates file-backed storage only (`:59-73`).
  Parent directories are attempted at mode `0700` and the database file at
  mode `0600`.

## Test evidence

Focused command:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  pytest -q \
  python/hearttwin/tests/test_shadow_trial_store.py \
  python/hearttwin/tests/test_shadow_trial_api.py

13 passed in 1.30s
```

The store tests at
`python/hearttwin/tests/test_shadow_trial_store.py` cover:

| Behavior | Evidence | Result |
| --- | --- | --- |
| Fresh-store round trip | `test_shadow_trial_round_trip_survives_new_store` | PASS |
| Same-ID replay | `test_same_payload_replay_is_idempotent_and_order_independent` | PASS |
| Conflicting write | `test_different_payload_cannot_overwrite_existing_trial` | PASS |
| Invalid payload cannot replace existing data | `test_invalid_payload_cannot_replace_existing_trial` | PASS |
| NaN/non-finite rejection | `test_non_finite_payload_cannot_be_persisted` | PASS |
| Canonical JSON across a new store instance | `test_persisted_json_is_canonical_and_restart_safe` | PASS |
| Non-mapping rejection | `test_payload_must_be_a_mapping` | PASS |
| In-memory storage rejection | `test_shadow_trial_memory_storage_is_rejected` | PASS |

The API tests at `python/hearttwin/tests/test_shadow_trial_api.py` additionally
show that:

- A created trial can be retrieved through the trial, effects, and pair routes
  with the safety disclaimer preserved (`:50-79`).
- Repeating the same POST request returns byte-equivalent JSON at the API
  level (`:117-135`), exercising deterministic trial generation plus the
  idempotent store write.
- Missing baseline resources return `404`, and a simulated persistence failure
  returns `503` (`:82-115`, `:137-162`).

## Cross-process restart probe

In addition to pytest, three separate Python processes were run against one
temporary file-backed SQLite database:

```text
first process:
{"fingerprint": "restart-proof", "metadata": {"a": 1, "b": 2}}
replay after restart:
{"fingerprint": "restart-proof", "metadata": {"a": 1, "b": 2}}
conflicting write after restart:
ShadowTrialStoreError:shadow trial IDs are immutable
{"fingerprint": "restart-proof", "metadata": {"a": 1, "b": 2}}
```

This verifies the important restart boundary directly rather than only by
constructing two store objects in one interpreter: the persisted record
survives process replacement, a semantically identical replay is accepted
despite object-key reordering, and a conflicting write cannot replace it.

## Bounded limitations

1. **Payload shape is not validated by the store.** `save()` validates that the
   value is a finite JSON-serializable mapping, and `get()` validates that the
   decoded value is an object (`:120-138`), but the store does not validate the
   complete `ShadowTrialResult` schema. The API create path serializes a typed
   result, so this is primarily a direct-store/corruption boundary. A future
   hardening pass should validate persisted payloads before returning them from
   generic retrieval paths.

2. **The API does not expose a distinct conflict status.** The create route
   saves the generated result at `python/hearttwin/api.py:207-210`, and catches
   every `ShadowTrialStoreError` as HTTP `503` at `:223-228`. Therefore, if a
   same-ID request ever generates different content, the store correctly
   protects the original record, but the caller receives the generic
   “persistence unavailable” response rather than an explicit immutable-write
   conflict. This does not weaken stored-data immutability, but it limits
   diagnosability and protocol precision.

3. **No concurrent-writer stress test is present in this review.** SQLite
   transactions, a primary-key constraint, and the configured busy timeout
   provide the intended protection for ordinary concurrent access, but the
   current evidence is sequential tests plus separate-process restart checks.
   A future gate should exercise concurrent same-ID identical and conflicting
   writes if the deployment will accept parallel trial creation.

4. **Trial persistence does not itself freeze the referenced baseline.** The
   store makes the trial payload immutable, but this review does not establish
   content-addressed or immutable persistence for the referenced baseline
   ensemble. Baseline lineage and replacement protection remain an upstream
   M6 integration concern.

## Files changed

Only this review document was added. No implementation or test files were
edited.
