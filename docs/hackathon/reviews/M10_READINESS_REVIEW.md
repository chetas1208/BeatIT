# M10 Readiness Review — A25

Date: 2026-09-26 UTC  
Scope: liveness, readiness, system-status, and operator preflight semantics  
Method: source inspection plus FastAPI `TestClient` probes; no production files changed

## Decision

**PARTIAL — route contracts pass in-process, but the operator readiness gate is not
release-closed.** The application exposes distinct liveness and readiness routes,
returns the required educational safety disclaimer, and reports optional-provider
degradation without pretending those providers are required for the deterministic
demo. However, readiness is based on configuration rather than dependency
reachability, a degraded core returns HTTP 200, and the host-level preflight did
not reach this application on the configured local port.

## Verified route behavior

The following command was run from the repository root:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 \
  --project . --extra dev python <TestClient probe>
```

Observed results:

| Route | Status | Observed contract | Result |
|---|---:|---|---|
| `/api/health/live` | 200 | `status=live`, service name, disclaimer | PASS |
| `/api/v1/health/live` | 200 | Versioned alias with the same shape | PASS |
| `/api/health/ready` | 200 | Core and optional status maps, warnings, disclaimer | PASS in-process |
| `/api/v1/health/ready` | 200 | Versioned alias with the same shape | PASS in-process |
| `/api/v1/system-status` | 200 | Readiness projection plus safe model metadata and disclaimer | PASS in-process |
| `/api/v1/models/status` | 200 | Model metadata and deterministic-twin availability | PASS in-process |

The probe confirmed that readiness always reports the deterministic twin as
`ready`, includes `language`, `weave`, `redis`, and `vista3d` in `optional`, and
returns no tested `Bearer `, `LEAK-`, `OPENAI_API_KEY=`, or
`UPSTASH_REDIS_REST_TOKEN=` markers. A patched storage probe returned:

```json
{
  "status": "degraded",
  "core": {"deterministic_twin": "ready", "storage": "degraded"}
}
```

The route still returned HTTP 200 in that degraded-core case.

## Semantic findings

### A25-R1 — Readiness does not perform dependency health checks (P1, open)

`health_ready()` derives core readiness from `storage_status()["configured"]`
and derives optional status from environment/provider configuration
(`python/hearttwin/api.py:160-185`). `validate_environment()` treats a present
`REDIS_URL`, `WANDB_API_KEY`, model provider, or VISTA endpoint/key pair as
configured, but does not connect to the service or make a bounded health request
(`python/hearttwin/tools/env_config.py:62-129`). Local storage is considered
configured without a read/write probe (`python/hearttwin/storage/factory.py:25-32`).

Therefore `ready` means “configuration is present” for optional integrations,
not “the integration is reachable and usable.” The system-status model records
also describe registry/artifact state; they do not prove that a model loaded or
completed inference. This is acceptable for the deterministic synthetic fallback
only if deployment documentation explicitly labels it as configuration status.

Required closure: define which dependencies are required per deployment profile,
add bounded probes for those dependencies, and test configured-but-unreachable
Redis, model, Weave, VISTA, and storage cases without leaking endpoint details or
secrets.

### A25-R2 — Degraded readiness uses HTTP 200 (P1, open)

When core storage is unconfigured, the endpoint returns a JSON `status` of
`degraded` but still responds with HTTP 200. Generic reverse proxies, load
balancers, and orchestrators commonly use the HTTP status code—not an application
field—to decide whether to route traffic. A deployment could therefore be marked
healthy while the required persistence capability is unavailable.

Required closure: choose and document the deployment contract. For a hard core
dependency, return a suitable non-2xx readiness response (normally 503) while
retaining the structured body; for synthetic local fallback mode, explicitly
declare that storage is non-durable and use a separate profile rather than
silently treating it as production-ready.

### A25-R3 — System-status is useful but not a complete readiness authority (P1,
open)

`/api/v1/system-status` reuses the readiness body and adds `available`, `loaded`,
`required`, and `error` for registry entries (`python/hearttwin/api.py:188-205`).
This is a safe operator summary, but it can report an artifact as available while
it is unloaded, and it inherits the configuration-only readiness semantics. It
should not be presented as proof of live model inference, Redis durability, or
Weave trace delivery.

### A25-R4 — Preflight has a useful local mode but weak remote assertions (P2,
open)

`scripts/demo-preflight.sh` checks command and fixture presence, then—only when
`E2E_BASE_URL` is set—requires HTTP 2xx from `/api/health/live`,
`/api/health/ready`, `/api/v1/system-check`, and `/api/v1/models/status`
(`scripts/demo-preflight.sh:7-43`). It does not validate response JSON, safety
disclaimer presence, readiness state, model fields, response time, or that the
returned service is actually BeatIT. It also has no curl connect/overall timeout.

The no-URL run passed:

```text
READY python / node / curl
READY demo fixture / ensemble golden / Shadow Trial golden / model manifest
SKIP HTTP checks (set E2E_BASE_URL)
DEMO READY
```

The explicit local HTTP run did not pass:

```text
E2E_BASE_URL=http://127.0.0.1:8000 ./scripts/demo-preflight.sh
404 /api/health/live
404 /api/health/ready
404 /api/v1/system-check
404 /api/v1/models/status
DEMO NOT READY
```

The port was already occupied by a Uvicorn process, but its response did not
expose the BeatIT routes; no process was stopped or modified. This is evidence
that a successful static preflight does not establish that the intended service
is running on the operator's target port.

Required closure: run preflight against the actual launch command or deployed
URL, assert JSON service/status/disclaimer fields, set bounded curl timeouts, and
fail if the endpoint is reachable but is not the expected BeatIT API.

## Safety and information exposure

The audited routes include the existing educational, non-diagnostic disclaimer.
The system-status projection intentionally omits credentials and the focused
probe found no tested secret-shaped markers. The route still returns provider
error strings from model registry status and environment warnings; keep those
messages sanitized and avoid exposing URLs, filesystem paths, request content, or
provider response bodies as the status implementation evolves.

## Verification matrix

| Check | Evidence | Result |
|---|---|---|
| In-process route status and shape | FastAPI `TestClient` probe above | PASS |
| Liveness independent of optional integrations | Route implementation and no-provider baseline | PASS |
| Optional degradation visible | Baseline readiness: language/Redis/Weave degraded, VISTA optional | PASS |
| Core degraded branch | Patched `storage_status()` probe | PASS as JSON; HTTP semantics open |
| Non-secret system status | Marker assertions on response text | PASS for tested markers |
| Local static preflight | `./scripts/demo-preflight.sh` | PASS |
| Local HTTP preflight | `E2E_BASE_URL=http://127.0.0.1:8000 ...` | FAIL: expected routes returned 404 |
| Deployed/reverse-proxy readiness | No public deployment URL supplied | NOT RUN |
| Restart and dependency-loss probes | No service fault injection performed | NOT RUN |

## Release disposition

Do not close the M10 readiness gate yet. The deterministic in-process contract is
usable for a synthetic demo, but public release requires a verified target
process/deployment, explicit HTTP readiness semantics, bounded dependency probes,
and a preflight that validates response content rather than status codes alone.
