# M9 Preflight Audit — Unified Product Experience

Last audited: 2026-09-26 16:22 UTC

Branch: `claude/fervent-mccarthy-NrLAO`

Workspace: dirty; M5.5–M9 implementation and review files are uncommitted

## Decision

**CONDITIONAL GO for M9 implementation; NO-GO for M9 completion or release.**

M8 is complete only within its declared Tier-1 mathematical scope. The M5.5,
M6, and M7 numerical contracts are usable as read-only inputs to M9, and their
focused automated suites pass in the current workspace. Their milestone gates
are not all closed: browser/accessibility validation is still blocked, security
remains synthetic/demo-only, M6 retains benchmark/provenance limits, and M7
retains browser/performance, implementation, and contribution-count gates.

M9 may consolidate the existing capabilities, but it must not imply that a new
shell, route, report, or passing build closes those inherited gates. M9 itself
cannot be called a verified unified product experience until its five-space
journey is exercised in a real browser with keyboard, accessibility, responsive,
WebGL, and return-path evidence.

### Audit snapshot warning

The workspace changed while this audit ran. The initial source inventory had
only `/` and the CareGuard pages; the final snapshot also contains concurrent
M9 route, navigation, product-contract, and report work. This record describes
the **final snapshot named above**. The mere presence of those files does not
count as reviewed M9 completion evidence. In particular, every entry in
[`M9_AGENT_PLAN.md`](M9_AGENT_PLAN.md) is still marked `planned`.

## Evidence inspected

- Completion and QA records:
  [`M5_5_COMPLETION.md`](M5_5_COMPLETION.md),
  [`M5_5_BROWSER_QA.md`](M5_5_BROWSER_QA.md),
  [`M6_COMPLETION.md`](M6_COMPLETION.md),
  [`M6_QA.md`](M6_QA.md),
  [`M7_PREFLIGHT_M6.md`](M7_PREFLIGHT_M6.md),
  [`M7_COMPLETION.md`](M7_COMPLETION.md),
  [`M7_QA.md`](M7_QA.md),
  [`M8_PREFLIGHT.md`](M8_PREFLIGHT.md),
  [`M8_COMPLETION.md`](M8_COMPLETION.md), and
  [`M8_QA.md`](M8_QA.md).
- Scientific/performance boundaries:
  [`M8_MATH_AUDIT.md`](M8_MATH_AUDIT.md),
  [`M8_INFORMATION_GAIN_BOUNDARY.md`](M8_INFORMATION_GAIN_BOUNDARY.md),
  [`M6_PERFORMANCE.md`](M6_PERFORMANCE.md),
  [`M7_PERFORMANCE.md`](M7_PERFORMANCE.md), and
  [`M8_PERFORMANCE.md`](M8_PERFORMANCE.md).
- Current backend routes, stores, contracts, frontend adapters, panels,
  comparison state, App Router entries, and generated Next.js route manifest.
- Fresh commands listed under **Current validation evidence** below.

## M8 completion audit

### What is complete

[`M8_COMPLETION.md`](M8_COMPLETION.md) declares **COMPLETE — Tier-1 scope**.
The implemented authority is a deterministic, target-specific Missing Piece
analysis over persisted M5.5 projection bases, including:

- bounded local finite-difference sensitivity;
- descriptive q05/q95 parameter spread;
- an explicitly named uncertainty-impact heuristic;
- same-sample M6 Shadow Trial-effect sensitivity;
- evidence taxonomy, freshness, completeness, mapping rationale, and Evidence
  Priority Score;
- immutable local SQLite persistence;
- `POST /api/v1/missing-piece` and
  `GET /api/v1/missing-piece/{analysis_id}`;
- frontend loading, empty, error, success, safety, and unavailable states.

Fresh evidence is stronger than the counts in the completion record: the
current focused M8 suite reports **65 passed** and the current full Python suite
reports **1220 passed, 1 skipped, 6 xfailed**. These results establish the
current dirty-worktree baseline; they do not turn uncommitted work into a
release artifact.

### What is not complete or not claimed

