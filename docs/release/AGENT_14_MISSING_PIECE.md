# M10.5 Agent 14 — Missing Piece API E2E Verification

## Scope

Verified the real Missing Piece API path with a temporary, file-backed SQLite
store and all optional intelligence providers disabled:

```text
POST /api/v1/twin/ensemble
  -> deterministic M5.5 ensemble creation and persistence
POST /api/v1/missing-piece
  -> finite-difference sensitivity
  -> uncertainty-impact heuristic
  -> versioned evidence ranking
  -> Missing Piece persistence
GET /api/v1/twin/ensemble/{ensemble_id}
GET /api/v1/missing-piece/{analysis_id}
```

The verifier used the non-PHI
`fixtures/golden/probabilistic/mixed-distributions.json` fixture, seed `303`,
and five requested samples. It exercised the API through FastAPI
`TestClient`; it did not call the Missing Piece engine as a substitute for the
HTTP contract.

## Isolation and method

- No production files, fixtures, or Python sources were modified.
- Both API stores were redirected to SQLite files inside a temporary directory:
  `ensembles.sqlite3` and `missing-piece.sqlite3`.
- The temporary directory was removed automatically after the run.
- The verifier ran with `MODEL_ENABLED=false`,
  `INTELLIGENCE_PROVIDER=disabled`, and `OPENAI_ENABLED=false`.
- The module-level stores were replaced with newly opened SQLite store objects
  before retrieval, simulating a process restart without touching production
  data.
- SQLite files were checked for mode `0600`.

## Executed verification

The following one-shot verifier was run from the repository root:

```text
MODEL_ENABLED=false INTELLIGENCE_PROVIDER=disabled OPENAI_ENABLED=false \
PYTHONPATH=. python - <<'PY' ... TestClient ... POST /api/v1/twin/ensemble ... \
POST /api/v1/missing-piece ... GET ... PY
```

The verifier asserted:

1. `/api/v1/intelligence/status` reports provider `disabled`, with
   `enabled=false` and `model_configured=false`.
2. `/api/v1/config` reports the same disabled-provider contract without
   requiring a model or network access.
3. The real ensemble API creates five accepted samples with no rejected
   samples and preserves the safety disclaimer.
4. Missing Piece sensitivity returns one finite-difference record for each of
   the five deterministic parameters, each contributing all five accepted
   samples.
5. Uncertainty-impact records are present, use
   `uncertainty-impact-heuristic-v1`, are sorted by impact score, and their
   normalized impacts sum to `1.0`.
6. Evidence ranking returns all three reviewed evidence types, uses
   `evidence-priority-score-v1`, has positive scores, and is sorted descending
   by ranking score.
7. The no-evidence request reports `available_coverage_fraction=0.0` and
   `complete=false`.
8. A second target metric with all three reviewed evidence types reports
   `available_coverage_fraction=1.0` and `complete=true`.
9. Re-opened SQLite stores return byte-equivalent API JSON for both the
   ensemble and Missing Piece analysis.
10. Repeating the same Missing Piece request returns the identical persisted
    response, and both SQLite files have mode `0600`.

The full-evidence check intentionally uses a different target metric. The
analysis ID is deterministic for an ensemble plus target metric, and the
store is immutable; changing evidence inputs under the same analysis ID must
not overwrite the original analysis.

## Results

| Check | Result |
|---|---|
| Model-disabled status | PASS — provider `disabled`; enabled/model configured both false |
| Config endpoint | PASS — disabled intelligence metadata, no credentials |
| Ensemble creation | PASS — HTTP 200; `ensemble-e8111bd03ea4`; 5 accepted / 0 rejected |
| Sensitivity | PASS — 5 finite-difference records over 5 accepted samples |
| Uncertainty impact | PASS — 5 drivers; normalized impact total `1.000000000000` |
| Evidence ranking | PASS — 3 items; top item `echocardiographic_measurement` |
| Empty evidence coverage | PASS — fraction `0.0`; complete `false` |
| Full evidence coverage | PASS — fraction `1.0`; complete `true` |
| Persisted ensemble retrieval | PASS — response equal after store re-open |
| Persisted Missing Piece retrieval | PASS — response equal after store re-open |
| Repeated request | PASS — response equal; immutable record preserved |
| SQLite permissions | PASS — ensemble and Missing Piece databases `0600` |
| Canonical Missing Piece SHA-256 | `8cd2db85c50855e1b3e3f158871511b5e29a47ccbf925609d12a364e6367ea17` |

## Disposition

**PASS for the isolated local Missing Piece API E2E contract.** Real API
sensitivity, uncertainty impact, evidence ranking, model-disabled operation,
temporary SQLite persistence, re-open retrieval, and deterministic repeatability
all passed.

This does not certify public deployment, authentication, tenant isolation,
backup/restore, reverse-proxy behavior, browser rendering, live model
availability, or clinical validity. The Missing Piece sensitivity and evidence
scores remain explicitly deterministic educational heuristics; they are not
causal estimates, medical recommendations, confidence intervals, or
information gain.
