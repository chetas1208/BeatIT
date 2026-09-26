# M10.5 Agent 12 — Missing Piece E2E Verification

**Date:** 2026-09-26 UTC
**Disposition:** **PASS for isolated local API and file-backed persistence; OPEN
for deployed release gates.**

## Scope

Exercised the real FastAPI Missing Piece path with a synthetic, non-PII
ensemble:

```text
POST /api/v1/twin/ensemble
  -> seeded ensemble validation and persistence
POST /api/v1/missing-piece
  -> sensitivity, uncertainty impact, completeness, and evidence ranking
GET /api/v1/missing-piece/{analysis_id}
  -> persisted response retrieval and contract validation
GET /api/v1/intelligence/status
  -> disabled-model runtime state
```

The target metric was `stroke_volume_ml`. The request declared all three
versioned evidence types: `repeat_ecg`, `blood_pressure_series`, and
`echocardiographic_measurement`.

## Isolation and method

- `BEATIT_ENSEMBLE_DB_PATH` and `BEATIT_MISSING_PIECE_DB_PATH` pointed to a
  temporary SQLite database under `/tmp`.
- `INTELLIGENCE_PROVIDER=disabled`, `MODEL_ENABLED=false`, and
  `OPENAI_ENABLED=false` were set before importing the API.
- The application was exercised through `fastapi.testclient.TestClient`; the
  probe did not call the Missing Piece engine as a substitute for the API.
- The input was explicitly marked `origin_quality=synthetic` and contained no
  patient identifiers, credentials, or external-provider calls.
- A fresh `SQLiteMissingPieceStore` instance reopened the same temporary file
  after the API GET, confirming file-backed retrieval independently of the
  original store object.
- The repository's production database, fixtures, source files, and running
  services were not modified.

## Executed verification

The one-shot verifier asserted:

1. Disabled intelligence reports HTTP 200, provider `disabled`,
   `enabled=false`, and `reachable=false`.
2. The ensemble and Missing Piece API creates return HTTP 200.
3. Sensitivities are finite, target-specific, and use
   `finite_difference` records.
4. Uncertainty impacts are present, sorted descending by impact score, use
   `uncertainty-impact-heuristic-v1`, and normalize to 1.0.
5. Evidence ranking contains the three requested mapped evidence types, is
   sorted descending, and uses `evidence-priority-score-v1`.
6. The API GET returns the exact persisted POST response and retains the
   canonical safety disclaimer and limitations.
7. A newly opened file-backed store retrieves the same analysis, with the
   SQLite file mode set to `0600`.

## Results

| Check | Result |
|---|---|
| Disabled model status | PASS — HTTP 200; provider `disabled`; disabled and unreachable as expected |
| Ensemble creation | PASS — HTTP 200 |
| Missing Piece creation | PASS — HTTP 200 |
| Sensitivity records | PASS — 5 finite records; all target `stroke_volume_ml`; finite-difference method |
| Uncertainty-impact records | PASS — 5 records; descending order; normalized total `1.0` |
| Evidence ranking | PASS — 3 records; requested evidence types mapped; descending order |
| Ranking method | PASS — `evidence-priority-score-v1` |
| API persisted retrieval | PASS — HTTP 200; analysis ID and complete payload equal to POST response |
| Fresh-store retrieval | PASS — analysis present after reopening SQLite store |
| SQLite permissions | PASS — mode `0600` |
| Safety boundary | PASS — canonical disclaimer, limitations, and synthetic provenance retained |

The generated analysis identifier was `missing-piece-ca2dd18f371a` during this
run. The temporary database was `/tmp/beatit-mp-e2e.zv3Bbi/e2e.sqlite3`.

## Release boundary

This closes the local Missing Piece API contract for the requested synthetic
path. It does not prove authentication, tenant isolation, public deployment,
reverse-proxy behavior, PostgreSQL or Valkey persistence, backup/restore,
concurrent writers, browser rendering, or patient-data suitability. The
Missing Piece surface remains educational and deterministic; its sensitivity,
uncertainty impact, and Evidence Priority Score must not be presented as
causal, diagnostic, treatment, clinical, or medical recommendations.
