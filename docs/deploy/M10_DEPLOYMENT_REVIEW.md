# M10 Deployment and Reverse-Proxy Review

**Review date:** 2026-09-26  
**Scope:** `deploy/beatit`, `deploy/nginx.conf.example`, deployment guidance,
trace SSE transport, proxy limits, websocket upgrade handling, and rollback.  
**Change boundary:** documentation only; no production or deployment files were
modified by this review.

## Decision

**PARTIAL — do not ship as a public deployment yet.**

The repository has a usable local launcher and a plausible nginx starting point.
FastAPI emits the required SSE response headers and nginx disables buffering for
`/api/`. The deployment gate remains open because the launcher is not
health-gated through readiness, failed starts are not cleaned up, the proxy
limits do not match the application upload limits, TLS/public-host testing has
not been performed, and backup/restore plus persistence restart are not proven.

## Evidence summary

| Area | Evidence | Result |
| --- | --- | --- |
| Launcher syntax | `bash -n deploy/beatit` passed | PASS |
| Process binding | Launcher starts FastAPI and Next.js on `127.0.0.1` (`deploy/beatit:46-49`) | PASS |
| Startup check | `up` checks liveness and frontend root only (`deploy/beatit:50-55`) | PARTIAL |
| Failed-start cleanup | Startup timeout reports logs/status but does not stop children or clear PID files (`deploy/beatit:57-59`) | OPEN |
| PID safety | `down` targets recorded PIDs only, but does not verify command identity before `kill` (`deploy/beatit:13`, `26-35`) | PARTIAL |
| SSE response | FastAPI sets `text/event-stream`, `no-cache`, keep-alive, and `X-Accel-Buffering: no` (`python/hearttwin/api.py:829-846`) | PASS |
| SSE proxying | nginx sends `/api/` through HTTP/1.1 with `proxy_buffering off` (`deploy/nginx.conf.example:18-25`) | PASS for configuration intent |
| SSE liveness | Stream emits a one-second comment ping and honors `Last-Event-ID` (`python/hearttwin/api.py:837`, `866-891`) | PASS in local unit coverage |
| Websocket upgrade | Upgrade headers are present only in the catch-all frontend location (`deploy/nginx.conf.example:27-35`); no websocket route was found in `python/`, `api/`, or `web/` | PARTIAL / not currently required |
| Request size | nginx allows 25 MiB, while case upload accepts 200 MiB and ECG accepts 50 MiB after full buffering (`deploy/nginx.conf.example:9`; `python/hearttwin/api.py:964-991`, `1089-1091`) | OPEN |
| Proxy timeout policy | `proxy_read_timeout 120s` is set; connect/send timeouts, rate limiting, and an explicit cache policy are absent (`deploy/nginx.conf.example:9-12`, `18-25`) | OPEN |
| Rollback | Manual rollback exists, but backup/restore and persistence restart are not exercised (`docs/release/ROLLBACK.md`; `docs/deploy/M10_BACKUP_ROLLBACK_REVIEW.md:8-16`) | OPEN |
| Public deployment | Example uses an invalid placeholder hostname and has no TLS configuration (`deploy/nginx.conf.example:6-9`) | NOT VERIFIED |

## Launcher review

### Verified strengths

- `deploy/beatit` derives the repository root from its own location and keeps
  PID/log state under `.run/beatit` (`deploy/beatit:4-11`).
- The local services bind to loopback, so the launcher does not directly expose
  FastAPI or Next.js to the network (`deploy/beatit:46-49`).
- `down` only targets the two explicitly recorded PID files and does not remove
  application data (`deploy/beatit:26-35`).
- `up` builds the production frontend before starting the services and waits for
  both a backend liveness response and a frontend response
  (`deploy/beatit:44-55`).
- Port overrides are explicit through `BEATIT_API_PORT` and
  `BEATIT_WEB_PORT`; the operator documentation exposes the same contract.

### Release blockers

1. The startup gate checks `/api/health/live`, not `/api/health/ready` or
   `/api/v1/system-check`. A process that is alive but has unusable storage or
   a broken deterministic path can therefore be reported as ready.
2. If the 30-second startup loop fails, the script leaves any started process
   and PID files for manual recovery. This can create a stale or partially
   running release.
3. `restart` is a stop-then-start operation, not an atomic replacement. A
   failed build or health check leaves the service unavailable.
4. PID reuse is not prevented: `down` checks only whether the recorded numeric
   PID exists, not whether it is still the expected BeatIT command.
