# M10 Frontend Release Review (A23)

Date: 2026-09-26  
Scope: product routes, loading/error/empty/fallback states, stale-result invalidation, and safe labels  
Disposition: **OPEN — frontend release gate not passed**  
Change scope: documentation only; no production or test files were modified.

## Executive finding

The five-space product shell has useful honest states and strong source labels. It
fails closed for unknown product routes, preserves unavailable report sections,
surfaces API and panel failures, and labels observed/derived/simulated/prior/
synthetic content in the main product surfaces.

The release gate remains open because result invalidation is not complete. A new
pipeline run leaves the prior twin, visualization, evaluation, and recovery
results in the global store while the new run is loading or after it fails. More
importantly, changing the selected temporal snapshot resets the scenario
controller's derived view, but `result` still reads the prior session history;
the report can therefore combine the new snapshot context with an old
hypothetical result. The comparison store also has no selected-snapshot lineage
key, so an already-open Split Heart pair can outlive the snapshot that produced
it.

These are release-integrity issues, not cosmetic loading defects: the UI can show
a valid-looking computational result whose origin is no longer the active one.

## Surface audit

| Surface | Loading / progress | Error state | Empty / unavailable state | Release assessment |
| --- | --- | --- | --- | --- |
| `/twin` | Intake status ladder and trace stream status; heart surface is wrapped in an error boundary | Pipeline error appears in the header and intake stage row; panel runtime errors are isolated | Timeline and evaluation use explicit standby/empty states; heart fallback behavior is not browser-verified | **Partial** |
| `/experiment` | Scenario controls and plausible-twin generation expose `aria-busy`/status text | Ensemble generation catches and announces an alert; parameter validation is surfaced inline | No selected snapshot and no computed branch are explicit | **Partial — stale scenario result open** |
| `/compare` | No async loading state in the comparison surface itself | Render failures are isolated by `ErrorBoundary` | Missing pair gives “No valid paired result is selected” and routes back to Experiment | **Partial — pair lineage can outlive snapshot** |
| `/evidence` | Ensemble generation shows “Generating…” | Generation failure is announced as an alert | No snapshot and no ensemble have explicit messages | **Partial** |
| `/report` | No separate report loading state; it is derived from current React/store state | Panel error boundary is available | Every unavailable section remains visible; no fabricated report value | **Pass for empty-state semantics; stale lineage remains open** |
| Case intake | `Creating`, `Extracting`, `Building twin`, `Simulating recovery`, and upload progress are visible; controls disable while busy | Upload alert, pipeline error, and failed stage are visible | Empty file list and blank intake are intentional entry states | **Partial — old results are retained during a new run** |
| Agent trace / evaluation / Redis rail | Standby, live, reconnecting, closed, and score standby states are visible | Trace reconnect status and panel boundary are visible | Evaluation has “No scores yet”; trace has standby | **Partial; browser delivery unverified** |

## Verified strengths

### Routes and navigation

- `web/app/[mode]/page.tsx` accepts only the five `BeatITMode` values and calls
  `notFound()` for unknown modes.
- `web/lib/product/navigation.ts` maps unknown paths to the safe `/twin`
  fallback and writes only mode paths to browser history; case IDs and payloads
  are not encoded in the URL.
- Product navigation tests passed: 3/3.

### Loading and failure surfacing

- `CaseIntakePanel` disables run/upload controls while the pipeline or upload is
  active and exposes stage-level progress instead of a silent spinner.
- `PlausibleTwinsPanel` exposes `aria-busy`, “Generating…”, and an assertive
  alert for generation failures.
- `useDualBeatStore.runPipeline` preserves typed API details through
  `ApiRequestError`, sets `status: "error"`, and exposes the error in the
  header/intake UI. The API client documents and implements no silent mock
  fallback.
- `ErrorBoundary` contains panel render failures and gives the user a Retry
  action. This is an honest containment fallback, not a fabricated result.
- `AgentTraceTimeline` distinguishes Live, Reconnecting, Closed, and Standby;
  `EvalScorecard` distinguishes Passed, Review, and No scores yet.

### Empty and missing-data behavior

- `buildProductReport` retains sections with `status: "unavailable"` and
  explicit text such as “No paired comparison is selected”; it does not replace
  missing evidence with inferred values.
- Compare requires a valid paired result and sends the user back to Experiment
  when the prerequisite is absent.
- The timeline has a composed “No longitudinal snapshots are available” state.
- Comparison metric helpers preserve missing/non-finite values as unavailable;
  the focused comparison tests cover partial and unavailable values rather than
  turning them into zero.

### Safe labels and boundaries

- `SourceStatusBadge` exposes `OBSERVED`, `DERIVED`, `SIMULATED`, `PRIOR`, and
  `SYNTHETIC` labels with accessible names.
- Experiment and Compare surfaces use `HYPOTHETICAL SIMULATION`,
  `COUNTERFACTUAL`, and educational-only language. Split Heart explicitly says
  it is not diagnosis, treatment guidance, or patient-specific mechanics.
- Plausible Twins states that uncertainty is propagated through deterministic
  physiology and is not AI confidence or clinical probability.
- The report always renders “Educational simulation only” and interpretation
  limitations.
- Timeline labels synthetic replay separately from live/latest state.

## Release-blocking findings

### A23-1 — Pipeline results are not cleared at run start (P1)

`runPipeline` clears only `error` before beginning a new request. It does not
clear `state`, `visualization`, `evaluation`, `scenarios`, `validatedFields`,
`stageResults`, or the prior `weave` value. During `creating`, `extracting`, or
`operating`, the center surface can continue rendering the previous run. If the
new run fails, the header says “Run failed” while the prior computational result
remains available in the twin/report surfaces.

