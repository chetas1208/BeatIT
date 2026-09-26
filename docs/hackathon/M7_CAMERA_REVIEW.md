# M7 Camera Behavior Review

Date: 2026-09-26

Agent: M7 Agent 08

Scope: current `HeartScene` focus/camera implementation and the M7 split-heart
comparison behavior. Documentation-only review; no code was changed.

## Verdict

**CONDITIONAL — linked semantic focus is present, but linked camera pose is not
integrated.**

The two M7 panes are independently mounted `HeartTwinInstance` renderers. Each
renderer owns a separate `useHeartInteraction` controller, `Canvas`, and `Rig`
camera loop. The current comparison UI can send the same semantic component ID
to both panes when **Linked selection** is enabled, so both local cameras move
toward their corresponding focus target. This is linked selection/focus
behavior, not shared camera state.

A pure comparison-camera module exists and has tests for linked and independent
pose/focus semantics. However, the active `SplitHeartComparison` surface does
not create or update that camera state, does not render a camera-mode control,
and does not pass camera poses into `HeartTwinInstance` or `Rig`. Therefore the
product must not currently claim that users can orbit one pane and have the
other pane follow, or that **Linked camera** / **Independent camera** is an
implemented UI mode.

## What the current HeartScene actually does

### Single-heart focus path

The existing `Rig` in `HeartScene.tsx` owns the render-loop camera behavior:

- It reads the active R3F camera and stores the current pose in refs
  (`web/components/heart/HeartScene.tsx:649-655`).
- On mount or camera replacement it sets the default position and look-at
  target to `[0.4, 0.25, 4.1]` and `[0, -0.05, 0]`
  (`web/components/heart/HeartScene.tsx:656-660`).
- When a semantic `focusedId` exists, it resolves a target through
  `focusTargetForComponent`, interpolates toward the target, and returns before
  pointer parallax is applied (`web/components/heart/HeartScene.tsx:662-671`).
- When there is no focus, it eases a small pointer parallax and returns toward
  the default look-at target (`web/components/heart/HeartScene.tsx:672-690`).
- Focus targets are stable semantic IDs with four explicit close-up targets and
  a generic fallback; they are not derived from patient values
  (`web/components/heart/camera/primitives.ts:15-19,95-103`).

The regular `HeartScene` uses one `HeartCanvasClient` and one local interaction
controller (`web/components/heart/HeartScene.tsx:1030-1057,1106-1117`). Its
selection/focus behavior therefore remains a single-camera interaction.

### M7 pane ownership

`HeartTwinInstance` is a controlled state renderer, but its camera and
interaction ownership remain local:

- Each instance calls `useHeartInteraction()` independently
  (`web/components/heart/HeartScene.tsx:967-986`).
- Each instance mounts its own `HeartCanvasClient` and passes its own
  `selectedId`, `hoveredId`, and `focusedId` into that canvas
  (`web/components/heart/HeartScene.tsx:993-1014`).
- Each canvas creates its own `Canvas` camera and its own `Rig`; the camera is
  not received as a prop (`web/components/heart/HeartScene.tsx:843-925`).

This is a sound isolation boundary: baseline and counterfactual state objects
are explicit inputs, while camera refs, focus transitions, and pointer input do
not leak between panes. It also means that equal initial framing is not proof of
camera linkage; it is simply the shared default pose.

## What M7 comparison currently links

`SplitHeartComparison` keeps the two semantic selection IDs in local state. With
**Linked selection** enabled, a click on either pane writes the same registered
component ID to both selections; with it disabled, only the clicked side is
updated (`web/components/twin/comparison/SplitHeartComparison.tsx:46-75`). The
same selected ID is then passed to both `HeartTwinInstance` components
(`web/components/twin/comparison/SplitHeartComparison.tsx:81`). Because each
instance's local interaction controller focuses its received ID, this produces
corresponding focus targets in both panes.

The semantic selection helpers independently specify this mapping by stable
registry IDs, not mesh names (`web/lib/twin/comparison/selection.ts:42-90`).
Their tests cover linked selection and unlinked selection behavior
(`web/lib/twin/comparison/__tests__/selection.test.ts:26-73`).

This claim is therefore accurate:

> **Linked selection causes corresponding semantic focus in both rendered
> hearts.**

This stronger claim is not accurate for the current UI:

> **The two camera poses are linked and user camera manipulation mirrors across
> panes.**

There is no `OrbitControls` or equivalent user orbit path in the reviewed
`HeartScene`; camera changes are the default framing, pointer parallax, and
semantic focus interpolation. The linked-selection button is not a linked-camera
button.

