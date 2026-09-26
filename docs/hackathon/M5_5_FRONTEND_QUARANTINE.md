# M5.5 Frontend Computation Quarantine

Status: **confirmed historical-only for production imports**.

This audit covers `web/lib/twin/ensemble/runner.ts` and
`web/lib/twin/ensemble/distributions.ts`. No production behavior was changed.
M6, M7, and M8 were not started.

## Conclusion

The active frontend does not import `runner.ts`. It requests ensemble results
from the canonical Python backend and maps the response without recomputing
physiology:

1. `web/lib/twin/scenario/useScenario.tsx:25` imports
   `generateBackendEnsemble` from `web/lib/twin/ensemble/backend.ts`.
2. `web/lib/twin/ensemble/backend.ts:1-3` imports the API client, contracts,
   and `adapter.ts`; it does not import `runner.ts` or `distributions.ts`.
3. `web/lib/twin/ensemble/backend.ts:52-67` sends the request to the backend
   and returns `mapBackendEnsembleResponse(response)`.
4. `web/lib/twin/ensemble/adapter.ts:5-64` maps the wire response and does not
   recalculate physiological outputs.

The scenario UI reaches this path through
`web/components/twin/scenario/ScenarioPanel.tsx:8,11-14,51`, which consumes
`useScenario()` and renders the resulting ensemble. No active production import
path reaches either quarantined module.

## Exact import evidence

The source/test scan used `rg` over `.ts`, `.tsx`, `.js`, and `.jsx` files while
excluding `node_modules`, `.next`, `dist`, and `build` content.

### `runner.ts`

The only import of the module is from its historical tests:

| File and line | Classification |
| --- | --- |
| `web/lib/twin/ensemble/__tests__/provenance.test.ts:5` | Historical test import of `runEnsemble` |
| `web/lib/twin/ensemble/__tests__/runner.test.ts:5` | Historical test import of `runEnsemble` and `chooseRepresentatives` |

There are no production imports of
`@/lib/twin/ensemble/runner` or a relative equivalent. The module itself
imports the separate sampler at `web/lib/twin/ensemble/runner.ts:4` and
implements the retained local computation at `web/lib/twin/ensemble/runner.ts:115-171`.

### `distributions.ts`

The module has these source-level references:

| File and line | Classification |
| --- | --- |
| `web/lib/twin/ensemble/runner.ts:4` | Dependency of the historical local runner |
| `web/lib/twin/ensemble/index.ts:2` | Barrel re-export; no production import of this barrel was found |
| `web/lib/twin/ensemble/__tests__/distributions.test.ts:7` | Historical distribution tests |
| `web/tests/m5-runtime.test.ts:7` | Runtime contract harness |

The active backend adapter path imports `contracts.ts` and `adapter.ts`, not
`distributions.ts`. Therefore the distribution implementation is also
production-inactive, although it remains intentionally available to tests and
the unused barrel export.

## Quarantine boundary

The quarantine is an import/usage boundary, not a deletion:

- Keep `runner.ts` and its sampler dependency available for historical M5
  tests and audit comparison.
- Do not use either module to produce active UI ensemble results.
- Treat Python `m5.5-ensemble-projection-v1` as the numerical authority for
  active ensemble sampling, validity, physiology projection, statistics,
  provenance, identifiers, and safety output.
- Any future reactivation requires an explicit parity decision and new
  cross-layer evidence; this document does not authorize that work.

## Verification evidence

Commands were run from `web/`:

```text
node --experimental-strip-types --loader ./tests/alias-loader.mjs --test ./tests/m5-runtime.test.ts
2 passed, 0 failed

./node_modules/.bin/tsc --noEmit
passed

./node_modules/.bin/eslint
passed with 2 existing warnings in components/careguard/cases/CaseDetail.tsx
```

The package-manager wrappers (`pnpm test:runtime`, `pnpm exec tsc --noEmit`,
and `pnpm lint`) stopped during dependency bootstrap with
`ERR_PNPM_IGNORED_BUILDS` for existing packages; the already-installed local
binaries above ran the corresponding checks successfully.

The retained runner/provenance test command was also attempted:

```text
node --experimental-strip-types --loader ./tests/alias-loader.mjs --test \
  ./lib/twin/ensemble/__tests__/runner.test.ts \
  ./lib/twin/ensemble/__tests__/distributions.test.ts \
  ./lib/twin/ensemble/__tests__/provenance.test.ts
```

The four distribution tests passed. The runner and provenance test files did
not execute because the strip-only loader rejected a TypeScript parameter
property in `web/lib/twin/time/clocks.ts:367`; this is a test-harness blocker,
not evidence that the retained runner is active or production-safe.

## Changed files

- `docs/hackathon/M5_5_FRONTEND_QUARANTINE.md` — audit record only.

No production files, tests, imports, or runtime behavior were modified.
