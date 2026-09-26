# M10.5 Agent 22 — Frontend Integration Verification

**Date:** 2026-09-26  
**Scope:** API client, five product-mode routes, loading/error/empty states, stale-result handling, and direct frontend checks.  
**Disposition:** **PARTIAL — do not close the frontend integration gate.**

## Verification commands

All commands were run from `web/` and did not require a live backend.

| Check | Result | Evidence |
|---|---|---|
| `./node_modules/.bin/tsc --noEmit` | PASS | Exit code 0; no diagnostics. |
| `./node_modules/.bin/eslint app components hooks lib types` | PASS WITH WARNINGS | Exit code 0; 0 errors and 4 existing warnings: two `no-img-element` warnings in `components/careguard/cases/CaseDetail.tsx`, and two unused `_query` warnings in `lib/assistant/__tests__/useReducedMotion.test.ts`. |
| Direct Node runtime suite | PASS | 8 tests passed, 0 failed: navigation, report contracts, M5 runtime contracts, and ensemble inspector model. |

Runtime command:

```text
node --experimental-strip-types --loader ./tests/alias-loader.mjs --test \
  ./lib/product/__tests__/navigation.test.ts \
  ./lib/product/__tests__/reportContracts.test.ts \
  ./tests/m5-runtime.test.ts \
  ./lib/twin/ensemble/__tests__/inspectorModel.test.ts
```

The Node loader emitted expected experimental-feature warnings; they did not affect the result.

## API client integration

**Verified strengths:**

- `web/lib/api.ts` has one typed request path for the backend methods used by cases, ensembles, Shadow Trial, Missing Piece, trace, and system checks.
- Case, trial, ensemble, and analysis identifiers are URL-encoded before interpolation.
- Non-2xx JSON responses preserve `detail`/`error` and `safety_disclaimer` in `ApiRequestError`.
- Fetch/network failures become a typed status-0 error instead of silently fabricating fallback data.
- The SSE URL supports an explicit `last_id`; `useTraceStream` clears when a new case begins and resumes the same case from its last event ID.

**Open integration risk:** requests do not provide an `AbortSignal`, client timeout, or request-generation token. Long-running or abandoned requests therefore depend on the backend/fetch lifecycle, and individual callers must guard against stale completion themselves.

## Product mode routes

The five supported routes are `/twin`, `/experiment`, `/compare`, `/evidence`, and `/report`.

- The Next route validates the dynamic segment with `isBeatITMode()` and returns `notFound()` for unknown segments.
- Client navigation writes only the mode path to browser history and listens for `popstate`; no case or payload data is placed in the URL.
- The direct navigation test passed all five mappings and the fail-closed behavior for `/careguard/runner`.
- Compare has an explicit prerequisite state when no valid paired result is selected; it directs the user to Experiment and does not infer a comparison.

## Loading, error, and empty states

The inspected surfaces expose useful state distinctions:

- Case intake shows stage progress, disables the run action while busy, and renders pipeline failures through a `role="alert"` message.
- Plausible Twins exposes `aria-busy`, disables generation while running, and has a no-lineage empty state plus an `aria-live` status/error message.
- Shadow Trial disables its action while running, retains invalid-pair counts, and suppresses effect summaries when no valid pair exists.
- Missing Piece has no-ensemble, no-analysis, loading, retryable error, incomplete-coverage, and unavailable-result states; it preserves the API safety disclaimer in a completed response.
- Report and comparison surfaces render explicit unavailable/no-metrics messages rather than fabricating values.
- Error boundaries wrap the major workspace rails and product surfaces, but browser-level error-boundary rendering was not exercised in this check.

## Stale-result review

### Release-relevant finding: pipeline results are not invalidated at rerun start

`useDualBeatStore.runPipeline()` clears only `error` before beginning a new run. It does not clear the prior `validatedFields`, `state`, `visualization`, `evaluation`, `scenarios`, `stageResults`, `weave`, or comparison state. If a rerun fails during create, extract, operate, or recovery, the header can show `Run failed` while the workspace continues displaying results from the previous run. During a long rerun, old results also remain visible until each corresponding stage replaces them.

**Disposition:** P1 integration blocker for a truthful release UI. Start each run with an explicit generation/reset policy, or render all result panels as belonging to the previous run until the new run completes. Add a regression test covering success → failed rerun and asserting that old outputs cannot be presented as current.

### Release-relevant finding: Missing Piece result is not keyed to the current request

`MissingPiecePanel` clears its result when the metric changes, but it does not clear or identify the result when `ensembleId` changes. An in-flight request also unconditionally calls `setResult()` when it resolves. A user can therefore select a new metric or ensemble and later receive the old request's analysis under the new selection.

**Disposition:** P1 integration blocker for evidence integrity. Associate each result with `ensembleId`, metric, and a request revision; discard completions that no longer match current props/state. Add a delayed-response test for metric and ensemble changes.

### Positive stale-state protections

- `useScenario` invalidates ensemble generations with a revision counter and rejects late results for a changed snapshot.
- Shadow Trial renders a stored trial only when its ensemble and scenario IDs match the current scenario context.
- Trace streaming clears events for a new case and resumes only for the same case.

## Final assessment

The direct frontend type, lint, route, report, and runtime checks pass. Product surfaces have explicit loading, error, empty, and safety states. However, the frontend integration gate remains **OPEN** until rerun invalidation and Missing Piece request identity are fixed and covered by regression tests. No production or test files were modified by this verification; this contribution adds only this review document.