The comparison clock is a separate concern. `SplitHeartComparison` advances one
comparison clock and passes `baselinePhase` and `scenarioPhase` to the two
renderers (`web/components/twin/comparison/SplitHeartComparison.tsx:49-65,81`).
Phase-locked or physiologic-rate playback synchronizes or intentionally
separates animation phase; it does not synchronize camera pose.

## Comparison-camera module: contract versus integration

`web/lib/twin/comparison/camera.ts` defines a useful renderer-neutral contract:

- `createComparisonCameraState` creates two panes with the same canonical
  starting pose (`:138-149`).
- Linked pose updates copy the pose to both panes; independent updates modify
  only the requested pane (`:180-200`).
- Linked focus applies the semantic target to both panes; independent focus
  applies it only to the requested pane (`:203-241`).
- Clearing and reset preserve the intended mode and return defensive copies
  (`:244-278`).

The focused tests support those pure-state claims, including mirrored linked
poses, isolated independent poses, linked semantic focus, reset, immutability,
and validation (`web/lib/twin/comparison/__tests__/camera.test.ts:19-97`). They
are evidence for the module contract only. A passing pure-function test cannot
establish that the active React renderers consume the module.

The integration gap is visible in the current call graph:

- `SplitHeartComparison` imports the comparison clock, differences, and
  visualization helpers, but not the comparison-camera module
  (`web/components/twin/comparison/SplitHeartComparison.tsx:3-11`).
- Its controls expose linked selection and difference-only presentation, not
  linked/independent camera mode (`web/components/twin/comparison/SplitHeartComparison.tsx:82`).
- `ComparisonViewState` and the Zustand comparison store contain a
  `linkedCamera` field and setter (`web/lib/twin/comparison/contracts.ts:67-76`;
  `web/lib/twin/comparison/store.ts:9-26,34-47`), but the rendered split
  component uses local selection state and does not consume that camera state.
- `difference-mode.ts` explicitly preserves the supplied orientation and says
  that difference presentation does not apply a camera transform
  (`web/lib/twin/comparison/difference-mode.ts:1-7,31-40,112-117`).

Accordingly, the implementation status is:

| Claim | Status | Honest wording |
| --- | --- | --- |
| Two panes have isolated renderer-local camera owners | **Supported** | Each `HeartTwinInstance` owns a separate canvas, interaction controller, and `Rig`. |
| Linked selection focuses corresponding anatomy | **Supported** | The same semantic selection ID is passed to both panes, and both local rigs focus it. |
| Independent selection keeps focus local | **Supported** | Unlinked selection updates one side; the other side retains its own selection/camera focus. |
| Linked camera pose/orbit mirroring | **Specified/tested in pure module only** | The contract exists, but the active split renderer does not wire it. |
| Independent camera pose/orbit control | **Not user-visible** | Local camera ownership exists, but no independent orbit control is exposed. |
| `linkedCamera` store flag drives rendering | **Not supported by current call path** | The field/setter exist, but the split surface does not consume them. |

## Safety and integration constraints

Any later camera integration should preserve these boundaries:

1. Keep camera targets keyed by stable semantic component IDs. Never couple a
   comparison camera to raw mesh names or to a backend measurement.
2. Keep baseline and counterfactual render inputs explicit. Camera linkage must
   not merge or mutate their cardiac state objects.
3. In linked mode, mirror only an explicit camera command or canonical pose;
   linked semantic focus may update both panes without implying shared mutable
   renderer state.
4. In independent mode, a focus, clear, reset, or future orbit action on one
   pane must not overwrite the other pane's pose or focused component.
5. Do not let a future shared camera state fight the current local `Rig` refs.
   The renderer needs one authoritative camera-write path per pane.
6. Preserve the M7 comparison labels and non-clinical boundary. Camera framing
   is a visual presentation aid, not evidence of anatomical measurement,
   mechanics, diagnosis, treatment, or clinical prediction.
7. Validate the actual browser interaction before upgrading these claims. The
   repository's current pure tests establish state semantics, not pointer,
   keyboard, WebGL, responsive-layout, or screenshot behavior.

## Review conclusion

M7 currently has a defensible split-heart isolation story and a defensible
linked-selection story. It does **not** yet have an honest basis for claiming
linked camera manipulation. The comparison-camera module is a good contract and
test seam for future integration, but until `SplitHeartComparison` and the two
`HeartTwinInstance` renderers consume it, documentation and demo language should
say **linked selection / corresponding focus** and **independent local camera
owners**, not **linked cameras**.

Validation for this documentation review was source inspection of the cited
HeartScene, camera primitives, split comparison, selection helpers, comparison
store, and focused camera/selection tests. No production code or test file was
changed.
