# M4 integrated architecture review

**Review date:** 2026-09-26  
**Scope:** Read-only review of the integrated M4 scenario, causal graph, UI,
visualization, persistence, and test seams. No source files were modified for
this review.

## Executive disposition

The M4 core has a reasonable boundary: a selected observed `TwinSnapshot` is
copied into a hypothetical result, numeric propagation is deterministic, and
the UI labels the result as hypothetical. M4 is **not acceptance-ready**,
however. The frontend typecheck is blocked by an M4 syntax error, and the
scenario result does not yet drive the existing heart/PV visualization path.

## Findings and dispositions

### M4-1 — Frontend compilation is blocked by the scenario provider file

- **Severity:** Blocker
- **Evidence:** `web/lib/twin/scenario/useScenario.ts:100-110` declares the
  file as `.ts` but returns JSX from `ScenarioProvider` at line 105.
- **Observed result:** The direct check
  `./node_modules/.bin/tsc -p tsconfig.json --noEmit --incremental false`
  from `web/` fails with `TS1005`, `TS1109`, and `TS1161` at that JSX. Focused
  ESLint likewise reports a parsing error for the same file.
- **Impact:** The M4 provider cannot pass the frontend compiler gate, so a
  production build or browser acceptance run cannot be treated as evidence.
- **Disposition:** **Fix before M4 acceptance.** Rename the module to a JSX
  extension or return the provider without JSX, then rerun typecheck, lint,
  build, and the browser smoke path. Keep the provider boundary around the
  panel as currently wired in `web/components/layout/AppShell.tsx:30-32,124-183`.

### M4-2 — Scenario projections are implemented but disconnected from the visible twin

- **Severity:** High
- **Evidence:** `web/lib/twin/scenario/visualization.ts:10-53` composes
  `scenarioPvLoop` and `scenarioHeartBinding`, but the module has no consumer.
  The same is true of the exported helpers in
  `web/lib/twin/scenario/pv.ts:23-35` and
  `web/lib/twin/scenario/heart.ts:8-27`.
  `web/components/heart/HeartScene.tsx:947-1015` renders only
  `temporal.selectedSnapshot` / `temporal.selectedVisualization` or the
  store visualization; it does not read `ScenarioProvider` state or call
  `scenarioVisualization`.
- **Impact:** Changing a causal control updates the scenario inspector and
  graph, but does not update the beating 3D heart, PV loop, or simulation
  charts. This contradicts the intended M4 architecture of an experiment
  affecting the existing visual surfaces and makes the projection modules dead
  integration seams.
- **Disposition:** **Fix before demo/completion.** Define one projection seam
  from the scenario controller into the twin context or the existing visual
  consumers, preserve the observed baseline, and render an explicit
  hypothetical label. Add an integration test that a changed heart rate or
  EF reaches both the heart inputs and the PV/chart data.

### M4-3 — Public propagation does not enforce the documented parameter contract

- **Severity:** High
- **Evidence:** The documented/UI ranges are defined in
  `web/lib/twin/scenario/parameters.ts:31-74` and described in
  `docs/hackathon/M4_PARAMETER_RANGES.md`. The core `evaluate` function instead
  clamps heart rate to `30-220` and preload/contractility to `0-2` at
  `web/lib/twin/scenario/propagation.ts:125-147`. The public
  `propagateScenario` path maps inputs directly at `:222-244` and never calls
  `validateScenarioParameter`.
- **Impact:** Direct callers can supply out-of-range, duplicate, or otherwise
  malformed inputs and receive a `complete` result with silently coerced
  values. The recorded input value can differ from the computed scenario value,
  while the documented policy says invalid values are rejected rather than
  coerced. The UI guard in `useScenario.ts:63-78` does not protect other
  callers or persisted/replayed inputs.
- **Disposition:** **Fix before M4 acceptance.** Make one shared validator the
  boundary for `propagateScenario`; reject invalid inputs or return an explicit
  `blocked` result, and use the same bounds in evaluation and UI. Add tests for
  every lower/upper boundary, NaN/infinity, unknown keys, and out-of-range
  inputs.

