# M10 Final Test Matrix

Date: 2026-09-26 UTC

| Gate | Command/evidence | Result |
|---|---|---|
| Python full suite | `PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev pytest -q` | `1233 passed, 5 skipped, 6 xfailed` |
| API health/readiness | `python/hearttwin/tests/test_api_routes.py` | Included in full suite; focused health tests pass |
| Frontend TypeScript | `cd web && ./node_modules/.bin/tsc --noEmit` | Pass after `next build` generated route types |
| Frontend lint | scoped direct ESLint | Pass; warnings are non-blocking |
| Product runtime | alias-aware Node test command | 3 passed |
| Next production build | `cd web && ./node_modules/.bin/next build` | Pass; routes generated |
| Demo preflight | `./scripts/demo-preflight.sh` | Pass; HTTP checks intentionally skipped without `E2E_BASE_URL` |
| Demo seed | `./scripts/seed-demo.sh` | Pass; deterministic smoke `RESULT: OK` |
| Launcher ownership | `./deploy/beatit status` | Pass; reports only its own recorded services |
| Self-host lifecycle | alternate ports: `up`, HTTP preflight, frontend root, `down` | Pass locally; public proxy/TLS not exercised |
| Full frontend runtime | M10 regression review | 9 inherited failures remain |
| Browser/AT/WebGL | Playwright launch attempt | Blocked by missing browser dependencies |
| Public deployment | nginx/public hostname | Not run |
| Chaos/restart | service/model/database fault injection | Not run |

The first parallel TypeScript invocation raced the initial production build and
failed because `.next/types/routes.js` was not generated yet. The sequential
post-build TypeScript check passed; this is recorded as an ordering issue, not
a source failure.
