# M10.5 Agent 21 — Failure Injection Verification

**Scope:** exercise model-disabled, VISTA-disabled, offline/local, invalid
ensemble, invalid scenario, and backend-unavailable behavior through the real
FastAPI application and the VISTA adapter.

**Date:** 2026-09-26 UTC

**Disposition:** **PASS for the isolated local failure contracts; OPEN for
deployed-provider and public-host verification.**

## Isolation and safety boundary

- The probe ran in one disposable Python process using FastAPI `TestClient`.
- Ensemble, Missing Piece, and Shadow Trial database paths were temporary
  files under a temporary directory and were removed at process exit.
- `INTELLIGENCE_PROVIDER=disabled`, `MODEL_ENABLED=false`,
  `VISTA3D_ENABLED=false`, and `CAREGUARD_VISTA_ENABLED=false` were set for
  the probe.
- OpenAI, generic-model, Redis, Upstash, Weave, and VISTA endpoint variables
  were removed from the probe process; no network provider was called.
- The backend-unavailable case replaced only the in-process Shadow Trial store
  with a test double that raised `ShadowTrialStoreError`, then restored the
  original store before the probe exited.
- No repository fixtures, databases, services, credentials, or production
  code were modified.
- All inputs were synthetic and educational; no clinical conclusion was
  inferred.

## Executed verification

The probe exercised these actual surfaces:

```text
GET  /api/v1/intelligence/status
GET  /api/v1/system-check
VISTA adapter segment() with CAREGUARD_VISTA_ENABLED=false
GET  /api/v1/twin/ensemble/ensemble-does-not-exist
POST /api/v1/twin/ensemble
POST /api/v1/shadow-trials with an out-of-bounds scenario
GET  /api/v1/shadow-trials/trial-backend-unavailable
```

The ensemble creation used the checked-in synthetic replay fixture. The
invalid scenario used `afterload_index=2.5`, outside the deterministic
scenario bounds. The final request used a temporary failing persistence store;
it did not stop or alter the host PostgreSQL, Valkey, or any other service.

## Results

| Failure condition | Result | Evidence |
| --- | --- | --- |
| Model disabled | PASS | `/api/v1/intelligence/status` returned HTTP 200, `provider=disabled`, `enabled=false`, and the canonical safety disclaimer. |
| Offline/local mode | PASS | `/api/v1/system-check` returned HTTP 200 and `status=ok`; the deterministic checks completed with `openai=fallback` and an explicit deterministic-fallback warning. |
| VISTA disabled | PASS | `vista_adapter.segment()` returned `status=disabled` without a network call and retained the clinician-review label. |
| Invalid ensemble | PASS | Missing ensemble retrieval returned HTTP 404 with the generic detail `Ensemble not found`. |
| Invalid scenario | PASS | Shadow Trial creation returned HTTP 422, reported the bounds failure, and retained the canonical safety disclaimer. |
| Backend unavailable | PASS | A Shadow Trial store failure returned HTTP 503 with `Shadow Trial persistence is unavailable`, preserved the disclaimer, and did not expose the injected internal exception text. |

## Observed probe output

```text
AGENT_21_FAILURE_PROBE PASS
MODEL_DISABLED status=200 provider=disabled enabled=false
OFFLINE_LOCAL_SYSTEM_CHECK status=200 overall=ok openai=fallback checks=10 warnings=3
VISTA_DISABLED status=disabled clinician_review_label=true
INVALID_ENSEMBLE status=404 detail=Ensemble not found
INVALID_SCENARIO status=422 detail_contains_bounds=true
BACKEND_UNAVAILABLE status=503 generic_detail=Shadow Trial persistence is unavailable internal_error_hidden=true
```

The full safety-disclaimer text was present in the model, invalid-scenario,
and backend-unavailable responses. The probe did not print inherited
environment values or any credential-shaped value.

## Verification command

The evidence came from an inline Python probe run from the repository root. It
loaded `fixtures/golden/probabilistic/synthetic-replay.json`, configured the
temporary database paths before importing `python.hearttwin.api`, asserted the
response contracts above, and exited successfully with code 0.

## Release boundary and remaining risks

- This verifies local in-process degradation and route mapping only.
- It does not prove behavior behind a public reverse proxy, TLS endpoint,
  deployed restart, real Redis outage, real model timeout, or a live VISTA
  service outage.
- The generic ensemble 404 route uses the framework's ordinary error envelope;
  the Shadow Trial safety-aware error handler was the backend-unavailable path
  used for disclaimer verification.
- Model-disabled fallback is appropriate for the deterministic educational
  pipeline, but it is not evidence that any optional language or imaging model
  is available or clinically validated.
- These results do not support clinical, diagnostic, or treatment claims.