5. The launcher does not pin or record a release revision, create a backup, or
   verify data integrity after restart. PostgreSQL and Valkey are outside its
   lifecycle and backup ownership.

## Reverse-proxy and SSE review

The nginx example correctly keeps the application processes on loopback and
routes `/api/` to FastAPI with HTTP/1.1 and buffering disabled. The application
also emits `Cache-Control: no-cache`, `Connection: keep-alive`, and
`X-Accel-Buffering: no`, while the stream sends a comment heartbeat every
second. These settings are appropriate for the current EventSource transport.

The following still require deployment evidence or configuration work:

- Run the proxy in front of a real local instance and verify that an
  `EventSource` receives setup, trace, heartbeat, disconnect, and resume events.
  The existing tests drive the async generator directly; they do not prove a
  real nginx/browser connection.
- Add and verify explicit `proxy_connect_timeout` and `proxy_send_timeout`
  values. Keep the read timeout longer than the expected heartbeat interval and
  validate behavior across a backend restart.
- Keep response buffering disabled specifically for the SSE path and confirm
  that compression or caching does not delay events. The current `/api/`
  location is broad and relies on the example's global settings.
- The example has no TLS, certificate, HSTS, host allow-list, or public DNS
  configuration. These are deployment responsibilities, not claims made by
  this repository.

## Websocket upgrade review

The catch-all `/` location forwards `Upgrade` and `Connection: upgrade`.
There is no websocket endpoint in the current application search surface, and
the documented live trace transport is SSE. Therefore websocket readiness is
not a current product gate, but the configuration is not a complete contract
for a future websocket endpoint under `/api/`: that location does not forward
the upgrade headers. If a future route requires websocket transport, add an
explicit scoped location and test handshake, idle timeout, reconnect, and
shutdown behavior before enabling it.

## Limits and failure behavior

The `client_max_body_size 25m` setting is smaller than both application upload
limits. It protects the proxy from larger requests but also means the
application's documented 50 MiB ECG and 200 MiB case-upload limits cannot be
reached through this example. This mismatch must be resolved deliberately:
either lower and document the application contract or raise the proxy limit
with a resource-budget and upload-abuse review.

The application reads upload bodies fully before checking their byte limit
(`python/hearttwin/api.py:990-997` and `1089-1093`). The proxy limit is therefore
an important memory-protection boundary, but it is not a substitute for
streaming or concurrency controls. The API reliability review also records the
absence of a global request deadline, rate limit, and concurrency budget.

## Rollback and persistence

`docs/release/ROLLBACK.md` gives a safe operator sequence and explicitly avoids
broad deletion. That is useful procedure, but it is not recovery evidence. The
backup/rollback review found no exercised database dump/restore, Valkey snapshot
policy, verified restore artifact, or post-restore integrity check. The
launcher also does not own PostgreSQL or Valkey lifecycle.

Before a public release, the deployment owner must demonstrate, on the target
deployment shape:

1. Source/release identity is recorded before startup.
2. SQLite, artifact, PostgreSQL, and Valkey ownership and backup destinations
   are explicit for the selected persistence mode.
3. A backup is restored into an isolated target and passes record/checksum and
   `/api/v1/system-check` validation.
4. A backend/frontend restart preserves the promised state and does not replay
   or corrupt trace state.
5. A failed startup is cleaned up and leaves the previous healthy release
   available, or the documented rollback command restores it within the agreed
   recovery target.

## Required closure checks

- [ ] Exercise nginx or the selected reverse proxy with a real browser
  EventSource, including `Last-Event-ID` reconnect.
- [ ] Decide and align proxy/application upload limits; test oversized and
  parallel uploads.
- [ ] Add deployment-level connect/send/read timeout evidence and a bounded
  failure response for backend stalls.
- [ ] Make launcher startup readiness-gated and verify failed-start cleanup.
- [ ] Verify stale-PID handling or replace PID-only process ownership with a
  supervisor contract.
- [ ] Exercise TLS, host routing, security headers, and public health checks on
  the actual deployment hostname.
- [ ] Complete backup/restore, restart-persistence, and rollback drills.
- [ ] Record the final result in `docs/release/RELEASE_CHECKLIST.md` and
  `docs/hackathon/M10_COMPLETION.md`.

## Final gate

**Deployment gate: OPEN / FAIL for final ship.** Local launcher and SSE
configuration are credible starting points, but they do not establish a
production-ready public deployment, safe rollback, or persistence durability.
