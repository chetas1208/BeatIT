# M10.5 Agent 23 — Deployment Lifecycle Verification

**Date:** 2026-09-26
**Scope:** alternate-port launcher lifecycle, health/readiness, frontend HTTP, preflight, process ownership, and clean shutdown
**Disposition:** PASS for the isolated local lifecycle path; public deployment remains unverified

## Method

The existing launcher was exercised without using the normal development ports:

```text
BEATIT_API_PORT=18000
BEATIT_WEB_PORT=13001
./deploy/beatit up
```

The ports were confirmed free before startup. Existing recorded launcher state was
`backend STOPPED` and `frontend STOPPED`. No existing service was stopped.

## Verification results

### Startup and process ownership

Startup returned:

```text
BEATIT READY frontend=http://127.0.0.1:13001 backend=http://127.0.0.1:18000
```

The launcher recorded and reported these processes:

```text
1171724  python -m uvicorn api.index:app --host 127.0.0.1 --port 18000
1171728  next-server (v16.2.7)
```

Both processes ran as the workspace user and were the only processes targeted by
`./deploy/beatit down`. The launcher status reported both services as `RUNNING`.

### Health and readiness

Both endpoints returned HTTP `200` and included the required safety disclaimer:

| Endpoint | Result |
| --- | --- |
| `GET /api/health/live` | `200`, `status: live`, `service: hearttwin-api` |
| `GET /api/health/ready` | `200`, `status: ready`, deterministic twin and storage ready |

Readiness correctly reported optional integrations as degraded or optional in the
local environment: language, Weave, and Redis were degraded; VISTA3D was optional.
The response identified deterministic/local fallbacks and did not expose secrets.

### Frontend HTTP

```text
GET http://127.0.0.1:13001/
HTTP 200
response body: 46,186 bytes
```

### Deployment preflight

```text
BEATIT_API_PORT=18000 BEATIT_WEB_PORT=13001 ./deploy/beatit preflight
```

All checks passed:

```text
READY    python
READY    node
READY    curl
READY    demo fixture
READY    ensemble golden
READY    Shadow Trial golden
READY    model manifest
200    /api/health/live
200    /api/health/ready
200    /api/v1/system-check
200    /api/v1/models/status
DEMO READY
```

### Clean shutdown

```text
BEATIT_API_PORT=18000 BEATIT_WEB_PORT=13001 ./deploy/beatit down
```

Observed after shutdown:

```text
backend STOPPED
frontend STOPPED
no alternate-port listeners remain
API connection refused as expected
```

The shutdown path removed only the launcher-recorded PID targets. No unrelated
listener remained on ports `18000` or `13001`.

## Execution note

An initial detached probe confirmed startup and live responses, but the execution
harness reaped those detached children after its command session ended. This was
not counted as a deployment failure. The complete verification above kept the
launcher command attached through startup, all probes, and shutdown, and passed
without relying on an unrelated service.

## Boundaries and remaining risks

- This verifies the local launcher and loopback HTTP lifecycle only.
- Public reverse proxy, TLS, DNS, browser/WebGL behavior, and remote deployment
  were not tested.
- External PostgreSQL, Valkey/Redis, object storage, backup/restore, and deployed
  restart persistence were not tested.
- Optional provider/model availability remains represented by local fallback
  status, not a live external-provider claim.

## Final verdict

**PASS — isolated local deployment lifecycle verified.** This evidence closes the
Agent 23 lifecycle check but does not change the broader M10.5 release decision or
authorize public shipment.
