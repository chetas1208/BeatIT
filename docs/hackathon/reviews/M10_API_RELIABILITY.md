# M10 API Reliability and Resource-Protection Review

**Contribution:** A03<br>
**Scope:** backend route validation, timeouts, expensive work, resource bounds, and error handling<br>
**Review date:** 2026-09-26<br>
**Production-code changes:** none<br>
**Disposition:** **OPEN** — focused functional checks pass, but release hardening is incomplete.

## Evidence and commands

All commands were run from `/home/923873155/BeatIT` against the current worktree. No secrets were printed.

| Command | Evidence | Result |
|---|---|---|
| `python - <<'PY' ... from python.hearttwin.api import app ... PY` | Enumerated the mounted FastAPI routes, including health, system-check, case pipeline, uploads, ensemble, Missing Piece, Shadow Trial, CopilotKit, and SSE routes. | PASS: route surface is discoverable. |
| Focused `TestClient` probe of `/api/health/live`, `/api/health/ready`, `/api/v1/system-status`, invalid create/ensemble/Shadow Trial requests, and an unknown case | Health/status returned `200`; malformed bodies returned `422`; missing case returned `404`. | PASS for status mapping and basic validation. |
| Three sequential `TestClient` calls to `/api/v1/system-check` | `200`, `ok`; elapsed times `55.9 ms`, `59.7 ms`, and `37.7 ms` in this local process. | PASS for local deterministic behavior; not a load or deadline proof. |
| `python -m pytest -q python/hearttwin/tests/test_api_routes.py python/hearttwin/tests/test_ensemble_api.py python/hearttwin/tests/test_trace_stream_sse.py` | `25 passed, 31 warnings in 3.75s`. | PASS for the focused regression set. |
| Schema and guard scan script | `EnsembleRequest.sample_count` is bounded to `1..1000`; Missing Piece identifiers/evidence are bounded; no API middleware, semaphore, rate-limit, `asyncio.wait_for`, request-body limit, or request-concurrency setting was found. | PASS for identified model bounds; OPEN for global protection. |

## PASS findings

### P-A03-1 — Basic route validation and state prerequisites

Pydantic validation rejects malformed required payloads with `422`. The case flow explicitly rejects unknown case IDs with `404`, `operate` before extraction with `422`, and recovery before operation with `422` (`python/hearttwin/api.py:1125-1127`, `1181-1191`, `1235-1245`). The focused tests cover these paths.

### P-A03-2 — Bounded high-cardinality scientific requests where contracts exist

The ensemble contract limits `sample_count` to 1000 (`python/hearttwin/ensemble.py:77-84`). Missing Piece uses strict models, maximum identifier length 128, and at most 32 evidence types (`python/hearttwin/missing_piece/api_models.py:20-76`). Shadow Trial rejects empty or duplicate metrics and duplicate scenario parameters (`python/hearttwin/shadow_trial_contracts.py:72-109`, `174-189`).

### P-A03-3 — Several CPU/SQLite-heavy M5–M8 operations are moved off the event loop

Ensemble creation/retrieval, Missing Piece work, and Shadow Trial work use `asyncio.to_thread` around synchronous engines and SQLite stores (`python/hearttwin/api.py:237-241`, `318-328`, `369-379`). The SQLite stores use file-backed databases and a five-second busy timeout (`python/hearttwin/storage/ensemble_store.py:78-80`; equivalent settings exist in the Missing Piece and Shadow Trial stores).

### P-A03-4 — External model and upload-provider calls have client-level timeout values

The intelligence provider reads a 45-second model timeout and bounded retry setting (`python/hearttwin/intelligence/factory.py:59-67`), and the legacy blob upload path specifies a 30-second HTTP timeout (`python/hearttwin/tools/storage.py:34-45`). These are useful lower-level protections, but they do not replace an API route deadline (see OPEN-A03-3).

### P-A03-5 — Liveness/readiness and safe degradation are exposed

The liveness endpoint avoids optional dependency checks, while readiness reports deterministic-core and optional-provider state (`python/hearttwin/api.py:153-185`). The system-status endpoint exposes model availability metadata without model credentials (`python/hearttwin/api.py:188-205`). The focused probe confirmed the expected shapes and no bearer/token-like test values in the response.

## OPEN findings

### OPEN-A03-1 — No API-wide concurrency, rate, or request-size guard (**P1 release blocker**)

`python/hearttwin/api.py:111-117` installs only `CORSMiddleware`. The guard scan found no request semaphore, rate limiter, `limit_concurrency`, `limit_max_requests`, request-body limit, or application deadline. The deployment command also contains no Uvicorn concurrency/request limit (`package.json:7-9`).

Consequences:

- `/api/v1/system-check` runs the complete extraction, operation, evaluation, and recovery path on every request (`python/hearttwin/api.py:590-597`, `625-670`), with no route budget.
- `/extract`, `/operate`, `/simulate-recovery`, and `/self-improve` await multi-stage work directly (`python/hearttwin/api.py:1118-1166`, `1174-1220`, `1228-1269`, `1272-1285`).
- The CopilotKit-mounted route is outside the explicit API guard surface (`python/hearttwin/api.py:133-140`).

**Required before RC:** enforce a deployment-appropriate request/concurrency budget (proxy and/or ASGI worker settings), add route-level deadlines for expensive work, and add rate/abuse protection for public deployment. Verify with concurrent and slow-client tests.