M8 does not support Sobol, Morris, Shapley, posterior uncertainty, calibrated
probability, confidence/credible intervals, entropy reduction, expected
information gain, causal biological effects, diagnosis, treatment, or clinical
measurement recommendations. Its scalar values cannot be painted into a
pointwise PV envelope, waveform band, mesh field, or anatomical uncertainty
map. These boundaries are normative for every M9 Evidence and Report label.

M8 browser/WebGL/accessibility evidence remains open. Its performance record
contains a narrow local 50/100/250-sample probe, but no checked-in benchmark
artifact, HTTP/persistence/concurrency/memory/hosted-capacity result, or browser
frame-time result. The same record also contains a stale bullet saying no M8
benchmark was recorded despite the earlier probe table. M9 must treat this as a
documentation inconsistency and must not promote the probe into an SLO or
capacity claim.

### M9 implication

M9 may reorganize and explain M8 output, but it must consume the persisted M8
DTO and retain target, units, method/version, baseline/analysis identity,
unavailable reasons, limitations, and the canonical safety disclaimer. It must
not calculate, rename, interpolate, or spatialize M8 results in TypeScript.

## Inherited open gates

| Milestone | Audited state | Gates still open | Explicit M9 implication |
| --- | --- | --- | --- |
| M5.5 | **INCOMPLETE.** The backend ensemble path, frontend adapter, local SQLite response store, provenance, scalar uncertainty UI, and golden tests exist. Fresh M5/M5.5 runtime harness: **5 passed**. | No browser, responsive, keyboard, screen-reader, or visual sign-off. Persistence is local only. Wildcard credentialed CORS, unauthenticated routes, full-state persistence, and best-effort trace redaction are not safe for patient data. The legacy frontend ensemble runner remains executable, and uncertainty is scalar rather than anatomical or pointwise. | Use only `POST /api/v1/twin/ensemble` output and its existing adapter as numerical authority. Do not import `web/lib/twin/ensemble/runner.ts`, imply hosted/user-owned durability, accept real patient data, or fabricate spatial/PV uncertainty. |
| M6 | **INCOMPLETE — NOT READY FOR M7** in its completion record, while the later M7 preflight grants a **conditional pass on the paired-result contract**. Fresh focused suite: **40 passed, 8 warnings**. | Browser/accessibility remains unevidenced; deployment remains demo-only; the persisted-baseline/subprocess benchmark envelope is incomplete; stronger timestamp/version/hash and stage lineage remain follow-up; pointwise PV uncertainty is absent. Persisted-trial frontend rehydration is not an established journey. | M9 may consume a valid persisted same-sample pair, raw M6 deltas, IDs, and provenance. It must not resample, recompute physiology, derive MAP from display BP fields, rebuild a trial from stale browser state, or describe effect direction as benefit/harm/efficacy. Deep links need fail-closed rehydration before they can claim artifact continuity. |
| M7 | **INCOMPLETE — VALIDATION GATES OPEN.** Split Heart, comparison clocks, semantic selection, canonical delta display, PV cursor context, and provenance labels are present. Fresh comparison suite: **79 passed**. | Browser/keyboard/AT/WebGL QA and machine-specific frame/memory evidence are missing. The ledger records **10**, below the required 20. Interactive linked-camera wiring, the single-to-split transition, and per-component 3D difference emphasis remain open. | Treat Compare as conditional and valid-pair-only. M9 navigation cannot close M7's visual, performance, camera, transition, or ledger gates. Missing or stale pairs must produce an explicit prerequisite state rather than a different workflow masquerading as Compare. |

All three milestones inherit the same release rule: successful Python tests,
TypeScript, lint, build, or HTTP response checks are necessary but are not
browser/accessibility evidence.

## Current frontend route and state audit

### Built route graph

The final source snapshot and a successful Next.js production build expose:

| Route | HTTP smoke | Current behavior | M9 status/implication |
| --- | ---: | --- | --- |
| `/` | 200 | Static entry rendering `AppShell`; client state defaults to Twin, but the URL remains `/`. | Supported compatibility entry. Decide whether it remains canonical or redirects to `/twin`; test both behavior and history. |
| `/twin` | 200 | Dynamic `[mode]` route validates the mode and renders the shared shell. | Named M9 route exists. |
| `/experiment` | 200 | Renders `ScenarioPanel`. | Named route exists; artifact identity is still in memory, not in the URL. |
| `/compare` | 200 | Renders Split Heart only when an in-memory valid pair exists; otherwise renders the full Experiment/Scenario panel. | Route exists, but its missing-prerequisite state is not fail-closed or Compare-specific. |
| `/evidence` | 200 | Renders `PlausibleTwinsPanel`, which nests Missing Piece after an ensemble exists. | Route exists, but no persisted analysis ID/target is encoded or rehydrated. |
| `/report` | 200 | Builds a session summary from current in-memory booleans and available IDs. | Route exists, but it is not yet bound to an exact persisted artifact chain. |
| `/bogus` | 404 | `[mode]` rejects values outside the five-mode allowlist. | Correct fail-closed route behavior. |
| `/careguard`, `/careguard/cases`, `/careguard/runner` | 200 | Separate CareGuard product surfaces. | Keep outside the five-space M9 journey unless an explicit, typed case handoff is designed. |
| `/api/copilotkit` | GET 405 | Node App Router CopilotKit endpoint; intended method is not GET. | Keep as a server-side integration boundary; do not introduce browser-side model credentials. |

The production build reports `/` and the CareGuard pages as static, with
`/[mode]` and `/api/copilotkit` dynamic.

### Current M9 integration findings

The current concurrent implementation is a useful scaffold, not a closed M9
journey:

1. The primary navigation lists exactly `TWIN`, `EXPERIMENT`, `COMPARE`,
   `EVIDENCE`, and `REPORT` in the required order.
2. Navigation uses `window.history.pushState` plus a synthetic `popstate`
   event. Back/Forward state has source support, but has not been browser-tested
   and does not use Next's router/prefetch semantics.
3. URLs carry only the mode. They do not carry snapshot, ensemble, trial, pair,
   Missing Piece analysis, target metric, component, or drawer identity.
4. The shared `BeatITSessionContext` currently sets `snapshotId`, `componentId`,
   `ensembleId`, and `targetMetric` to `null`; trial and pair IDs exist only
   when the in-memory comparison store is populated.
5. Scenario and ensemble state live in a mounted React provider, while the
   comparison store is an in-memory Zustand store without persistence. A direct
   route load or reload therefore cannot establish the artifact identity needed
   by Compare, Evidence, or Report.
6. `/compare` falls back to the Experiment workspace instead of explaining
   that a valid pair is missing and linking to its owner. This can obscure the
   active route and violates the fail-closed empty-state requirement.
7. `/report` infers readiness from session booleans and gives every section the
   same small provenance list. It does not include a persisted Missing Piece
   analysis ID, target, exact scenario/trial digest, per-section provenance, or
   stale/mismatch validation.
8. There is no explicit `Return to Twin` action in each secondary surface.
   Closing Split Heart clears the in-memory comparison while remaining on the
   Compare route, which then displays Experiment.
9. The new modal product drawer supports Escape and outside-click, but source
   inspection shows no focus capture, initial focus, focus trap, background
   inertness, or focus restoration. It therefore inherits rather than resolves
   the browser/accessibility gate.
10. M9 tests and planned source-status work are not yet present in the final
    snapshot: `sourceStatus.ts`, navigation tests, and report-contract tests are
    absent even though route/contracts/report files exist.

The route scaffold can remain, but M9 completion requires a typed artifact
identity/rehydration contract, honest prerequisite states, explicit return
behavior, and tests before visual polishing is treated as integration.

## Browser blocker — reproduced

The blocker remains environmental and reproducible in the current workspace:

```text
$ playwright --version
Version 1.63.0

$ ldd ~/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome | rg 'not found|libasound'
libasound.so.2 => not found

$ playwright screenshot --browser=chromium ... http://127.0.0.1:3100/twin ...
error while loading shared libraries: libasound.so.2: cannot open shared object file
exit 1 before navigation

$ playwright screenshot --browser=firefox ... about:blank ...
Executable doesn't exist at ~/.cache/ms-playwright/firefox-1543/firefox/firefox
exit 1
```

The required Chromium and Firefox runs therefore produced no DOM rendering,
screenshot, accessibility tree, keyboard traversal, responsive layout, WebGL
console, frame-time, memory, or screen-reader evidence. The successful HTTP
responses below establish routing only.

