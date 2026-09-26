# M10 Security, Secret, Privacy, and Logging Review

Reviewed: 2026-09-26 UTC
Method: read-only source/configuration audit. No production code was changed.
Scope: current checkout, including the M10 readiness additions and existing
optional CareGuard/provider integrations. External deployment configuration,
reverse-proxy logs, hosted Weave/Redis data, and live credentials were not
inspected.

## Verdict

**CONDITIONAL / SYNTHETIC-DEMO-ONLY. DO NOT ACCEPT REAL PATIENT DATA.**

The repository has good secret-handling intent: provider credentials are read
from environment variables, public config/status routes mostly expose booleans
and labels, trace sanitization removes several obvious identifiers, and no live
credential-shaped literal was found in non-test source. The deployed API is
still unauthenticated and exposes patient-bearing case records by identifier;
the CORS policy is wildcard plus credentials; and several trace/error/provider
paths can carry filenames, response text, or exception text. These are release
blockers for any public or patient-data deployment.

## Findings

### S-01 — P0 OPEN: Case, trace, upload, and derived-artifact access has no authorization

- `python/hearttwin/api.py:762-811,912-1015` serves case records, traces,
  harness data, and uploaded-file metadata using only a caller-supplied case ID.
- `python/hearttwin/api.py:229-425` similarly retrieves persisted ensemble,
  Missing Piece, and Shadow Trial artifacts by ID without authentication,
  ownership, or tenant checks.
- `python/hearttwin/tools/storage.py:75-97` stores complete case JSON in Redis
  or process memory; the record can contain notes, files, source metadata, and
  derived state.

Impact: anyone who obtains or guesses an identifier can read data; an
identifier is not an access control boundary. The application must remain
synthetic/demo-only until authentication, authorization, tenant isolation,
opaque references, and retention/deletion policy exist. Do not put patient data
behind the current deployment.

### S-02 — P1 OPEN: Wildcard credentialed CORS

`python/hearttwin/api.py:111-117` configures `allow_origins=["*"]`,
`allow_credentials=True`, and unrestricted methods and headers.

The current browser client does not add an application authorization header
(`web/lib/api.ts:109-127`), but this policy is unsafe if cookies, bearer auth,
or another ambient credential is added. Configure an explicit allow-list for
the deployed frontend and set `allow_credentials` only when the chosen auth
design requires it.

### S-03 — P1 OPEN: Trace sanitization preserves filenames and raw warning text

- `python/hearttwin/tools/weave_trace.py:291-335` special-cases `files` but
  copies each `filename` directly into trace metadata. Filenames can contain
  names, dates, accession numbers, or other PHI.
- `python/hearttwin/tools/weave_trace.py:179-181` appends exception text to
  global warnings without applying the sanitizer. Those warnings are included
  in run/trace responses (`:120-140,267-268`).
- The general string redaction (`:318-323`) handles several patterns but does
  not cover formatted phone numbers or arbitrary credential formats, and the
  PII-key check is exact-key based rather than normalized for all naming styles.

Impact: local traces, SSE traces, or external Weave traces can retain metadata
or diagnostic text that should not leave the process. Replace filenames with a
safe basename/hash or opaque file ID, sanitize warnings before persistence and
response, and add secret/phone/camelCase-key coverage tests.

### S-04 — P1 OPEN: Upload size enforcement happens after the entire body is read

`python/hearttwin/api.py:968-997` calls `await file.read()` and checks the
200-MB limit only after allocating the complete upload. The ECG route does the
same for its 50-MB limit (`:1077-1095`). The general route also accepts every
`image/*` and `video/*` content type based on the client-provided MIME value.

Impact: unauthenticated callers can consume memory, storage, and downstream
processing capacity. Enforce request/body limits at the proxy and multipart
layer, stream to bounded storage, sniff/validate content, cap dimensions and
processing concurrency, and add rate/quota controls before public exposure.

### S-05 — P1 OPEN: Uploaded content can leave the deployment without a data policy

- `python/hearttwin/tools/image_extract.py:81-103` base64-encodes the complete
  image and sends it to the configured model provider.
- `python/hearttwin/tools/vista3d_client.py:147-218` submits CT bytes to an
  external VISTA endpoint when enabled.
- `python/hearttwin/tools/storage.py:31-59` can send uploaded bytes to Vercel
  Blob or the optional S3 adapter.

These are legitimate integrations, but source review found no enforced consent,
de-identification gate, provider retention policy, or per-route audit decision
before transfer. Keep all demo inputs synthetic; for real data require an
explicit data-processing policy, de-identification/consent gate, approved
providers, encryption, retention controls, and audit evidence.

### S-06 — P1 OPEN: External response bodies and exception text can enter user-visible warnings

- `python/hearttwin/assistant/model_client.py:176-195` stores up to 500
  characters of a remote error/response body in `ModelAPIError` state.
- `python/hearttwin/tools/vista3d_client.py:138-144,210-219` includes exception
  text and up to 300 characters of the VISTA response in warnings.
- `python/hearttwin/tools/image_extract.py:136-145` includes the exception
  string in the extraction result warning.

