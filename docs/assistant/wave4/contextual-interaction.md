# Wave 4 — Contextual interaction plumbing (context events + suggested actions)

> Scope: `web/lib/assistant/contextEvents.ts`, `web/lib/assistant/suggestedActions.ts`,
> `web/components/assistant/SuggestedActionChips.tsx`. New files only, per the
> concurrency constraint below — read `docs/assistant/GLOBAL_ARCHITECTURE.md`'s
> "CONTEXT ARCHITECTURE" section and `docs/assistant/wave3/context-and-orchestration.md`
> first; this note only explains the decisions inside their constraints.

## Why this agent exists

Wave 3 built the backend half of context resolution —
`apply_context_event(context, event_type, value)` in
`python/hearttwin/assistant/context_resolver.py` — but explicitly built no frontend
call site for it ("No frontend code was written this wave," per that wave's own
handoff note). GLOBAL_ARCHITECTURE.md's context-source examples ("click LV ->
component_id=LV; scrub timeline -> snapshot_id updates; open paired Twin #284 ->
pair_id=284") and its "2-4 contextual suggestions" requirement both still had no
frontend implementation at all. This wave builds that frontend plumbing — the event
bus, the accumulated-context hook, and the pure suggested-actions mapping — as
standalone, importable pieces.

**Not wired into any real click handler this wave**, deliberately: Codex was
confirmed (via `git status`) to be concurrently, continuously editing
`web/components/heart/HeartScene.tsx`, `web/components/twin/scenario/ScenarioPanel.tsx`,
`web/lib/api.ts`, `web/package.json`, and `web/components/layout/AppShell.tsx` while
this task ran, plus building new `web/components/twin/comparison/` and
`web/components/twin/shadow-trial/` directories. Editing any of those files this wave
would race a live concurrent editor. Everything below is read-only reconnaissance of
the *current* state of those files, cited by file:line, for a future wave to act on —
not a promise that the lines will be unchanged by the time that wave starts (re-read
first).

## Files built

- `web/lib/assistant/contextEvents.ts` — `emitContextEvent(event_type, value)`,
  `useContextEvent(callback)`, `useCurrentAssistantContext()`. See its module
  docstring for the Zustand-based design rationale (reuses the store primitive
  already established by `web/lib/store.ts` and `web/lib/twin/comparison/store.ts`,
  rather than a hand-rolled listener array, because `getState()/setState()` work
  outside a React tree — matching "framework-agnostic" — while the two `use*` hooks
  stay thin wrappers, the same split every other store here already uses).
- `web/lib/assistant/suggestedActions.ts` — pure `getSuggestedActions(context)`.
- `web/components/assistant/SuggestedActionChips.tsx` — presentational chip list,
  `onSelect(action: string)` callback, no store subscription of its own.
- `web/lib/assistant/__tests__/suggestedActions.test.ts` — 5 cases for the pure
  logic, using this repo's existing `node:test` convention (see "Tests" below).

### Type reconciliation with Agent 16

Agent 16's `web/types/assistant.ts` and `web/lib/assistantApi.ts` did **not** exist
yet when this task started (`test -f` returned missing for both). A local minimal
type was defined first, matching the plan's fallback instruction. Partway through
this task, `web/types/assistant.ts` landed (its `ConversationContext` interface,
lines 40-53, matches exactly what this note predicted: `component_id`,
`snapshot_id`, `pair_id`, `scenario_id`, `target_metric`, all `string | null`,
optional). `contextEvents.ts` was updated before finishing this task to derive its
`AssistantContext` type as
`Pick<ConversationContext, "component_id" | "snapshot_id" | "pair_id" | "scenario_id" | "target_metric">`
imported from `@/types/assistant`, rather than keep a second hand-written copy of
those five fields. It intentionally does **not** use the full `ConversationContext`
(which also requires `conversation_id` and `audience`) — this event store only ever
accumulates from UI events and never learns those two fields; they belong to the
conversation session, not a click/scrub/pair-open event.

## Real call sites for a future wave to wire up

All verified by reading the current file contents during this task (2026-09-26).
Re-read each file before editing — Codex was actively changing several of them.

### 1. Component selection (`component_selected`)

