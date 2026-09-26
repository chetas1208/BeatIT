# M10 Observability Review

**Contribution:** A10 — observability, readiness, non-secret status, and trace/log exposure  
**Date:** 2026-09-26 UTC  
**Scope:** FastAPI health/status routes, local and Weave trace plumbing, SSE trace
delivery, sanitization, and operational exposure. Read-only review; no
production or test files were changed.

## Verdict

**OPEN — the local fallback and status contracts are testable, but observability
is not release-closed.** The repository has distinct liveness/readiness routes,
honest optional-provider labels, non-secret response tests, bounded string/PII
sanitization, and a reconnectable local SSE stream. However, readiness currently
means configuration/filesystem presence rather than dependency reachability,
the Weave path is only a best-effort `publish()` adapter with no source-level
proof of a nested operation tree or flush, and case trace/harness/status
surfaces are not visibly authenticated or retention-bounded. The review therefore
supports a local synthetic demo with explicit fallback labels, not a production
observability claim.

## Pass findings

### OBS-P1 — Liveness and readiness are distinct and retain the safety boundary

**PASS for the route contract.** `/api/health/live` and its versioned alias
return process liveness without checking optional dependencies
(`python/hearttwin/api.py:153-157`). `/api/health/ready` and
`/api/v1/health/ready` report the deterministic twin and local storage as core,
while language, Weave, Redis, and VISTA are reported separately as optional or
degraded (`python/hearttwin/api.py:160-185`). Both responses carry the canonical
`safety_disclaimer`. The route test verifies the distinction and the four
optional status keys (`python/hearttwin/tests/test_api_routes.py:37-48`).

### OBS-P2 — Operator status is intentionally narrower than secret configuration

**PASS, bounded.** `/api/v1/system-status` exposes core readiness and model
fields limited to `available`, `loaded`, `required`, and `error`
(`python/hearttwin/api.py:188-205`). `/api/v1/intelligence/status` documents
that it does not return keys or authorization data, while `/api/v1/models/status`
reports local model metadata without loading checkpoints
(`python/hearttwin/api.py:208-225`). The route tests assert that sentinel
`Bearer ` and `LEAK-` values are absent from system status and that intelligence
status does not expose `API_KEY` or `Authorization`
(`python/hearttwin/tests/test_api_routes.py:50-68`). The deterministic model
registry is lazy: status inspects configured paths and loaded state without
allocating model memory (`python/hearttwin/models/registry.py:1-5,63-84`).

### OBS-P3 — The local trace path is resilient and applies a privacy filter

**PASS for the tested local fallback.** `TraceSink` catches failures for run,
stage, tool, evaluation, and finish operations so tracing errors do not break
the application (`python/hearttwin/tools/weave_trace.py:39-43,48-73,75-137`).
Trace payloads pass through `_sanitize`, which redacts named PII/content keys,
file bytes, SSNs, long strings, long lists, and excessive nesting
(`python/hearttwin/tools/weave_trace.py:291-335`). The trace tests cover
never-throw behavior, local stage/evaluation persistence, raw report trimming,
and absence of a sentinel API key from stored traces
(`python/hearttwin/tests/test_weave_integration.py:54-65,67-80,105-125`).

This is a best-effort denylist and length filter, not a proof that arbitrary
future fields or third-party provider payloads are safe.

### OBS-P4 — The local SSE stream has explicit resume semantics and honest source labels

**PASS for the local transport contract.** The trace stream sends a setup event
with `source: local`, polls the same in-process trace source as the snapshot
route, emits stable local event IDs, and accepts either the query parameter or
`Last-Event-ID` for resumption (`python/hearttwin/api.py:793-845,849-909`).
The endpoint disables proxy buffering and sends keep-alive comments. Tests cover
unknown-case 404 behavior, setup/trace records, stable event naming, and resume
skipping of already-seen events (`python/hearttwin/tests/test_trace_stream_sse.py:86-120`).

The explicit `local` label is important: this stream must not be presented as a
Redis or hosted Weave stream when the local fallback is active.

### OBS-P5 — System check reports fallback states rather than silently promoting them

**PASS for the deterministic diagnostic contract.** `/api/v1/system-check`
executes a golden deterministic path, reports check status and warnings, and
adds explicit warnings when Weave, Redis, OpenAI, or VISTA are unavailable
(`python/hearttwin/api.py:590-597,705-715,736-753`). The environment helper
also names the fallback mode without returning credential values
(`python/hearttwin/tools/env_config.py:62-129`).

## Open findings

### OBS-O1 — Weave status does not prove real trace emission or nested call coverage

**Severity: P0 sponsor and release evidence gap.** Weave initialization is
attempted only when tracing is enabled and `WANDB_API_KEY` exists
(`python/hearttwin/tools/weave_trace.py:271-288`). After that, `_publish()` calls
`_WEAVE_CLIENT.publish(payload)` only if the client happens to expose that
method, and otherwise preserves local storage as the fallback
(`python/hearttwin/tools/weave_trace.py:168-177`). The reviewed trace module
contains no `@weave.op` decorators, operation wrappers, or flush before an API
response. `weave_info()` can therefore report `enabled`/`connected` based on
initialization while the source does not establish that the emitted events are
visible as a nested public Weave tree (`:142-156`).

Required closure: use the verified Weave operation API for the orchestrator and
agent stages, flush before returning the HTTP response, and capture a live
public run URL. The readiness/status contract must distinguish configured,
initialized, successfully emitted, and flushed states.

