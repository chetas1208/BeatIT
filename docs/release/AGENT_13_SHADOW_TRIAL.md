# M10.5 Agent 13 — Shadow Trial E2E Verification

## Scope

Verified the real paired Shadow Trial API path using an isolated, temporary
file-backed SQLite database:

```text
POST /api/v1/twin/ensemble
  -> seeded EnsembleResponse persisted in SQLite
POST /api/v1/shadow-trials
  -> same-sample paired Shadow Trial persisted in SQLite
GET /api/v1/shadow-trials/{trial_id}
GET /api/v1/shadow-trials/{trial_id}/effects
GET /api/v1/shadow-trials/{trial_id}/pairs/{sample_id}
```

The trial used a four-sample seeded synthetic ensemble and a bounded
`afterload_index` scenario changing the value from `1.0` to `1.2`.

## Isolation and method

- No production files, fixtures, databases, or Python sources were modified.
- The API's ensemble and Shadow Trial stores were redirected in-process to the
  same SQLite file under `TemporaryDirectory`.
- The API was exercised through `fastapi.testclient.TestClient`; the verifier
  called the HTTP routes rather than invoking `run_shadow_trial` directly.
- Both stores were replaced with newly opened store instances before retrieval
  to exercise the persisted read path after a restart-style store reopen.
- The temporary directory and database were removed automatically after the
  run.

## Executed verification

The one-shot verifier was run from the repository root with a temporary
SQLite target. It asserted:

1. The real ensemble creation route returns HTTP 200.
2. The real Shadow Trial creation route returns HTTP 200 and a complete trial.
3. Every pair preserves identity: `baseline_twin_id == sample_id`, while the
   scenario twin ID is distinct.
4. All four pairs are valid and expose finite metric deltas with matching
   delta units.
5. Effect distributions contain one delta per valid pair and descriptive mean
   and median values.
6. Trial, effect, and individual-pair retrieval routes return the persisted
   response after reopening both SQLite stores.
7. A scenario value outside the bounded parameter range is rejected with HTTP
   422 and retains the canonical safety disclaimer.
8. Repeating the identical Shadow Trial POST twice returns response-equivalent
   JSON and does not create a different trial identity.

## Results

| Check | Result |
| --- | --- |
| Storage | PASS — temporary file-backed SQLite |
| Ensemble creation | PASS — HTTP 200 |
| Shadow Trial creation | PASS — HTTP 200 |
| Trial ID | `shadow-trial-3be30b4b4597` |
| Requested / valid / invalid pairs | `4 / 4 / 0` |
| Same-sample identity | PASS |
| Effect distributions | PASS — non-empty deltas and summaries |
| Trial retrieval after store reopen | PASS — HTTP 200; response equal |
| Effects retrieval | PASS — HTTP 200; distributions equal |
| Pair retrieval | PASS — HTTP 200; selected pair equal |
| Invalid scenario | PASS — HTTP 422 |
| Repeated-create idempotence | PASS — JSON responses equal |
| Canonical safety disclaimer | PASS |

The invalid request used the same baseline ensemble with `afterload_index =
2.5` and `delta = 1.5`; the API returned a bounded-scenario validation error.
The successful trial retained the canonical educational simulation disclaimer
on creation and all read projections.

## Disposition

**PASS for the isolated local Shadow Trial API contract.** Real pair creation,
identity preservation, effect calculation, persisted retrieval, invalid-input
handling, and deterministic idempotence were verified.

This evidence does not certify public deployment, authentication,
multi-tenant isolation, PostgreSQL/Valkey providers, backup/restore,
reverse-proxy behavior, concurrent writers, browser rendering, or suitability
for clinical data or treatment decisions.
