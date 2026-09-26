# M10.5 Agent 17 — Browser E2E Verification

**Scope:** attempt real browser automation against the self-hosted loopback
application, then run non-browser route smoke when browser execution is blocked.

**Audit date:** 2026-09-26 UTC

**Disposition:** **OPEN — browser E2E is blocked by host dependencies; local
HTTP route smoke passes.**

## Safety boundary

The verification used synthetic demo/runtime data only. It did not change
production code, fixtures, databases, Docker services, or user data. The
application was started on isolated ports `18001` (FastAPI) and `13002`
(Next.js), and both temporary processes were terminated by the probe.

The default ports were not used because `127.0.0.1:8000` was already occupied
by a process returning `404` for the BeatIT health routes. No existing process
was stopped.

## Browser capability check

Playwright was available through the host Python installation:

```text
Playwright 1.63.0
cached Chromium: /home/923873155/.cache/ms-playwright/chromium-1243/...
cached Firefox: /home/923873155/.cache/ms-playwright/firefox-1538/...
```

The repository does not declare Playwright, Puppeteer, Cypress, or a browser
E2E test script in `web/package.json`. The host did provide the Playwright CLI
and Python package, so a real headless launch was attempted rather than
crediting static checks as browser coverage.

## Browser attempt

The probe launched Playwright Chromium and Firefox headlessly and attempted to
navigate the self-hosted app at `http://127.0.0.1:13001`. Neither browser
reached a page:

| Browser | Result | Exact blocker |
| --- | --- | --- |
| Chromium | BLOCKED | The cached headless shell exited with code `127`: `libasound.so.2: cannot open shared object file` |
| Firefox | BLOCKED | Playwright 1.63 expected `/home/923873155/.cache/ms-playwright/firefox-1543/firefox/firefox`, which is not installed |

The host library check also confirmed `libasound.so.2` is absent. No browser
DOM, console, WebGL, keyboard, focus, or accessibility assertions are claimed.
No package or system dependency installation was attempted.

## Non-browser self-host smoke

Because browser execution was unavailable, a temporary in-session pair was
started from the built application:

```text
python -m uvicorn api.index:app --host 127.0.0.1 --port 18001
web/node_modules/.bin/next start -p 13002
```

Results:

```text
AGENT 17 NON-BROWSER SMOKE PASS
frontend=/ 200 46186 bytes
frontend=/twin 200 46532 bytes
frontend=/experiment 200 46544 bytes
frontend=/compare 200 46538 bytes
frontend=/evidence 200 46540 bytes
frontend=/report 200 46536 bytes
backend=/api/health/live 200 281 bytes
backend=/api/health/ready 200 704 bytes
backend=/api/v1/system-check 200 1720 bytes
backend=/api/v1/models/status 200 1250 bytes
```

The liveness response contained `status`, `service`, and
`safety_disclaimer`. The model-status response contained `deterministic_twin`,
`models`, and `safety_disclaimer`.

## Launcher observation

`BEATIT_API_PORT=18000 BEATIT_WEB_PORT=13001 ./deploy/beatit up` reported
`BEATIT READY`, and its health check passed before the command returned. In
this execution environment, the recorded detached processes were no longer
serving after the command session closed. This is not credited as restart or
deployment persistence proof; it requires follow-up in the target host/service
supervisor environment.

## Release boundary

The route smoke establishes that the built Next.js pages and FastAPI health,
system-check, and model-status endpoints respond on an isolated local pair. It
does not prove browser rendering, WebGL, hydration, client-side navigation,
CopilotKit interaction, SSE behavior, keyboard accessibility, reverse-proxy
behavior, TLS, or deployed-process persistence.

**Final result: browser gate OPEN; non-browser local route smoke PASS; overall
M10.5 release certification is not implied.**
