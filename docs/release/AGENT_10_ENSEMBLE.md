# M10.5 Agent 10 — Probabilistic Ensemble E2E Verification

## Scope

Verified the real probabilistic-ensemble API path without changing production
code or production data:

```text
POST /api/v1/twin/ensemble
  -> EnsembleRequest validation
  -> seeded run_ensemble projection
  -> EnsembleResponse validation
  -> temporary SQLite persistence
GET /api/v1/twin/ensemble/{id}
GET /api/v1/twin/ensemble/{id}/distributions
```

The verification used the existing
`fixtures/golden/probabilistic/mixed-distributions.json` fixture. It exercises
normal, uniform, lognormal, empirical, and fixed input distributions with a
fixed seed and five requested samples.

## Isolation and method

- No production files, fixtures, or Python sources were modified.
- The API module's ensemble store was redirected in-process to a
  `TemporaryDirectory` SQLite database.
- The same store was replaced with a newly opened `SQLiteEnsembleStore` using
  the same temporary path to simulate application restart and persistence
  re-open.
- The temporary directory and database were removed automatically after the
  run.
- The API was exercised through `fastapi.testclient.TestClient`, not by
  calling `run_ensemble` alone.

## Executed verification

The following one-shot verifier was run from the repository root:

```text
python - <<'PY' ... TestClient ... POST /api/v1/twin/ensemble ... GET ... PY
```

The verifier asserted:

1. Creation returns HTTP 200 and a validated ensemble response.
2. Retrieval returns HTTP 200 and exactly equals the creation response.
3. The distributions endpoint returns the persisted distributions and
   provenance for the same ensemble ID.
4. A newly opened store retrieves the same persisted response after the store
   object is replaced.
5. Repeating the identical seeded POST returns the identical response.
6. Every representative ID resolves to an accepted sample, and representative
   ejection fractions are ordered low ≤ median ≤ high.
7. The canonical safety disclaimer is present.

## Results

| Check | Result |
|---|---|
| Fixture | `fixtures/golden/probabilistic/mixed-distributions.json` |
| Create status | PASS — HTTP 200 |
| Ensemble ID | `ensemble-e8111bd03ea4` |
| Requested / accepted / rejected | `5 / 5 / 0` |
| Retrieval status | PASS — HTTP 200 |
| Distribution route | PASS — HTTP 200 |
| Re-opened-store retrieval | PASS — HTTP 200; response equal |
| Repeated seeded creation | PASS; response equal |
| Canonical response SHA-256 | `e033007019cdb8e3d3293f749fa1cfe14f70fae8d86b2c9af42344c722330c1b` |
| Safety disclaimer | PASS |

Representatives selected by the real engine:

| Label | Sample | Ejection fraction |
|---|---|---:|
| low | `ensemble-e8111bd03ea4-sample-1` | 57.633348331120615% |
| median | `ensemble-e8111bd03ea4-sample-4` | 59.3926211714914% |
| high | `ensemble-e8111bd03ea4-sample-2` | 60.59511933729404% |

The ordering assertion passed. The response also preserved the fixture's
provenance and version metadata through persistence and retrieval.

## Disposition

**PASS for the isolated local ensemble E2E contract.** Creation, deterministic
reproducibility, representative selection, API retrieval, distribution
projection, and file-backed re-open were all exercised successfully.

This result does not certify public deployment, authentication, multi-tenant
isolation, backup/restore, reverse-proxy behavior, or browser rendering. Those
remain separate M10.5 release gates.
