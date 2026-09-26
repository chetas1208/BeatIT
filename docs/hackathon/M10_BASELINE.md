# M10 Baseline

Baseline captured: 2026-09-26 UTC before release-hardening changes.

This file is a historical pre-hardening snapshot. The canonical final local
run is recorded in `M10_TEST_MATRIX.md` and `M10_COMPLETION.md`.

## Repository state

The worktree is intentionally dirty from M5.5 through M9 and Wave 6 model
runtime work. M10 preserves those changes and does not use destructive Git
operations. Scope is frozen in `M10_SCOPE_FREEZE.md`.

## Host evidence

| Resource | Observed |
|---|---|
| OS/kernel | Ubuntu Linux 6.8, x86_64 |
| CPU | 20 logical CPUs |
| RAM | 125 GiB total; 104 GiB available at audit time |
| GPU | 2 × NVIDIA GeForce RTX 3090, 24,576 MiB each |
| Driver | 535.288.01 |
| Root disk | 3.6 TiB total, 743 GiB available |
| `/usr/data` | 2.7 TiB total, 2.2 TiB available |
| Docker | Server 29.5.3 |
| PostgreSQL | `postgres:16-alpine`, healthy, host port 5432 |
| Valkey | `valkey/valkey:7-alpine`, host port 6379 |
| VISTA checkpoint | present outside repo; optional and lazily loaded |

## Test and build baseline

- Python suite: **1231 passed, 5 skipped, 6 xfailed** in 13.41 seconds.
- API route focus after readiness additions: **14 passed**.
- Frontend product runtime tests: **3 passed** using the direct Node loader.
- Frontend TypeScript, scoped ESLint, and direct Next production build pass
  when run from `web/` with local binaries.
- `pnpm -C web test:runtime` and `pnpm -C web lint` are blocked before task
  execution by pnpm's ignored-build-script policy for `@scarf/scarf`,
  `es5-ext`, `sharp`, and `unrs-resolver`.
- Browser sign-off remains blocked: Chromium lacks `libasound.so.2` and the
  Playwright Firefox executable is unavailable.

## Canonical final local run (2026-09-26 war-room refresh)

- Python suite: **1314 passed, 5 skipped, 6 xfailed** (full `pnpm test:py`).
- Frontend runtime (all `*.test.ts`): **161 passed, 0 failed** after reducer + loader fixes.
- `./deploy/beatit up` on ports 8010/3010: **BEATIT READY**; `demo-preflight.sh` with `E2E_BASE_URL`: **DEMO READY**.
- SQLite ensemble persistence across reload: **verified** (same `BEATIT_ENSEMBLE_DB_PATH`).
- Python final suite after earlier M10 code changes: **1233 passed, 5 skipped,
  6 xfailed** (superseded by counts above except where noted).
- The earlier `1231 passed` value above is retained as the pre-hardening
  baseline, not the release-candidate total. The separate regression review's
  clean-export `1126 passed` run is an attribution snapshot and is not the
  canonical final run.

## Runtime baseline

Existing API health and deterministic `/api/v1/system-check` routes are
available. M10 adds explicit `/api/health/live`, `/api/health/ready`, and
`/api/v1/system-status` semantics; the focused tests pass. The deterministic
twin is core-ready while language, Weave, Redis, and VISTA are optional or
degraded when their providers are not configured.

## Baseline risks

- Self-host deployment files and one-command demo seed/reset are not yet
  established.
- Persistence is primarily local SQLite/file-backed; PostgreSQL/Valkey are
  present but not the declared authority for all existing stores.
- The local VISTA checkpoint is structurally available but no compatible live
  inference runner is configured.
- Persisted artifact rehydration, browser QA, and full chaos/restart evidence
  are open gates inherited from M9.
