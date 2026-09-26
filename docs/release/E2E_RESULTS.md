# M10.5 End-to-End Results

Last run: 2026-09-26 UTC (`./scripts/verify-release.sh --deep`)

## Automated chain

| Step | Result |
|---|---|
| `./scripts/validate-env.sh` (via verify_env) | PASS |
| Demo fixtures + `verify-demo.sh` | PASS (`m10.5-demo-v1`) |
| Secret scan (git + rg) | PASS |
| Python pytest | **1314 passed**, 5 skipped, 6 xfailed |
| Frontend tsc/eslint/build + runtime `*.test.ts` | PASS |
| `scripts/verify_api_e2e.py` | PASS (ensemble + shadow trial + missing piece + reload) |
| `./deploy/beatit up` @ 18000/13001 | BEATIT READY |
| `./scripts/demo-preflight.sh` | DEMO READY |
| `run_local_smoke.py` HTTP | PASS (create→extract→operate→recovery) |
| Frontend root HTTP | 200 |

Machine-readable summary: `artifacts/release-verification.json`.

## Not exercised in this runner

- Full Playwright product journey (Twin → Report, WebGL, Split Heart interactions).
- nginx/Caddy TLS termination on a public hostname.
- Live language-model authenticated inference (inventory: `DETERMINISTIC_FALLBACK_READY`).
- PostgreSQL/Redis outage injection.

## Browser journey

**PARTIAL PASS** (2026-09-26): `scripts/browser_product_e2e.py` with Playwright
Chromium + user `libasound` shim — five product modes, SYNTHETIC chip, WebGL
canvas, primary-space nav buttons, keyboard tab smoke. Not the full judge script
(timeline scrub, Shadow Trial click-through, Split Heart modes, reload persistence).
