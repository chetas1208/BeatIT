# M9 State Review — Loading, Error, Empty, Stale

Date: 2026-09-26  
Scope: `TWIN`, `EXPERIMENT`, `COMPARE`, `EVIDENCE`, `REPORT`. Source-only audit;
no production files were changed.

## Verdict

**OPEN.** Local empty/error messages exist, but async results are mostly
component-local or inferred from booleans. Old artifacts can remain visible
after a request or context changes, and REPORT does not validate freshness or
lineage.

## Findings

### STATE-1 — TWIN has no central loading/unavailable state (P1)

`HeartScene` immediately renders from whatever store state exists. Its only
first-load message is the client-only canvas placeholder, `initializing
viewport` ([`HeartScene.tsx:927-947`](../../../web/components/heart/HeartScene.tsx#L927-L947)).
Pipeline progress/error is visible in the intake/header rail, but the central
Twin surface has no explicit no-case, updating, backend-error, or structured
renderer-unavailable state. `ErrorBoundary` offers Retry but exposes a
truncated exception rather than a useful data-preserving fallback
([`ErrorBoundary.tsx:39-55`](../../../web/components/ui/ErrorBoundary.tsx#L39-L55)).

### STATE-2 — TWIN can display a stale hypothetical branch (P0)

`HeartScene` prefers `selectedEnsembleSample`, then `scenario.result`, before
the selected temporal snapshot/store state
([`HeartScene.tsx:1038-1048`](../../../web/components/heart/HeartScene.tsx#L1038-L1048)).
The same component is mounted in all five product modes
([`AppShell.tsx:116-133`](../../../web/components/layout/AppShell.tsx#L116-L133)).
After Experiment/Evidence activity, TWIN can therefore show simulated output
instead of the observed continuity snapshot. The branch label does not repair
the ownership violation.

### STATE-3 — EXPERIMENT keeps old results visible during replacement (P1)

`PlausibleTwinsPanel` sets `loading` but does not clear or mark the existing
ensemble stale before awaiting a new one; `useScenario` replaces it only after
the request resolves ([`PlausibleTwinsPanel.tsx:50-59,77-123`](../../../web/components/twin/ensemble/PlausibleTwinsPanel.tsx#L50-L123), [`useScenario.tsx:111-129`](../../../web/lib/twin/scenario/useScenario.tsx#L111-L129)).
Old distributions, provenance, and nested Missing Piece output can appear
current beside `Generating…`. Shadow Trial has the same issue: `trialRun` is
cleared only on failure, so the prior trial remains visible while a replacement
request is active ([`ShadowTrialPanel.tsx:94-151`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L94-L151)).

### STATE-4 — COMPARE replacement failures are silent (P1)

`useComparisonStore.selectPair` updates only when projection succeeds; a
missing/invalid pair returns without changing state
([`store.ts:29-39`](../../../web/components/twin/comparison/store.ts#L29-L39)).
If a valid pair is open, a failed replacement can leave that old pair rendered
with no stale or error reason. The route-level no-pair message only covers
`paired === null` ([`AppShell.tsx:120-128`](../../../web/components/layout/AppShell.tsx#L120-L128)).

### STATE-5 — EVIDENCE analysis is not invalidated by ensemble changes (P0)

`MissingPiecePanel` stores `result` locally and clears it only when the user
changes the metric. It does not react to a changed `ensembleId` prop
([`MissingPiecePanel.tsx:37-60`](../../../web/components/twin/missing-piece/MissingPiecePanel.tsx#L37-L60)).
An analysis for ensemble A can therefore remain displayed after ensemble B is
passed by the parent. The panel needs an identity/context guard and late-result
rejection.

### STATE-6 — REPORT readiness is presence, not current validity (P0)

`ReportSurface` derives readiness from in-memory booleans and IDs, treating any
ensemble as Evidence and any scenario/ensemble as Experiment
([`ReportSurface.tsx:20-35`](../../../web/components/product/ReportSurface.tsx#L20-L35)).
`buildProductReport` exposes only `ready` or `unavailable` from those booleans
([`reportContracts.ts:33-51`](../../../web/lib/product/reportContracts.ts#L33-L51)).
There is no loading, stale, partial, fetch-error, exact lineage, or persisted
artifact state. A direct load/reload cannot verify the artifact chain; the
preflight records this as an open M9 gap
([`M9_PREFLIGHT.md:151-167`](../M9_PREFLIGHT.md#L151-L167)).

## Existing positive states

- Twin timeline has an explicit no-snapshot state
  ([`Timeline.tsx:89-99`](../../../web/components/twin/timeline/Timeline.tsx#L89-L99)).
- Experiment explains missing snapshots; Compare explains missing pairs and
  links to Experiment ([`ScenarioPanel.tsx:28-30`](../../../web/components/twin/scenario/ScenarioPanel.tsx#L28-L30), [`AppShell.tsx:120-128`](../../../web/components/layout/AppShell.tsx#L120-L128)).
- Missing Piece has explicit no-ensemble/no-analysis states and Retry
  ([`MissingPiecePanel.tsx:121-143`](../../../web/components/twin/missing-piece/MissingPiecePanel.tsx#L121-L143)).
- Report retains unavailable sections and the safety disclaimer
  ([`reportContracts.ts:47-56`](../../../web/lib/product/reportContracts.ts#L47-L56)).

## Required closure

Use one context-keyed state model for every async artifact:

```text
empty → loading(requestId, contextKey) → ready(value, contextKey)
                                      ↘ error(retryable, contextKey)
ready + context/request change → stale(reason)
```

At minimum, test origin/ensemble changes, replacement requests, late responses,
direct reload/deep links, invalid Compare selection, and partial/stale REPORT
inputs. TWIN must remain observed-state-first.

## Verification

`cd web && ./node_modules/.bin/tsc --noEmit` — **PASS**.

No browser sign-off is claimed; the M9 preflight records Chromium blocked by
missing `libasound.so.2` and Firefox unavailable
([`M9_PREFLIGHT.md:183-210`](../M9_PREFLIGHT.md#L183-L210)).