- **`web/components/heart/HeartScene.tsx:1112`** — the primary (non-comparison)
  `HeartScene()` component's click handler:
  ```
  onSelect={(id) => { setShowReport(false); interaction.select(id); }}
  ```
  inside the `<HeartCanvasClient>` render. Add
  `emitContextEvent("component_selected", id)` alongside `interaction.select(id)`.
- **`web/components/heart/HeartScene.tsx:1002`** — the same interaction inside
  `HeartTwinInstance` (used by the M7 split-heart comparison view):
  ```
  onSelect={(id) => {
    setShowReport(false);
    interaction.select(id);
    onComponentSelect?.(id);
  }}
  ```
  Same fix, same file. Both call sites share one `useHeartInteraction()` hook
  (`web/components/heart/interaction/useHeartInteraction.ts:9`) but are two
  separate component instances, so both need the `emitContextEvent` call added
  independently.

### 2. Timeline scrub / snapshot selection (`snapshot_selected`)

- **`web/components/twin/timeline/Timeline.tsx:151-156`** — `seekToValue`, called
  from the range-slider `onChange` at line 228, computes `nextSnapshot` and calls
  `onSeek(nextTimestamp, nextSnapshot?.id ?? null)`.
- **`web/components/twin/timeline/Timeline.tsx:213`** — a second path, clicking a
  specific snapshot marker directly: `onSelect={() => onSeek(snapshot.timestamp, snapshot.id)}`.
- Both funnel into the one real call site to edit —
  **`web/components/heart/HeartScene.tsx:1212`**:
  ```
  onSeek={(timestamp, snapshotId) => controller.seek(timestamp, snapshotId)}
  ```
  Add `if (snapshotId) emitContextEvent("snapshot_selected", snapshotId)` here
  (guard the null case — `seekToValue` passes `null` when the cursor lands between
  snapshots with no exact match). This is the single spot where both scrub paths
  converge, so it is the only line that needs the new call.

### 3. Pair opening (`pair_opened`)

- **`web/lib/twin/comparison/store.ts:38`** — the `open` action on
  `useComparisonStore` (a second Zustand store, sibling to the one this task adds):
  ```
  open: (trial, pairId, reference) => { const paired = buildPair(trial, pairId, reference); if (paired) set({ trial, paired, view: initialView(paired.pairId) }); },
  ```
  Add `emitContextEvent("pair_opened", pairId)` inside the `if (paired)` branch,
  after confirming the pair actually resolved (mirrors this file's own pattern of
  only committing state once `buildPair` succeeds).
- Triggered today from **`web/components/twin/shadow-trial/ShadowTrialPanel.tsx:146`**:
  ```
  <PairInspector trial={trial} onCompare={(sampleId) => { if (referenceVisualization) openComparison(trial, sampleId, referenceVisualization); }} />
  ```
  where `openComparison` is `useComparisonStore((state) => state.open)`
  (`ShadowTrialPanel.tsx:85`).
- Secondary call site worth including in the same edit:
  **`web/lib/twin/comparison/store.ts:39`**, the `selectPair` action — fired when
  the user switches which pair they're viewing *within* an already-open
  comparison. Whether that should also emit `pair_opened` (same event type, new
  `pairId` value) or be left alone is a product call for whoever wires this up;
  flagging it here since it is the same file and the same event type would apply.

### 4. Scenario creation (`scenario_created`)

- **`web/lib/twin/scenario/useScenario.tsx:73-80`** — the `experiment` callback:
  ```
  const experiment = useCallback(() => {
    if (!parameters) return null;
    const result = compute(parameters);
    if (result) {
      ensembleRevision.current += 1;
      setSession((previous) => ({ snapshotId, parameters, history: pushScenario(previous.snapshotId === snapshotId ? previous.history : createScenarioHistory(), result) }));
      setEnsembleSession({ snapshotId, ensemble: null, selectedSampleId: null });
    }
    return result;
  }, [compute, parameters, snapshotId]);
  ```
  Add `emitContextEvent("scenario_created", result.definition.id)` inside the
  `if (result)` branch. `result.definition.id` is the scenario id string (see
  `ScenarioDefinition.id`, `web/lib/twin/scenario/types.ts:46`; default value
  `` `scenario-${snapshot.id}` `` is set at
  `web/lib/twin/scenario/propagation.ts:239`).
