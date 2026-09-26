# M4 Test Plan

**Validation snapshot:** 2026-09-26 UTC  
**Scope:** M4 deterministic scenario engine, scenario UI integration, frontend
build gates, and Python regression safety.  
**Status:** M4 implementation is auditable but acceptance remains incomplete.

## M4-specific test inventory

The only M4 runtime test files currently present are:

- `web/lib/twin/scenario/__tests__/history.test.ts` — push, undo, redo, reset,
  and redo-branch clearing.
- `web/lib/twin/scenario/__tests__/propagation.test.ts` — observed-state
  isolation, origin/scenario identity, deterministic completion, causal paths,
  and the bounded afterload-to-stroke-volume relationship.

Together they contain five tests. They do not currently cover parameter-boundary
rejection, NaN/infinity, duplicate or unknown inputs, persistence round trips or
malformed envelopes, runtime immutability, visualization projection, component
deltas, or rendered accessibility behavior.

## Exact validation commands

Run from the repository root unless the command begins with `cd web`.

### 1. Focused M4 frontend lint

```bash
cd web
./node_modules/.bin/eslint \
  lib/twin/scenario \
  components/twin/scenario \
  components/twin/timeline \
  --max-warnings=0
```

Expected gate: exit 0. **Observed:** passed on 2026-09-26.

### 2. Frontend production build

```bash
cd web
./node_modules/.bin/next build
```

Expected gate: exit 0, including the build's TypeScript pass. **Observed:**
passed on 2026-09-26 with Next.js 16.2.7; all seven static pages generated and
the `/api/copilotkit` route built.

### 3. Direct frontend typecheck

```bash
cd web
./node_modules/.bin/tsc -p tsconfig.json --noEmit --pretty false --incremental false
```

Expected gate: exit 0. **Observed:** currently fails in generated
`.next/types/validator.ts` because `.next/types/routes.d.ts` is not recognized as
a module and `LayoutProps` is unresolved. The production build's own TypeScript
phase passed, so this standalone failure is a generated-artifact/configuration
gap rather than an observed M4 source error; rerun after regenerating or cleaning
the Next type artifacts.

### 4. Focused Python regression supporting the deterministic core

```bash
python -m pytest \
  python/hearttwin/tests/test_cardiac_formulas_golden.py \
  python/hearttwin/tests/test_pipeline_integration.py
```

Expected gate: exit 0. **Observed:** `22 passed, 25 warnings` in 0.23s.

### 5. Full Python regression

```bash
pnpm test:py
```

Equivalent direct command:

```bash
python -m pytest python/hearttwin/tests
```

Expected gate: exit 0. **Observed:** `701 passed, 10 failed, 1 skipped` in
9.15s. All ten failures are in `test_evaluator_agent.py` and
`test_validator_agent.py`; they call `asyncio.get_event_loop()` after the
Python 3.13 default loop is absent. This is an inherited compatibility gap, not
an M4 scenario failure, but it keeps the global regression gate red.

### 6. M4 frontend runtime tests — currently blocked

The repository has no frontend `test` script and no installed `tsx`, Vitest, or
Jest runner. The direct Node probe is:

```bash
cd web
node --experimental-strip-types --test \
  lib/twin/scenario/__tests__/history.test.ts \
  lib/twin/scenario/__tests__/propagation.test.ts
```

**Observed:** both files fail before test execution because Node cannot resolve
the TypeScript path alias `@/lib`. Runtime results must not be reported as
passed until a runner/alias-aware harness is installed or configured.

### 7. Full frontend lint (informational)

```bash
cd web
./node_modules/.bin/eslint . --max-warnings=0
```

**Observed:** fails with 6 errors and 4 warnings, all reported outside the M4
scenario-owned paths (primarily `components/careguard/*`, plus
`components/redis/RedisStatsRail.tsx` and `components/safety/DisclaimerModal.tsx`).
Use the focused M4 lint gate for M4 source ownership, while keeping this full
lint debt visible for release acceptance.

## Manual browser acceptance still required

Start the backend and frontend in separate terminals:

```bash
python -m uvicorn python.hearttwin.api:app --reload --port 8000
cd web
./node_modules/.bin/next dev
```

Then manually verify at `http://localhost:3000`:

1. Select an observed timeline snapshot and confirm its observed values remain
   unchanged after experimenting.
2. Change each of the five bounded controls, run **Experiment**, and confirm
   the result is labeled **HYPOTHETICAL SIMULATION**.
3. Confirm the causal graph shows returned paths/branches, including the SVR to
   MAP path, and that the displayed deltas are deterministic.
4. Confirm the scenario projection reaches both the 3D heart and the simulation
   charts while the observed baseline remains identifiable.
5. Exercise **Reset**, **Undo**, and **Redo** and confirm controls match the
   displayed scenario result.
6. Check keyboard operation, 320 CSS px width, and 200% zoom; verify that the
   scenario controls, graph relationships, status messages, and delta content
   remain understandable without relying on visual layout.
7. Check the browser console for runtime errors.

No browser/manual run was performed in this validation pass.

## Known acceptance gaps

- Full Python regression is red because of the Python 3.13 asyncio loop
  compatibility failures described above.
- Standalone `tsc` is blocked by stale/generated `.next/types` errors even
  though `next build` completed its TypeScript phase successfully.
- M4 runtime tests cannot execute: no frontend test runner is configured, and
  raw Node execution does not understand the `@/*` alias.
- The five existing M4 tests do not cover boundary validation, persistence,
  runtime freezing, projection integration, or rendered accessibility.
- Browser/manual acceptance, including responsive and keyboard checks, remains
  unverified.
- Full frontend lint has unrelated pre-existing errors outside M4.
- The existing M4 review records a known bounded educational PV/afterload
  limitation; scenario outputs must not be described as patient-specific
  predictions or clinical evidence.
- `pnpm -C web ...` currently attempts dependency verification and stops with
  `ERR_PNPM_IGNORED_BUILDS` for ignored package build scripts in this workspace.
  Direct installed binaries were used for the frontend gates above.

M4 should remain marked incomplete until the runtime tests, full regression
policy, and browser/manual acceptance are resolved or explicitly waived.
