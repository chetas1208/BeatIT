# M10 Proxy Configuration Review

**Contribution:** A16 — nginx SSE, limits, security headers, and loopback
upstreams  
**Review date:** 2026-09-26 UTC  
**Scope:** `deploy/nginx.conf.example` compared with the FastAPI SSE route,
health routes, upload limits, and self-host deployment guidance.  
**Change boundary:** Documentation only. No production or test files were
modified by this review.

## Verdict

**PARTIAL — suitable as a local reverse-proxy starting point, not release
evidence for a public deployment.** The example keeps both application
processes on loopback and has the essential nginx behavior for the current
EventSource transport: HTTP/1.1 upstream requests, buffering disabled for
`/api/`, and a read timeout longer than the backend's one-second heartbeat.
The example does not yet establish a public security or capacity contract.
Its 25 MiB body limit is smaller than the API's 50 MiB ECG and 200 MiB case
upload limits, TLS is absent, and connect/send timeout, cache, rate-limit, and
browser-through-proxy evidence are not present.

## Evidence matrix

| Area | Observed configuration or implementation | Result |
| --- | --- | --- |
| API upstream | `127.0.0.1:8000` (`deploy/nginx.conf.example:4`) | PASS for loopback intent |
| Frontend upstream | `127.0.0.1:3001` (`deploy/nginx.conf.example:3`) | PASS for loopback intent |
| SSE protocol | FastAPI returns `text/event-stream`, `no-cache`, keep-alive, and `X-Accel-Buffering: no` (`python/hearttwin/api.py:829-846`) | PASS at application layer |
| SSE proxying | `/api/` uses HTTP/1.1 and `proxy_buffering off` (`deploy/nginx.conf.example:18-25`) | PASS for configuration intent |
| SSE heartbeat budget | Backend emits a comment heartbeat every 1 second; nginx reads for up to 120 seconds (`python/hearttwin/api.py:849-891`; `deploy/nginx.conf.example:10`) | PASS for idle-stream continuity |
| SSE compression | `gzip_types` does not include `text/event-stream` (`deploy/nginx.conf.example:11-12`) | PASS by current MIME list; verify no higher-level gzip override |
| Upload limit | nginx allows 25 MiB (`deploy/nginx.conf.example:9`); case upload allows 200 MiB and ECG allows 50 MiB (`python/hearttwin/api.py:977-997`, `1089-1093`) | OPEN contract mismatch |
| Proxy timeouts | `proxy_read_timeout 120s` is explicit; connect and send timeouts are not | OPEN |
| Proxy caching | No cache directives are present; default nginx behavior is relied upon | OPEN for deployment-specific config |
| Security headers | `nosniff`, same-origin referrer policy, and `X-Frame-Options: DENY` are set with `always` (`deploy/nginx.conf.example:14-16`) | PASS baseline; incomplete public hardening |
| TLS and HSTS | Example listens on port 80 only and has no TLS or HSTS configuration (`deploy/nginx.conf.example:7-8`) | NOT VERIFIED / public-release blocker |
| Host identity | `beatit.example.invalid` is a placeholder (`deploy/nginx.conf.example:8`) | NOT deployable without operator replacement |
| Live parser/browser proof | nginx is not installed on this host; no public proxy or browser EventSource run was available | NOT VERIFIED |

## SSE semantics

### Verified strengths

- The API's stream route emits the correct `text/event-stream` media type and
  disables response caching. `X-Accel-Buffering: no` also gives nginx an
  application-side signal not to buffer the response
  (`python/hearttwin/api.py:829-846`).
- The `/api/` location sets `proxy_http_version 1.1` and
  `proxy_buffering off`, which is appropriate for forwarding incremental
  EventSource events rather than waiting for a response buffer to fill
  (`deploy/nginx.conf.example:18-25`).
- The backend sends a comment ping once per polling interval, currently one
  second, so the 120-second `proxy_read_timeout` is comfortably above the
  expected idle interval (`python/hearttwin/api.py:849-891`).
- The frontend uses the browser's EventSource reconnect behavior and the
  backend accepts `Last-Event-ID`/`last_id`, so the proxy does not need a
  special resume mechanism (`web/hooks/useTraceStream.ts:7-10,54-66`;
  `python/hearttwin/api.py:829-846`).
- The configured gzip MIME list excludes `text/event-stream`; this reduces the
  risk that compression buffering delays trace events. This is a property of
  this example only and should be rechecked if a distribution-wide nginx
  include changes gzip types.

### Remaining SSE checks