There is a second tooling blocker: normal pnpm frontend commands stop at
`ERR_PNPM_IGNORED_BUILDS` for `@scarf/scarf`, `es5-ext`, `sharp`, and
`unrs-resolver`. Installed binaries can currently be invoked directly, but M9
cannot call the documented package scripts reproducibly until the repository's
build-script policy is resolved or the documented commands are changed.

## Current validation evidence

Commands were run from `/home/923873155/BeatIT` unless noted:

```text
pnpm test:py
  PASS — 1220 passed, 1 skipped, 6 xfailed, 494 warnings

python -m pytest -q python/hearttwin/tests/test_shadow_trial_*.py
  PASS — 40 passed, 8 warnings

python -m pytest -q python/hearttwin/tests/test_missing_piece_*.py
  PASS — 65 passed

cd web && node --experimental-strip-types --loader ./tests/alias-loader.mjs \
  --test ./lib/twin/comparison/__tests__/*.test.ts
  PASS — 79 passed

cd web && node --experimental-strip-types --loader ./tests/alias-loader.mjs \
  --test ./tests/m5-runtime.test.ts \
  ./lib/twin/ensemble/__tests__/inspectorModel.test.ts
  PASS — 5 passed

cd web && ./node_modules/.bin/tsc --noEmit
  PASS

cd web && ./node_modules/.bin/eslint <M5.5/M6/M7/M8 frontend scope>
  PASS

cd web && ./node_modules/.bin/next build
  PASS — compiled, typechecked, generated 7/7 static pages; route graph above

GET /, /twin, /experiment, /compare, /evidence, /report,
    /careguard, /careguard/cases, /careguard/runner
  PASS — HTTP 200
GET /bogus
  PASS — HTTP 404

cd web && pnpm exec tsc --noEmit
cd web && pnpm test:runtime
  BLOCKED BEFORE EXECUTION — ERR_PNPM_IGNORED_BUILDS

Playwright Chromium and Firefox commands
  BLOCKED BEFORE PAGE NAVIGATION — failures reproduced above
```

These checks are a dirty-worktree snapshot, not commit or deployment proof.

## Mandatory M9 implications and exit gate

M9 implementation must:

1. Treat M5.5 ensemble results, M6 Shadow Trial pairs, and M8 Missing Piece
   analyses as read-only numerical authorities.
2. Keep observed/derived/interpolated/synthetic classification, hypothetical
   labels, units, unavailable reasons, scalar/PV limitations, lineage, and the
   canonical safety disclaimer visible through every transformation.
3. Add one typed source of truth for route mode plus artifact identity; validate
   all rehydrated IDs and fail closed on missing, stale, mismatched, or
   unauthorized artifacts.
4. Make Compare, Evidence, and Report show space-specific prerequisite/error
   states rather than silently mounting another space's full workflow.
5. Bind Report to the exact case/snapshot/scenario/ensemble/trial/pair/analysis/
   target chain and preserve section-specific provenance and limitations.
6. Provide an explicit, non-destructive Return-to-Twin path that restores the
   same case and origin snapshot while retaining valid downstream artifacts.
7. Add focused navigation, direct-load/history, artifact mismatch, report,
   source-status, loading/error/empty, and stale-state tests.
8. Resolve or explicitly accept the pnpm build-script policy before claiming
   the documented frontend commands are reproducible.
9. Close the real-browser gate with narrow and wide viewport checks, keyboard
   and focus behavior, accessibility-tree/AT evidence, reduced motion, WebGL
   console/resource cleanup, and split-heart frame/memory measurements.
10. Reconcile stale status documentation: `MILESTONES.md` says only M1 is
    implemented, M8 completion says M9 was not started, and the M9 ledger still
    says every task is planned despite current M9 files.

**Stop condition:** if browser dependencies remain unavailable, or the exact
artifact journey cannot survive navigation/reload without silent rebinding,
M9 must remain **INCOMPLETE — VALIDATION BLOCKED**. Contracts, source audits,
unit tests, typechecks, builds, and HTTP smoke checks may continue, but none is
a substitute for the product-level acceptance journey.

## Scope of this audit

This task changed only `docs/hackathon/M9_PREFLIGHT.md`. It did not modify
physics, backend/frontend implementation, tests, configuration, package policy,
milestone status, or the M9 agent ledger.