Required before release: associate result data with a run/case generation and
clear or quarantine prior results before a new run becomes active. A failed run
must not leave prior output looking like the failed run's output.

### A23-2 — Scenario `result` can outlive its selected snapshot (P1)

`useScenarioController` derives a reset `current` view when
`session.snapshotId !== snapshotId`, and it correctly invalidates the ensemble
on parameter/snapshot changes. However, the returned `result` is
`history.present`, where `history` is the original session object, rather than
the snapshot-aware `current.history.present`. After selecting another snapshot,
the controls can show the new baseline while `ScenarioPanel` and
`ReportSurface` still consume the old branch.

Required before release: make every scenario result, history entry, selected
sample, and report provenance carry and validate the active snapshot ID; clear
or mark the branch unavailable immediately on snapshot change.

### A23-3 — Comparison state has no snapshot lineage guard (P1)

`PairedHeartState` contains trial/pair identifiers but no origin snapshot ID in
the frontend comparison store. `AppShell` keeps the global comparison selection
while the temporal twin can move to another snapshot. Nothing automatically
closes or marks the Split Heart pair stale. The pair can therefore remain
visible after its source timeline selection changes.

Required before release: store the origin snapshot ID with the pair and either
close, quarantine, or visibly mark the comparison stale when the active
snapshot/case changes. Report provenance must use the same guard.

### A23-4 — Labels are safe but not fully source-derived (P2)

`AppShell` assigns the Twin header `OBSERVED` by product mode, while synthetic
replay and derived projections are possible inside the selected timeline. The
timeline and heart viewport add more precise replay/synthetic labels, but the
top-level badge can still overstate the source class.

Required before release: derive the top-level badge from the selected snapshot's
quality/provenance, or explicitly label the mode as a product space and keep the
data-quality badge separate. Never let a synthetic replay inherit an observed
label by route alone.

### A23-5 — Browser-visible state transitions remain unverified (P1)

Source inspection confirms semantic `role`, `aria-live`, `aria-busy`, and
`aria-label` coverage in the reviewed components. The available environment
does not provide a runnable browser: Chromium is missing `libasound.so.2` and
Playwright Firefox is unavailable. Consequently, no release claim is made for
hydration, WebGL failure presentation, focus behavior, responsive overflow,
actual EventSource reconnects, or stale-state behavior in a browser.

Required before public demo: run the browser matrix with backend online,
backend offline, failed pipeline, empty case, snapshot change, comparison
close, reduced motion, keyboard navigation, and reload.

## Stale-state matrix

| Transition | Expected release behavior | Observed implementation | Verdict |
| --- | --- | --- | --- |
| Start a second pipeline run | Prior output is cleared or clearly marked as previous | Prior global result slices remain populated until later stages overwrite them | **Fail** |
| Pipeline fails after prior success | Failed run cannot present prior output as current | `status` becomes error but old output slices remain | **Fail** |
| Select a different temporal snapshot | Scenario branch and ensemble become unavailable or recompute | Ensemble is guarded; `result` reads old history present | **Fail** |
| Change scenario parameter | Old ensemble/pair is invalidated | `ensembleRevision` and ensemble state are invalidated | **Pass, source-level** |
| Start overlapping ensemble requests | Only latest request may commit | Revision and requested snapshot checks reject late results | **Pass, source-level** |
| Change snapshot with Split Heart open | Pair is closed or marked stale | Comparison store has no snapshot key or observer | **Fail** |
| Change case ID | Trace from prior case is not shown | `useTraceStream` clears trace for a new case and resumes only same-case IDs | **Pass, source-level** |
| Navigate to an invalid product path | No unsafe or ambiguous product surface | Route uses `notFound`; client mapping fails closed to Twin | **Pass** |

## Direct verification

| Check | Result |
| --- | --- |
| Product navigation/report contracts | **PASS — 3 passed** |
| Direct TypeScript (`web/node_modules/.bin/tsc --noEmit`) | **PASS** |
| Scoped ESLint over reviewed product/layout/scenario/comparison files | **PASS** |
| Scenario/comparison unit sweep | **PARTIAL — 81 passed, 2 failed** |
| Failed test 1 | Existing `scenario/history.test.ts` expectation mismatch in `push` history behavior |
| Failed test 2 | Existing Node strip-only loader cannot parse a TypeScript parameter property in `propagation.test.ts` |
| Browser verification | **BLOCKED** — Chromium missing `libasound.so.2`; Firefox unavailable |

The two broader-suite failures were not modified or fixed by this audit. They
must be triaged before a final frontend release claim; the focused product tests
and static checks remain green.

## Required closeout checklist

- [ ] Clear or generation-tag all pipeline result slices at run start and on
  failure.
- [ ] Make scenario `result` snapshot-aware; add a regression test for changing
  snapshots after a computed branch.
- [ ] Add origin snapshot/case lineage to comparison state and invalidate an
  open pair on selection/case changes.
- [ ] Make top-level source labels derive from selected data quality/provenance.
- [ ] Add browser tests for loading, error, empty, fallback, reload, reconnect,
  stale-result, reduced-motion, and keyboard paths.
- [ ] Resolve the two direct scenario/comparison test-run failures or document
  an approved, reproducible harness exception.
- [ ] Re-run direct typecheck, scoped lint, product tests, full runtime tests,
  production build, and the browser matrix after the fixes.

## Final disposition

**DO NOT SHIP the public frontend yet.** The product shell is structurally
credible and its missing-data/safety language is substantially in place, but
stale computational results can cross run and snapshot boundaries. That can
undermine the central credibility promise even when every individual rendered
card is correctly labeled.