The configuration does not explicitly set `proxy_cache off`,
`proxy_connect_timeout`, or `proxy_send_timeout`. Caching is normally disabled
unless enabled elsewhere, but a deployment example should either state that
assumption or make the SSE behavior explicit. Connect and send deadlines
should be selected for the target host and failure-tested rather than
inherited from an unknown global nginx configuration.

The `proxy_buffering off` directive currently applies to every `/api/` route,
not only `/api/v1/cases/.../trace/stream`. That is safe for event delivery but
broader than necessary and may reduce response buffering efficiency for normal
JSON endpoints. A production deployment can retain the broad setting for
simplicity, or add a narrowly scoped SSE location after testing route matching
and the unchanged upstream URI.

Required deployment proof:

1. Run nginx in front of the launcher and open a real browser EventSource.
2. Capture setup, trace, heartbeat, disconnect, and reconnect events.
3. Confirm that `Last-Event-ID` resumes without replaying already-consumed
   local events.
4. Stop or restart the backend and record the browser error/reconnect state and
   bounded proxy behavior.

## Request-size and resource limits

The example's `client_max_body_size 25m` is syntactically valid and provides a
useful early proxy boundary, but it is not aligned with the application
contract:

- `/api/v1/cases/{case_id}/files` accepts up to 200 MiB after reading the full
  upload body (`python/hearttwin/api.py:977-997`).
- `/api/v1/ecg/diagnose` accepts up to 50 MiB after reading the full CSV body
  (`python/hearttwin/api.py:1089-1093`).

Therefore, a client using this nginx example receives a proxy rejection for
valid application-sized uploads above 25 MiB. That can be an intentional
synthetic-demo policy, but it must be documented as the public contract or
aligned with the application limits. Raising the proxy limit without adding
resource controls would increase exposure: both handlers buffer the complete
body in memory before applying their application-level size check, and the
reviewed API has no global upload concurrency or rate limit.

The required closure decision is one of:

- set and document 25 MiB as the supported deployment limit and make the API
  return a consistent error contract for that boundary; or
- raise the proxy limit only with an explicit memory/concurrency budget and
  oversized/parallel-upload tests; or
- implement a bounded streaming upload path before claiming the larger API
  limits through a public proxy.

## Security-header and exposure review

### Positive controls

The example sets three useful baseline response headers with `always`, so they
also apply to many error responses:

- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: same-origin`
- `X-Frame-Options: DENY`

The application services are upstream-only loopback listeners in the documented
launcher (`deploy/beatit:46-49`), and the proxy passes `Host`, forwarded client
address, and scheme headers to both upstreams (`deploy/nginx.conf.example:21-23`,
`30-32`).

### Open public-deployment hardening

- The example is HTTP-only. It has no certificate, HTTPS redirect, HSTS, or
  documented public hostname. Do not treat the three baseline headers as a
  complete browser security policy.
- There is no Content Security Policy or Permissions Policy. These require
  validation against the Next.js assets, WebGL heart view, CopilotKit, and any
  future third-party resources before being tightened.
- The API currently configures wildcard CORS with credentials enabled
  (`python/hearttwin/api.py:111-117`). nginx headers do not correct that
  cross-origin policy; a public deployment must restrict allowed origins and
  test credential behavior separately.
- The frontend location always forwards `Connection: upgrade` and the
  `Upgrade` header (`deploy/nginx.conf.example:27-35`), although the current
  product uses SSE rather than a websocket endpoint. If websocket transport is
  added under `/api/`, the API location would also need explicitly scoped
  upgrade handling and handshake tests.
- `server_name beatit.example.invalid` is intentionally non-routable and must
  be replaced. The replacement must be paired with a host allow-list/default
  server policy so arbitrary Host headers do not select the application.

## Validation performed

- Read the complete nginx example and compared each relevant directive with
  the FastAPI SSE, health, and upload implementations.
- Confirmed the frontend EventSource URL and resume contract in
  `web/hooks/useTraceStream.ts` and `web/lib/api.ts`.
- Confirmed the launcher binds the app processes to loopback.
- Confirmed `nginx` is not installed on this host, so `nginx -t` could not be
  run. No claim of parser-level nginx validity is made here.
- This review file is the only intended file change for contribution A16.

## Release disposition

**Proxy gate: OPEN / FAIL for public release.** The example is a credible
loopback and local SSE baseline, but the upload-limit mismatch, missing
deployment-level timeout/cache policy, absent TLS/public-host configuration,
wildcard credentialed CORS, and lack of live nginx/browser evidence prevent a
production-ready claim. The current evidence supports a synthetic local demo
only, with the limitations made explicit.
