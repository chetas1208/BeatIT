# M9 Interaction Contract

Status: **M9 product contract**  
Date: 2026-09-26

This document defines the interaction rules for the unified BeatIT journey. It
covers the five primary spaces: `TWIN`, `EXPERIMENT`, `COMPARE`, `EVIDENCE`,
and `REPORT`. The contract preserves the active case and its provenance while
making every transition reversible and understandable.

## Interaction principles

- The Digital Twin is the continuity surface. A surface may inspect or derive
  from the active case, but navigation must not silently replace the case,
  observed history, or selected origin snapshot.
- A drawer is a focused detail surface, not a second application. It preserves
  the surface behind it and always offers an explicit close action.
- Observed, derived, hypothetical, and synthetic content keeps its existing
  language and status labels. Loading or unavailable content is never replaced
  with plausible-looking values.
- Every asynchronous state has a visible equivalent and an assistive-technology
  announcement where appropriate.
- The browser history is part of the interaction model: Back reverses the
  latest navigational or drawer change before leaving the active journey.

## Drawer rules

Drawers are used for secondary inspection that benefits from retaining the
underlying surface: provenance, component detail, pair detail, evidence detail,
and report preview. A drawer must not be used to hide a required primary action
or to create an unrelated workflow.

- On wide screens, a drawer opens from the inline edge of the current surface
  and is visually separated from the underlying content. On narrow screens it
  becomes a full-width, full-height sheet with its own scroll region.
- The drawer has `role="dialog"`, `aria-modal="true"`, and an accessible name.
  Its heading identifies the selected item, not only the generic drawer type.
- The drawer remains mounted only while open, or is otherwise inert and removed
  from the accessibility tree while closed. Background controls cannot receive
  focus while the drawer is modal.
- The drawer contains a visible close button in a stable location. The close
  button is available even when the drawer content is loading or failed.
- Drawer content scrolls independently from the underlying page. Opening a
  drawer does not reset the underlying surface scroll position.
- A drawer may be deep-linked when its content has a stable identity. The URL
  must carry enough context to reopen the same detail without relying on an
  in-memory click history.
- Opening a drawer does not mutate the case, observed snapshot, experiment
  parameters, comparison pair, or report data. Any mutation requires a named
  primary action and its own confirmation/state contract.

## Keyboard rules

- All actions are reachable in DOM order with `Tab` and `Shift+Tab`; disabled
  actions remain disabled rather than becoming pointer-only actions.
- `Enter` activates a focused button or link. `Space` activates a focused
  button. Native controls retain their browser keyboard behavior.
- When a drawer is open, `Tab` wraps within the drawer. `Escape` closes the
  drawer unless a nested control explicitly owns an Escape interaction; in
  that case the nested interaction resolves first and the drawer remains open.
- A drawer must not close from an accidental key event while text is being
  edited. Escape closes the drawer only after any nested editor has handled its
  own cancellation behavior.
- Focus-visible styling is required for every keyboard focus target. Focus
  must never be conveyed by color alone, hover, animation, or pointer position.
- Tabs use the native tab pattern already established by the application:
  selected state is exposed with `aria-selected`, and inactive panels are not
  focusable when hidden. Arrow-key roving focus is only allowed when the tab
  implementation owns the complete tablist contract; do not add custom arrow
  handling to ordinary navigation links.
- No keyboard shortcut may be the only way to reach a space, close a drawer,
  retry a request, or return to `TWIN`.

## Outside-click rules

- Clicking the scrim or the area outside a drawer closes it when the drawer is
  an inspection-only surface and there are no unsaved edits.
- The drawer content, header, close button, and controls inside it do not count
  as outside clicks. Pointer-down must be classified before the close action is
  dispatched so a drag or selection cannot close the drawer unexpectedly.
- A drawer containing editable values, a running request, or a confirmation
  step does not close on outside-click. The user must use the explicit close,
  cancel, or discard action and receive the relevant warning when work could be
  lost.
- Outside-click never cancels an active pipeline, experiment, Shadow Trial,
  report generation, or evidence fetch. It only changes visibility of the
  inspection surface.
- On narrow screens, the sheet itself is the interaction boundary; tapping its
  content never dismisses it. Only the scrim or explicit close action dismisses
  an inspection-only sheet.

## Focus rules

- Capture the element that opened the drawer before opening it. Move focus into
  the drawer after it is rendered, preferably to the drawer heading when it is
  static and otherwise to the close button or first meaningful control.
- Keep focus inside a modal drawer until it closes. Do not move focus to a
  newly-rendered result merely because the result appeared; announce the state
  and let the user choose whether to inspect it.
- On close, return focus to the opener if it is still connected, visible, and
  enabled. If it is unavailable because the underlying surface changed, return
  focus to the current surface heading or its primary navigation landmark.
- After route navigation, focus the destination's main heading or equivalent
  landmark once, with a concise route announcement. Do not steal focus during
  background refreshes or trace updates.
- Focus restoration must not scroll the user to an unrelated location. When the
  opener is inside a scroll container, restore the container position before
  focusing it.
- Loading, error, and empty messages are part of the accessible reading order.
  Use `role="status"` with a polite announcement for progress and success;
  use `role="alert"` for actionable failures that require immediate attention.

## Navigation rules

The primary navigation exposes the five spaces in this order:

```text
TWIN  ·  EXPERIMENT  ·  COMPARE  ·  EVIDENCE  ·  REPORT
```

- Each space has a stable route and a visible active state. The active state is
  exposed semantically, not by color alone.