### OBS-O2 — Readiness checks configuration, not reachability or service health

**Severity: P1 operational false-ready risk.** Readiness marks Weave and Redis
as `ready` when their environment configuration exists, not after a network
probe (`python/hearttwin/api.py:169-183`). Local artifact storage is considered
configured whenever local storage is selected, without checking that the root
is writable (`python/hearttwin/storage/factory.py:25-33`). The model registry
checks path existence/config shape, not load or inference health
(`python/hearttwin/models/registry.py:63-84`), and VISTA status is derived from
configuration flags rather than a live endpoint check. Redis reachability is
only best-effort in the separate stats route, where failures become
`status="error"` and an exception type (`python/hearttwin/api.py:559-587`).

Required closure: keep liveness cheap, but make readiness explicitly report
`configured`, `reachable`, and `usable` for each dependency. Probe only bounded,
safe operations and define whether an optional dependency makes readiness
degraded or failed.

### OBS-O3 — Trace, harness, and status surfaces have no visible access-control or retention boundary

**Severity: P0 privacy/deployment risk if non-synthetic data reaches the service.**
The case trace and harness routes return retained trace payloads, stage results,
evaluation data, run identifiers, and Weave metadata
(`python/hearttwin/api.py:793-811,912-941`). The SSE route streams the same
trace data. No authentication or authorization middleware is present in the
reviewed API setup; CORS is wildcard with credentials enabled
(`python/hearttwin/api.py:111-117`). Local traces are process-global dictionaries
with no TTL, size cap, or tenant boundary (`python/hearttwin/tools/weave_trace.py:14-18,231-246`).

Required closure: enforce the deployment’s authentication/authorization policy,
restrict CORS origins, define synthetic-only versus protected-data mode, bound
trace retention and payload size, and verify that reconnects cannot cross case
or tenant boundaries. Until then, retain the documented nonclinical,
synthetic-demo limitation.

### OBS-O4 — The model status endpoint exposes filesystem paths and registry metadata

**Severity: P1 information-disclosure hardening item.** The compact
`system-status` projection omits paths, but `/api/v1/models/status` calls
`ModelStatus.as_dict()`, which includes `path`, runtime, metadata, and error
fields (`python/hearttwin/api.py:216-225`; `python/hearttwin/models/schemas.py:34-57`).
An absolute checkpoint path is operationally useful to a local operator but is
not required by an unauthenticated public status surface.

Required closure: expose a public-safe model summary without absolute paths or
free-form metadata, or protect the detailed endpoint as an operator-only route.
Add tests that assert paths, provider diagnostics, and arbitrary exception text
cannot escape the public status contract.

### OBS-O5 — Error observability is inconsistent and can include raw exception detail

**Severity: P1 log/response hygiene item.** Some integration failures reduce to
an exception type (`python/hearttwin/api.py:585-586`), but system-check failure
messages interpolate `str(exc)` into the public diagnostic response
(`python/hearttwin/api.py:692-703`), and generic validation/safety handlers also
return exception detail (`python/hearttwin/api.py:1293-1326`). A repository
search found no common structured application logger, request correlation ID,
latency metric, or resource metric for the main FastAPI path. This makes
incident correlation and redaction policy inconsistent across routes.

Required closure: define a structured event schema with request/run/case
correlation IDs, duration, outcome, and bounded safe error codes; keep raw
exception text in protected server logs only; and add response/log redaction
tests for provider, storage, upload, and validation failures.

### OBS-O6 — The intended Weave UI entry point is not mounted in the shell

**Severity: P1 demo observability gap.** `WeaveBadge` implements connected,
standby, and error states and a run/project deep link
(`web/components/eval/WeaveBadge.tsx:3-16,22-55,57-103`). The reviewed
`AppShell` renders the run status, trace, evaluation, and Redis rail but does
not import or render `WeaveBadge` (`web/components/layout/AppShell.tsx:188-241`).
The backend can therefore expose a trace URL without the promised visible
operator/judge entry point.

Required closure: mount the badge in the declared shell slot and verify
connected, no-run, error, and local-fallback states in a browser-capable
environment. Do not call the sponsor observability gate complete from static
component existence alone.

## Required verification before release

1. Run one deployed synthetic case with `GET /api/health/live`,
   `GET /api/health/ready`, `/api/v1/system-status`, model status, trace
   snapshot, and SSE reconnect evidence captured together.
2. Demonstrate a real nested Weave tree and public URL after the response has
   flushed; separately demonstrate the explicit local fallback with no key.
3. Exercise Redis, storage, language, and VISTA failures and verify status
   transitions, safe error codes, deterministic fallback, and no secret/raw
   payload exposure.
4. Run the trace redaction probe with synthetic PII in names, filenames,
   notes, evidence/provenance fields, and provider errors; inspect both API
   responses and server/third-party trace destinations.
5. Verify authentication, CORS, retention limits, case isolation, browser
   reconnect behavior, and operator-visible Weave/local source labels.

## Release disposition

**Observability gate: NOT READY for hosted/public or patient-data claims.**
Local synthetic fallback observability is usable and meaningfully tested. The
remaining gaps are implementation/verification blockers, not reasons to add
new product science: real Weave emission/flush proof, dependency-aware
readiness, access and retention controls, consistent safe error telemetry, and
browser/deployed evidence.
