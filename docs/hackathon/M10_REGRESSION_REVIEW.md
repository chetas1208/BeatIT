# M10 Agent 02 — Regression Review

Date: 2026-09-26 UTC  
Scope: regression evidence only; no production code changed.

## Verdict

No new Python, TypeScript, lint, required runtime-contract, or production-build
regression was observed in the final current-tree comparison.

The release is **not fully regression-clear** because the broader frontend
runtime run remains red with nine failures. All nine reproduce in the clean
baseline and are therefore inherited or harness/test-contract failures, not
regressions attributable to the current M10 worktree.

The worktree was concurrently advanced during this audit. The first run was
against `d0fdab9`; `HEAD` then advanced to `f5578b4aee8d925b539d5726995a80491513e4e0`.
The final comparison below uses a fresh clean export of `f5578b4` and the
current worktree after that advance. An earlier pre-advance run reported
`1231 passed`; the repeatable final-state run reported `1126 passed`. This
difference is recorded as worktree drift, not interpreted as a product
regression.

## Verification matrix

| Gate | Current worktree | Clean `f5578b4` baseline | Classification |
|---|---:|---:|---|
| Full Python suite | 1126 passed, 5 skipped, 6 xfailed; 486 warnings; 1137 collected | 1126 passed, 5 skipped, 6 xfailed; 486 warnings; 1137 collected | No delta |
| Direct TypeScript | PASS | PASS | No regression |
| Direct ESLint | PASS; 0 errors, 4 warnings | FAIL: clean baseline has no `eslint.config.*` | Current improvement; baseline tooling gap |
| Required direct runtime contract | PASS; 5 passed | PASS for the baseline contract | No regression |
| All-file direct frontend runtime | 124 passed, 9 failed; 133 tests | 42 passed, 9 failed; 51 tests | Same 9 failures; no added failure |
| Direct Next production build | PASS; routes generated | FAIL: `Couldn't find any pages or app directory` | Current improvement; baseline lacks current App Router surface |

Commands used for the final current-tree gates:

```text
pnpm test:py
./web/node_modules/.bin/tsc -p web/tsconfig.json --noEmit
cd web && ./node_modules/.bin/eslint
node --experimental-strip-types --loader ./web/tests/alias-loader.mjs --test \
  ./web/tests/m5-runtime.test.ts \
  ./web/lib/twin/ensemble/__tests__/inspectorModel.test.ts
node --experimental-strip-types --loader ./web/tests/alias-loader.mjs --test \
  $(find web -path 'web/node_modules' -prune -o -type f -name '*.test.ts' -print | sort)
cd web && ./node_modules/.bin/next build
```

The clean-baseline Python command was:

```text
python -m pytest python/hearttwin/tests
```

The package-manager `pnpm exec tsc --noEmit` and `pnpm test:runtime` wrappers
also attempted dependency bootstrap and stopped with
`ERR_PNPM_IGNORED_BUILDS` for `@scarf/scarf`, `es5-ext`, `sharp`, and
`unrs-resolver`. The direct binaries above executed the actual gates. This is
an environment/package-manager blocker, not a source failure.

## Exact inherited frontend runtime failures

The same failures occurred in both the clean baseline and current tree:

1. `web/lib/heart/__tests__/patient-report.test.ts`
   - `patient binding preserves measured values, source provenance, and localized findings`:
     expected labels `Contractility index`, `Afterload index`, `Stroke volume`; actual
     labels `Contractility Index`, `Afterload Index`, `Stroke Volume Ml`.
   - `patient binding preserves direct, extracted, derived, and unavailable evidence kinds`:
     expected `insufficient_evidence`; actual `observed`.
2. `web/lib/twin/ensemble/__tests__/provenance.test.ts` — loader rejects the
   parameter property in `web/lib/twin/time/clocks.ts:367` with
   `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`.
3. `web/lib/twin/ensemble/__tests__/runner.test.ts` — same loader failure at
   `web/lib/twin/time/clocks.ts:367`.
4. `web/lib/twin/events/__tests__/eventStore.test.ts` — same loader failure at
   `web/lib/twin/time/clocks.ts:367`.
5. `web/lib/twin/reducer/__tests__/reducer.test.ts` — same loader failure at
   `web/lib/twin/time/clocks.ts:367`.
6. `web/lib/twin/scenario/__tests__/history.test.ts`
   - `push stores the present result and clears the redo branch`: expected
     `past: [first, second]`; actual `past: [first]`.
7. `web/lib/twin/scenario/__tests__/propagation.test.ts` — same loader failure
   at `web/lib/twin/time/clocks.ts:367`.
8. `web/lib/twin/snapshots/__tests__/snapshots.test.ts` — same loader failure
   at `web/lib/twin/time/clocks.ts:367`.

The current-only product and comparison runtime additions increased the run
from 51 to 133 tests; they passed and introduced no additional failure.

## Lint warnings

The current direct lint gate has no errors and four warnings:

- `web/components/careguard/cases/CaseDetail.tsx:89,103`: raw `<img>` warnings.
- `web/lib/assistant/__tests__/useReducedMotion.test.ts:14,20`: unused
  `_query` warnings.

These are warnings, not M10 regressions.

## Python warning inventory

The Python suite is green in both trees. The 486 warnings are unchanged and
are dominated by:

- FastAPI `on_event` deprecation warnings in CareGuard.
- `datetime.utcnow()` deprecation warnings from Pydantic model construction.

No Python test failure or changed failure count was observed.

## Attribution and release disposition

- **M10 regression found:** none in the comparable automated gates.
- **Inherited P1 closure items:** the nine all-file frontend runtime failures
  above; the six loader failures require a test-runner/transpilation decision,
  while the patient-report and scenario-history failures require contract/test
  reconciliation.
- **Environment blocker:** pnpm ignored-build-script policy prevents the
  package wrappers from reaching TypeScript/runtime execution.
- **Open release evidence:** browser/WebGL/accessibility/manual journey gates
  were not run in this audit.

The current worktree passes the narrow release gates but should not be called
fully regression-closed until the inherited frontend runtime failures are either
repaired or explicitly quarantined with an accepted release decision.