### M4-4 — The causal graph presentation is not the causal graph it claims to show

- **Severity:** Medium
- **Evidence:** `web/components/twin/scenario/CausalGraph.tsx:14-25` renders
  every node in the array order with an arrow between adjacent nodes. The
  actual graph is defined by `M4_CAUSAL_GRAPH.edges` in
  `web/lib/twin/scenario/propagation.ts:60-90`; it contains branches such as
  preload → EDV and SVR → MAP, not a single chain of heart rate → preload →
  afterload → contractility → SVR → EDV → ... .
- **Impact:** The on-screen explanation visually asserts edges that do not
  exist and hides the branch structure that makes the deterministic result
  auditable. This is especially misleading for the SVR-to-MAP path.
- **Disposition:** **Fix before demo/completion.** Render actual graph edges or
  the returned `propagation.paths`, with signed direction and changed-node
  state. Keep node labels sourced from the graph definition rather than using
  array position as topology.

### M4-5 — Immutability, persistence, and history contracts are only partially enforced

- **Severity:** Medium
- **Evidence:** `forkSnapshot` deep-freezes its result at
  `web/lib/twin/scenario/fork.ts:48-75`, but `propagateScenario` creates a
  separate cloned origin without runtime freezing at
  `web/lib/twin/scenario/propagation.ts:181-189,248-255`. The readonly
  TypeScript types therefore do not provide runtime immutability.
  Persistence validation in `web/lib/twin/scenario/persistence.ts:130-227`
  checks that `state` is merely an object; it does not validate the cardiac
  state shape, causal payload, parameter keys/bounds, or delta consistency.
  Finally, `useScenario.ts:93-94` changes the history result on undo/redo but
  leaves the slider `parameters` at the newer values, so controls can disagree
  with the displayed result.
- **Impact:** A consumer can mutate a scenario object despite the documented
  immutable boundary; malformed persisted data can be accepted as a typed
  result; and undo/redo can present one scenario while the controls describe
  another. The persistence and projection paths also have no active consumer
  coverage in the current M4 tests.
- **Disposition:** **Harden before enabling persistence or calling M4 complete.**
  Use one immutable fork/result constructor, validate persisted data against
  the actual domain contract, and store or derive parameter values together
  with the history present value. If persistence is not required for the demo,
  explicitly defer it rather than treating the current validator as a complete
  storage boundary.

## Positive architectural evidence

- `propagateScenario` deep-copies the selected state before writing derived
  measurements (`web/lib/twin/scenario/propagation.ts:155-178`), and the
  origin retains snapshot identity, timestamp, provenance, and evidence IDs
  (`:181-189`).
- The result carries explicit causal deltas, paths, source metadata, warnings,
  and `deterministic: true` (`web/lib/twin/scenario/propagation.ts:257-287`),
  rather than asking an LLM to calculate physiology.
- The UI consistently labels the surface as `HYPOTHETICAL SIMULATION` and
  provides a non-clinical safety boundary in
  `web/components/twin/scenario/ScenarioPanel.tsx:20-23` and
  `web/components/twin/scenario/ScenarioInspector.tsx:114-131`.

## Validation record

- Targeted backend regression: **74 passed, 25 deprecation warnings** for
  `test_cardiac_formulas.py` and `test_pipeline_integration.py`.
- Frontend direct TypeScript check: **failed** on M4 JSX syntax in
  `useScenario.ts:105`.
- Focused frontend ESLint: **failed** with the same M4 parse error. A full
  lint also reports unrelated pre-existing errors outside the M4 scenario
  files; it was not used as an M4 pass signal.
- No production build or browser demo was accepted because the frontend
  compiler gate is currently blocked.
- The workspace root has no `.git` metadata, so this review records filesystem
  evidence and does not make commit/diff-history claims.

## Overall recommendation

Treat M4 as **implemented foundation / incomplete integration**. Resolve
M4-1 through M4-3 before a demo claim. Resolve M4-4 and M4-5 before calling the
causal explanation and persistence contracts production-quality; otherwise
mark those capabilities explicitly deferred in the M4 completion record.