### OPEN-A03-2 — Uploads are fully buffered before limit enforcement (**P1 resource blocker**)

The case upload reads the entire multipart part into `file_bytes` and only then checks the 200 MiB limit (`python/hearttwin/api.py:968-997`). ECG upload does the same before its 50 MiB check (`python/hearttwin/api.py:1077-1095`). The artifact path then passes the same byte buffer to storage (`python/hearttwin/tools/storage.py:24-59`).

This bounds accepted payload size but does not bound peak memory or work for concurrent requests; it also relies on the upstream server/proxy to reject oversized request bodies early. The upload path accepts all `image/*` and `video/*` types (`python/hearttwin/api.py:978-987`), increasing the breadth of expensive payloads.

**Required before RC:** enforce `Content-Length`/multipart limits at the proxy and server, stream to bounded storage or a quota-controlled temporary file, cap concurrent uploads, and test parallel near-limit and over-limit requests. Also close the `httpx.AsyncClient` created at `python/hearttwin/tools/storage.py:37` rather than leaving its connection pool unmanaged.

### OPEN-A03-3 — Expensive routes have no end-to-end deadline (**P1 reliability blocker**)

Provider/client timeouts exist, but there is no timeout around the complete HTTP handler. A model timeout can be repeated by provider/key retry behavior, and deterministic pipeline, serialization, persistence, and external storage time are outside that client timeout. The focused local system-check timing is only a small-process observation and cannot establish a production upper bound.

**Required before RC:** define route budgets for system-check and each pipeline route; wrap cancellable work in an explicit deadline; return a stable `504`/safe fallback; and test provider timeout, SQLite lock, Redis stall, storage stall, and client disconnect behavior.

### OPEN-A03-4 — Redis case persistence has no application-configured socket deadline (**P1 deployment blocker when Redis is enabled**)

`redis.asyncio.from_url` is created without a socket/connect timeout (`python/hearttwin/tools/redis_client.py:35-56`). Case `get`/`set` operations await that client directly (`python/hearttwin/tools/storage.py:66-84`). A configured-but-unresponsive Redis service therefore has no explicit API-level upper bound; readiness only reports configuration and does not exercise the case-store path (`python/hearttwin/api.py:160-185`).

**Required before RC:** configure connect/read/socket timeouts, bound retries, and verify that Redis failure returns a bounded `503` or documented local fallback according to the persistence policy. Add a readiness probe that tests the actual required store, not only environment configuration.

### OPEN-A03-5 — Local trace/run retention is unbounded (**P1 long-lived-process memory risk**)

The local tracing fallback stores every case event in process-global lists and every run in a process-global dictionary (`python/hearttwin/tools/weave_trace.py:14-15`, `48-68`, `231-245`). There is no TTL, cap, eviction, or deletion path. `GET /trace` and the SSE stream read from that growing list (`python/hearttwin/api.py:793-807`, `829-891`).

**Required before RC:** add bounded retention/eviction and a maximum response/event window, or route local traces to a bounded persistent stream. Exercise a long-running multi-case soak and inspect RSS plus response size.

### OPEN-A03-6 — Several request models accept unbounded text, lists, and arbitrary mappings (**P1 input-hardening blocker**)

The core request models do not declare maximum lengths/items for `patient_notes`, `file_ids`, `user_vitals`, recovery `scenarios`, or `medication_effect_profile` (`python/hearttwin/schemas.py:180-224`, `372-388`). `ShadowTrialRequest` also has no maximum length for identifiers, descriptions, parameters, or metrics (`python/hearttwin/shadow_trial_contracts.py:92-109`, `174-189`). This is separate from the bounded `sample_count` and Missing Piece limits.

**Required before RC:** set explicit payload, text, list, mapping, and nested-depth limits for public routes, and reject oversized JSON before expensive model validation/serialization. Add adversarial oversized-body tests.

### OPEN-A03-7 — Normal error responses do not preserve the API safety envelope (**P1 contract blocker**)

The custom HTTP and validation handlers delegate all non-Shadow-Trial errors to Starlette defaults (`python/hearttwin/api.py:1309-1327`). The probe observed `{"detail": ...}` without `safety_disclaimer` for a normal missing-case `404` and invalid-create `422`; Shadow Trial errors did include the disclaimer because it takes the special branch. There is also no application-level generic `Exception` handler, so unexpected failures are not normalized by this module.

**Required before RC:** make all `/api` error paths return the stable error envelope and disclaimer, while avoiding internal exception/secret leakage; add tests for normal `404`, validation `422`, storage `503`, unexpected `500`, and client disconnects.

### OPEN-A03-8 — Wildcard credentialed CORS remains public deployment risk (**P1 security/reliability adjacency**)

The API allows every origin while enabling credentials and all methods/headers (`python/hearttwin/api.py:111-117`). This can expand the set of browser clients able to exercise expensive routes and is inconsistent with a constrained public deployment.

**Required before RC:** allowlist the deployed frontend and approved previews, decide explicitly whether credentials are required, and validate preflight behavior. This review records the issue but does not modify production code per task scope.

## Final gate decision

**API reliability gate: OPEN / FAIL for final ship.** The focused functional suite is green, and the deterministic local health path is responsive. The release cannot claim resource protection until the P1 items covering global limits/deadlines, upload buffering, Redis stalls, trace retention, input-size limits, and consistent error envelopes are either fixed and verified or explicitly covered by a trusted reverse proxy and deployment contract with evidence.
