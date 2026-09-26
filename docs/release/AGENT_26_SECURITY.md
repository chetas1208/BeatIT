# M10.5 Agent 26 — Security Adversary Review

## Scope

This is a bounded adversarial verification of the local FastAPI application. It
covers malformed JSON, invalid request values, upload and path handling, CORS
and response headers, public secret boundaries, and trace sanitization.

No production code, fixtures, databases, existing services, or credentials were
modified. All upload persistence probes used an in-process no-op seam or a
temporary directory. Fake sentinel values were used for secret checks and were
not printed.

## Method and evidence

Executed on 2026-09-26 from the repository root with FastAPI `TestClient` and
direct checks of the existing local artifact and trace boundaries.

Probe summary: **15 PASS, 10 FAIL, 25 total**. The trace check was then split
by field to avoid conflating protected content fields with generic secret-key
fields.

## Results

| Area | Result | Evidence |
|---|---|---|
| Malformed JSON on `/api/v1/cases` | PASS / OPEN | HTTP 422; no 5xx, but the response omitted `safety_disclaimer`. |
| Invalid ensemble shape | PASS / OPEN | HTTP 422; no 5xx, but the response omitted `safety_disclaimer`. |
| Invalid Missing Piece values | PASS | HTTP 422; no 5xx and the attacker-controlled marker was not echoed. |
| Invalid Shadow Trial shape | PASS | HTTP 422 with `safety_disclaimer`; no 5xx. |
| Local artifact traversal | PASS | `../escape`, nested traversal, and absolute-path probes were all rejected by `_safe_path`. |
| Local artifact key choice | PASS | Temporary artifact write used the generated opaque file ID, not the supplied filename. |
| Unsupported upload MIME type | PASS | HTTP 400; storage seam was not called. |
| Upload size limit | PASS / OPEN | With the configured limit temporarily reduced to 16 bytes, a 17-byte upload returned HTTP 400. The implementation reads the complete upload before checking size; the production cap is 200 MiB. |
| Path-like upload filename | FAIL | A filename containing traversal-like segments was accepted and reflected unchanged in the HTTP response. Local storage did not escape because it uses an opaque ID. |
| CORS origin policy | FAIL | An arbitrary `https://attacker.invalid` origin received a matching `access-control-allow-origin` together with `access-control-allow-credentials: true`. |
| CORS preflight | FAIL | The same arbitrary origin received a successful credentialed preflight for POST and authorization/content-type headers. |
| FastAPI security headers | FAIL | Direct API responses lacked `X-Content-Type-Options`, `Content-Security-Policy`, `X-Frame-Options`, and `Strict-Transport-Security`. Reverse-proxy headers were not tested. |
| Public config/model status secret boundary | PASS | Config, system status, readiness, model status, and intelligence status did not contain fake secret values. |
| Trace PII/raw-content sanitization | PASS | `raw_text`, `email`, `content`, and `bytes` markers were redacted. |
| Trace generic secret-key sanitization | FAIL | Values under `api_key`, `token`, and `secret` keys were present in the local trace payload. |

## Exact validation-envelope evidence

The current exception handlers apply the mandatory disclaimer to Shadow Trial
validation errors but delegate other `HTTPException` and
`RequestValidationError` cases to FastAPI's default handlers:

```text
cases_malformed     status=422 safety_disclaimer=False
ensemble_invalid    status=422 safety_disclaimer=False
missing_piece_invalid status=422 safety_disclaimer=False
shadow_invalid      status=422 safety_disclaimer=True
```

This is a consistency and safety-boundary failure, not a parser crash.

## Findings

### S1 — Credentialed wildcard CORS

**Severity: P0 for public deployment.** `CORSMiddleware` is configured with
`allow_origins=["*"]` and `allow_credentials=True`. The adversary probe
confirmed that an untrusted origin is reflected in credentialed CORS responses.
Restrict origins to an explicit deployment allowlist and verify both preview and
production domains before release.

### S2 — Generic secret fields leak into traces

**Severity: P0 if external tracing is enabled.** The sanitizer protects known PII
and raw-content keys but does not redact generic `api_key`, `token`, or `secret`
keys. A fake sentinel placed under each key remained in the trace payload.
Extend the sanitizer key set and add regression tests that inspect both local
fallback traces and external-trace payload construction.

### S3 — Safety disclaimer is absent from most validation errors

**Severity: P1.** Malformed JSON and invalid request bodies on non-Shadow-Trial
routes return normal FastAPI validation envelopes without the canonical
`safety_disclaimer`. Standardize the exception handlers for all public API
routes while preserving the existing status codes and non-secret error detail.

### S4 — Filename handling is not normalized at the API boundary

**Severity: P1 for any blob-backed or public deployment.** The upload route
accepts and reflects path-like filenames. The local artifact implementation
currently keys storage by a UUID, so the traversal probe did not escape the
temporary root. The separate blob-storage path constructs a URL using the raw
filename; filenames should be treated as display metadata only, normalized or
replaced for provider paths, and bounded in length.

### S5 — Upload limits are post-buffering

**Severity: P1 for untrusted uploads.** The route calls `await file.read()` and
only then checks the byte count. This enforces the final size rule but does not
protect memory or request handling from an oversized body. Enforce a bounded
stream/request body before buffering and align proxy, API, and ECG limits.

### S6 — Security headers are deployment-dependent and unverified

**Severity: P1 for public deployment.** The direct API has no baseline security
headers. The repository contains a reverse-proxy example, but no live proxy
verification was part of this probe. Configure and verify headers at the actual
public boundary, including TLS/HSTS where applicable.

## Secret-exposure boundary

The public metadata endpoints passed fake-secret non-disclosure checks. No real
secret values were printed or committed. This result does not certify logs,
reverse-proxy access logs, provider SDK exceptions, external Weave traces, or
container image layers; those remain separate release checks.

## Release disposition

**FAIL — do not ship publicly or with patient data.** The local traversal,
invalid-input, upload-type, and public-config checks provide useful protection,
but S1 and S2 are direct exposure risks. S3–S6 remain release-hardening gates.

## Reproduction commands

The probes were run as an in-process Python script using `TestClient`; they did
not require a running server. The focused source-level checks are:

```text
python -m pytest -q python/hearttwin/tests/test_api_routes.py
python -m pytest -q python/hearttwin/tests/test_weave_trace_fallback.py
```

These existing suites are supporting evidence only; they do not close the
adversarial findings above.