- Navigation keeps the active case identity and the last valid origin snapshot
  in context. It may clear a surface-local selection, but it must not silently
  start a new case or overwrite observed history.
- A route that needs an item uses a stable identifier in the URL. Invalid or
  unavailable identifiers produce an explicit error/empty state with a path
  back to the nearest valid space; they do not render a different item's data.
- Browser Back and Forward restore the corresponding space and deep-linkable
  drawer state. Closing a URL-addressable drawer is a history action, so Back
  does not unexpectedly leave the product.
- Selecting the already-active space is idempotent: it preserves the current
  selection and scroll position unless the user explicitly chooses a reset.
- Primary navigation is available from every space and from every non-blocking
  drawer. A blocking confirmation may temporarily require an explicit response
  before navigation proceeds.
- Links that leave BeatIT identify that they leave the active case context and
  do not pretend to preserve unsaved work.

## Loading, error, and empty rules

### Loading

- Show loading immediately after the user starts an asynchronous action. The
  initiating control becomes disabled when duplicate submission is unsafe and
  has a stable label such as `Loading…`, `Generating…`, or `Retrying…`.
- Preserve already-valid content during refresh and mark it as updating; do not
  replace it with a blank panel. For first load, use a shape-matching skeleton
  only when the content geometry is known; otherwise use a concise status.
- Loading indicators do not imply clinical progress, certainty, or completion.
  Long work exposes what is running and keeps cancel/return behavior explicit.
- Every loading state has a bounded failure path. A spinner without progress,
  retry, cancellation, or an honest unavailable outcome is not a valid state.

### Error

- Explain what failed in user language, preserve the active case and any valid
  prior result, and provide the smallest useful next action: retry, choose a
  valid origin, return to `TWIN`, or continue with available evidence.
- Never show a fabricated result, stale result as current, raw exception, secret,
  or patient-identifying payload in an error surface. Keep the canonical safety
  disclaimer wherever the underlying API contract requires it.
- Errors caused by missing prerequisites are distinct from transport or server
  failures. Say what is missing and link to the surface that can provide it.
- A retry is idempotent from the user's perspective: it does not silently
  create a second case or duplicate a persisted trial/report.

### Empty and unavailable

- An empty state says why it is empty, whether the user can change that, and
  what action is available next. Examples: select an observed snapshot, run the
  bounded experiment, choose a valid pair, or return to the active twin.
- “No data yet,” “no valid data,” and “data unavailable” are separate messages.
  Retain rejection reasons and lineage when the contract provides them.
- Empty states keep the surface's heading and navigation available. They do not
  use a disabled-looking blank canvas or a success color to represent absence.
- If a result is intentionally withheld for safety, provenance, or contract
  reasons, state that boundary plainly and do not offer a misleading retry.

## Reduced-motion rules

- Respect `prefers-reduced-motion: reduce` for all transitions, drawer movement,
  focus scrolling, chart animation, camera easing, heart motion, and status
  pulses. Prefer an immediate state change or a short opacity change.
- Reduced motion changes presentation, not meaning. All controls, labels,
  values, loading/error/empty states, and navigation remain available.
- Never use motion as the only loading or status signal. Pair it with text and
  accessible state.
- Do not auto-play a comparison, camera tour, or report transition when reduced
  motion is requested. User-initiated motion remains bounded and interruptible.
- Avoid repeatedly restarting animation when a drawer opens, a trace event
  arrives, or a route is revisited. Preserve the user's position and state.

## Return-to-Twin rules

`TWIN` is the canonical home for the active case and the only default return
target when a secondary workflow loses its local context.

- A return action is labeled `Back to Twin` or `Return to Twin`, not a generic
  `Back`, when it crosses from `EXPERIMENT`, `COMPARE`, `EVIDENCE`, or `REPORT`
  to the cardiac work surface.
- Returning to `TWIN` preserves the active case, the last valid observed origin,
  and any completed read-only result. It does not reset the case, rerun the
  pipeline, or discard evidence.
- Returning from `COMPARE` closes the comparison view and restores the
  single-heart view. It does not mutate or delete the persisted pair/trial.
- Returning from `EXPERIMENT` leaves the hypothetical branch intact for the
  current session, but clearly labels it as hypothetical and does not replace
  observed history.
- Returning from `EVIDENCE` or `REPORT` restores the twin context that opened
  the detail. If that context is unavailable, land on the `TWIN` overview and
  announce the fallback.
- Closing a drawer opened from `TWIN` returns focus to its opener and keeps the
  Twin scroll position. A direct route to `TWIN` focuses the Twin heading once.
- If a return would abandon unsaved edits or an active destructive action, show
  a confirmation with explicit `Stay` and `Leave` choices. Read-only inspection
  and completed results never require confirmation.
- The return path must remain usable in loading, error, and empty states. When
  the originating request fails, `Return to Twin` remains available and does
  not imply that the failed result exists.

## Verification checklist

Before M9 sign-off, verify with keyboard and a browser accessibility tree:

1. Open and close every drawer with the trigger, close button, Escape, and
   eligible outside-click; confirm focus trapping and restoration.
2. Traverse all five spaces with keyboard only; confirm active-state semantics,
   browser Back/Forward, deep links, and preserved case/origin context.
3. Exercise first-load, refresh, retry, transport error, missing prerequisite,
   empty, no-valid-result, and unavailable states without fabricated values.
4. Confirm reduced motion removes drawer/camera/chart/heartbeat animation while
   retaining equivalent information and controls.
5. From every secondary space and each drawer, confirm `Return to Twin` lands on
   the correct case context, preserves valid read-only results, and restores
   focus or announces the documented fallback.