Remote services can echo submitted text, internal URLs, request identifiers, or
other sensitive data. Return stable typed error codes to clients, keep detailed
diagnostics in a redacted server-only sink, and scrub URLs, authorization
values, response bodies, and provider payloads before any trace or API warning.

### S-07 — P1 OPEN: Model status exposes filesystem paths

`python/hearttwin/models/registry.py:63-83` builds a status object containing
the resolved checkpoint path, and `python/hearttwin/api.py:216-225` returns
`status.as_dict()` from the public `/api/v1/models/status` route. This can
disclose deployment directory layout and mounted model locations. The newer
`/api/v1/system-status` route intentionally omits the path (`api.py:188-204`),
which is the safer contract. Remove or redact `path` from the public legacy
route, or require operator authentication.

### S-08 — P1 OPEN: No application-level abuse controls are visible on expensive/public routes

The FastAPI setup (`python/hearttwin/api.py:103-117`) has no authentication,
rate limiting, request quota, or concurrency guard. Upload, ECG classification,
model-backed extraction, CopilotKit, ensemble, Shadow Trial, and recovery routes
can therefore be invoked repeatedly by an unauthenticated caller. This creates
cost, memory, CPU, external-provider, and storage abuse risk even with valid
synthetic inputs. Put rate limits and body/concurrency quotas at the edge and
backend, then authenticate non-demo routes.

### S-09 — P1 OPEN: Default validation errors may echo submitted input

For non-Shadow-Trial routes, `python/hearttwin/api.py:1320-1327` delegates
`RequestValidationError` to FastAPI's default handler. With the current Pydantic
stack, validation details can include the rejected `input` value. This must be
verified against the deployed dependency versions and treated as unsafe for
patient notes, tokens, or uploaded metadata until the handler is changed to
return field-safe error codes without request values.

### S-10 — P1 OPEN: Optional secret-in-path VISTA authentication is log-prone

`python/hearttwin/careguard/simulation/vista_adapter.py:30-43` can append an
endpoint secret to the URL path, while `:70-72` also places it in an auth
header. URL paths are commonly retained by proxy, access, tracing, and browser
diagnostic logs. Prefer header-only authentication or an explicitly redacted
transport path; never include the secret-bearing URL in user-visible status or
logs.

### S-11 — P1 OPEN: Raw-model logging is configurable and only warned about

`python/hearttwin/careguard/feature_flags.py:61-66` permits raw model input or
output logging when environment flags are enabled. `python/hearttwin/careguard/config.py:254-259`
adds a warning but does not fail closed. A shared/production deployment can
therefore be started in a PHI-capturing posture. Force these flags off outside
an explicitly isolated local test mode and fail readiness when they are true.

## Credential-shaped literal scan

The scan covered tracked environment templates and non-test `python/`, `api/`,
`web/`, `scripts/`, and `deploy/` source for API-key/token/password/bearer/private
key patterns and common provider prefixes.

- **No live credential-shaped literal found in non-test source.** `.env.example`
  and `web/.env.example` contain blank or `REPLACE_WITH_*` placeholders.
- Test files contain intentionally fake values used by secret-leakage tests;
  these are not runtime credentials and were not treated as production leaks.
- Providers correctly construct authorization headers from environment values
  (`python/hearttwin/intelligence/generic_openai.py:79-86`,
  `python/hearttwin/tools/vista3d_client.py:84-99`); headers are not returned by
  the reviewed public status/config routes.
- `.gitignore:16-38,65-89` excludes env files, credentials, uploads, data, and
  model weights. This is a repository safeguard, not a deployment secret store.

## Positive controls verified

- Public config and environment snapshots expose configuration booleans, model
  labels, and provider status rather than secret values
  (`python/hearttwin/api.py:433-479`, `python/hearttwin/tools/env_config.py:62-125`).
- Model adapters mask failures to type/status in their normal provider paths;
  the remaining response-body findings above are from legacy/optional error
  handling.
- Trace sanitization redacts exact keys for names, contact data, MRNs, notes,
  raw content, and bytes (`weave_trace.py:20-36,291-323`). It is useful
  defense-in-depth but is not sufficient for the open findings above.
- CareGuard audit persistence calls structured redaction before Redis/Postgres
  writes (`python/hearttwin/careguard/audit.py:23-51`), and its raw model
  logging defaults are intended to be off. The flags remain an open fail-closed
  issue (S-11).

## Required pre-release actions

1. Keep the product explicitly synthetic/demo-only and block patient data.
2. Add authentication, case ownership/tenant checks, artifact authorization,
   rate limits, quotas, and bounded upload processing.
3. Replace wildcard credentialed CORS with an explicit production allow-list.
4. Make traces, warnings, validation errors, provider errors, filenames, and
   URLs pass through a single redaction policy before persistence or response.
5. Remove filesystem paths from public model status and prohibit secret-bearing
   URLs.
6. Fail readiness for unsafe raw-model logging and add adversarial tests for
   credentials, phone numbers, filenames, validation echoes, provider errors,
   oversized uploads, and cross-case access.

## Final disposition

**M10 security gate: NOT PASSED.** Suitable for a controlled synthetic demo
with no real patient data and no assumption of privacy. Do not call the public
deployment HIPAA-ready, production-safe, or appropriate for identifiable data
until S-01 through S-11 are closed and verified in the deployed environment.