- Note `changeParameter` (`useScenario.tsx:84` onward) also produces a new
  `ScenarioResult` on every parameter tweak, reusing the same scenario id — that's
  a scenario being *edited*, not created, so it should not re-fire this event;
  only `experiment()`'s first successful compute for a given interaction is the
  "created" moment per the spec's naming.

### 5. Target metric change (`target_metric_changed`) — no UI control exists yet

Searched all of `web/components/` and `web/lib/twin/` for any consumer of
`TargetMetric`/`target_metric` outside of type/schema definitions
(`web/types/heart.ts:98,114`, `web/lib/schemas.ts:25,127`, both inside
`RecoveryConfig`). **No component currently sets this field** — there is no
target-metric picker in the frontend today, only the type describing what
`/simulate-recovery` accepts. This is a genuine gap, not an oversight in this
search: whoever adds that control (plausibly inside
`web/components/twin/scenario/ScenarioPanel.tsx`, which Codex was actively editing
during this task and is the natural home for a recovery/target-metric selector)
should call `emitContextEvent("target_metric_changed", metric)` from that new
control's `onChange`. Re-check `ScenarioPanel.tsx` for what Codex landed before
assuming this is still true.

### Suggested-actions consumption site (not a context-emission site)

`web/components/copilot/CopilotDock.tsx` already renders a **static** suggestions
list unrelated to this task: `const SUGGESTIONS = [...]` at line 285, passed to
CopilotKit's own `<CopilotChat suggestions={SUGGESTIONS} .../>` at line 602. A
future wave integrating `SuggestedActionChips`/`getSuggestedActions` should decide
whether to replace or augment that static list with
`getSuggestedActions(useCurrentAssistantContext())` — out of scope here since
`CopilotDock.tsx` is on this task's do-not-touch list.

## What's deliberately NOT built (future work)

- No real click/scrub/pair-open handler calls `emitContextEvent` yet — see above.
- No POST to a backend `apply_context_event` endpoint — none exists yet per
  `docs/assistant/wave3/context-and-orchestration.md`; `contextEvents.ts`'s
  `emit` only updates local frontend state this wave. A future wave adding that
  endpoint should call it from inside `emit` (see the docstring on
  `emitContextEvent`).
- No target-metric UI control exists to wire up (see §5 above).
- `SuggestedActionChips`'s `onSelect` is not wired to any chat panel — Agent 16's
  conversation component (using its now-landed `web/lib/assistantApi.ts` /
  `web/types/assistant.ts`) is the natural integration point once it exists.

## Tests

`web/lib/assistant/__tests__/suggestedActions.test.ts`, 5 cases, using this
repo's existing convention: Node's built-in `node:test` + `node:assert/strict`,
runnable via the same invocation as the pre-existing `test:runtime` script:

```
node --experimental-strip-types --loader ./tests/alias-loader.mjs --test ./lib/assistant/__tests__/suggestedActions.test.ts
```

All 5 pass. This file was **not** added to `web/package.json`'s `test:runtime`
script (which hardcodes an explicit file list) because `package.json` was on the
concurrent-edit list for this task — a future wave should add
`./lib/assistant/__tests__/suggestedActions.test.ts` to that script's file list
once it's safe to touch `package.json` again.

`npx tsc --noEmit` was also run against the full `web/` project; the three new
files (`contextEvents.ts`, `suggestedActions.ts`, `SuggestedActionChips.tsx`)
produce no type errors. (An unrelated pre-existing error in a different
concurrently-added file, `web/components/assistant/VisuallyHidden.tsx`, was
observed and is not this task's file.)

## Global Architecture Compliance: YES

No second context object, tool registry, router, or safety layer was created.
`AssistantContext` is a `Pick` of Agent 16's real `ConversationContext` — not a
competing shape — and the five event types match
`python/hearttwin/assistant/context_resolver.py`'s `ContextEventType` exactly. No
frontend-side entity extraction from free text was added (matching Wave 3's own
explicit boundary: context updates come only from explicit UI events, never
guessed out of chat prose).
