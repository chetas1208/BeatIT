# Wave 4 — Chat accessibility audit & primitives (Agent 20)

Scope: `web/lib/assistant/`, `web/components/assistant/`. Read-only pass over
`web/components/copilot/CopilotDock.tsx` and `web/components/safety/DisclaimerModal.tsx`
for convention-matching only — neither file was modified.

## What existed, and when

`web/components/assistant/` and `web/lib/assistant/` did not exist at task start
(`find web/components/assistant -type f` → "No such file or directory"). Sibling
Wave 4 agents landed files while this task was in progress; final set audited:

| File | Agent | Landed |
|---|---|---|
| `BeatITCopilotTrigger.tsx` | 16 | early |
| `BeatITCopilotPanel.tsx` | 16 | early |
| `ArtifactCard.tsx` | 18 | early |
| `PhysicianBriefView.tsx` | 18 | early |
| `SuggestedActionChips.tsx` | 19 | mid-task |
| `ArtifactDetailPanel.tsx` | 18 | mid-task |

No repo-wide focus-trap, matchMedia-based reduced-motion hook, or
visually-hidden component existed before this task (see "Pre-existing
utilities" below) — all three were built new.

## Repo conventions found (read-only survey)

- Dialog-like surfaces use `role="dialog"` + `aria-label`/`aria-labelledby`
  (`DisclaimerModal.tsx` also adds `aria-modal="true"`; `CopilotDock.tsx`'s
  panel uses plain `role="dialog"` with no `aria-modal`). **None of the
  existing dialogs (`DisclaimerModal`, `CopilotDock`) actually trap focus,
  handle Escape, or restore focus to a trigger** — they rely on a visible
  close button only. This is a pre-existing gap in the codebase, not
  something Wave 4 introduced; out of scope to fix here (`CopilotDock.tsx`
  and `DisclaimerModal` are on this task's do-not-touch list) but worth a
  follow-up ticket since the same gap was about to be repeated in the new
  surface.
- Icon-only triggers consistently pair `aria-hidden` on the decorative icon
  with `aria-label` on the interactive `<button>` (`CopilotDock`'s dock
  toggle, `BeatITCopilotTrigger`). Followed the same pattern here.
- Responsive convention (`AppShell.tsx`, read-only): **`lg:` is the
  desktop breakpoint**; unprefixed classes are the mobile/base layout (the
  3-column desktop grid collapses to `grid-cols-12` stacked panels below
  `lg`). There is no repo-wide `sm:`/`md:` convention to match — `lg:` is it.
  Floating panels (`CopilotDock`, `BeatITCopilotPanel`) don't participate in
  that grid; they size themselves with `min(<rem>, calc(100vw/100dvh - <gap>))`,
  which is itself the mobile-safe pattern (no fixed-pixel dialog width to
  reflow at phone width).
- Contrast: color tokens in `web/app/globals.css` are pre-annotated with
  approximate ratios (`--ht-ink` ~13:1, `--ht-ink-2` ~8:1, `--ht-muted` ~5:1
  against the surface tokens) — comfortably above WCAG AA 4.5:1 for text.
  Font sizes across the whole console (not just Wave 4 files) commonly run
  0.72–0.86rem for secondary text; that's an existing app-wide convention
  (seen identically in `ComponentReport.tsx`, `Panel.tsx`, etc.), not a
  Wave 4 regression, and out of this task's scope to change.
- Test convention: **`node:test` + `node:assert/strict`**, run via
  `node --experimental-strip-types --loader ./tests/alias-loader.mjs --test <files>`
  (see `web/package.json`'s `test:runtime` script and
  `web/lib/twin/reducer/__tests__/reducer.test.ts`). No jsdom or
  `@testing-library/*` dependency exists in `web/package.json` — confirmed by
  grep. That matters below.

## Findings per file (as audited)

### `BeatITCopilotTrigger.tsx` (Agent 16)
- Native `<button>`, `aria-expanded`, `aria-label` that flips with state —
  correct, no fix needed.
- No responsive issue (fixed `bottom-4 left-4`, intrinsic button size).
- **Gap (fixed):** opening the panel didn't move focus into it or trap Tab;
  closing didn't return focus to this button. Fixed by wiring the new
  `useFocusTrap` hook inside `BeatITCopilotPanel.tsx` (see below) — the hook
  reads `document.activeElement` (this button, since it's what's focused at
  click time) when `active` flips true, so no prop plumbing back to the
  trigger was needed.

### `BeatITCopilotPanel.tsx` (Agent 16)
Findings at audit time (before my fixes):
1. `role="dialog"` with no `aria-modal` and no focus trap/Escape/restore —
   same gap as the existing `CopilotDock`/`DisclaimerModal` pattern, about to
   be repeated a third time.
2. The scrollable message list had no `aria-live`/`role="log"` — new
   assistant replies and the "thinking…" state would not be announced to
   screen reader users at all.
3. The message `<input>` had only a `placeholder`, no accessible name
   independent of that placeholder (placeholder text disappears once typed
   and isn't a reliable label for all AT/browser combinations).
4. Close button, send button: already correct (`aria-label`, native
   `<button>`). No fix needed.
5. Responsive: panel sizes with `min(24rem, calc(100vw - 2rem))` /
   `min(34rem, calc(100dvh - 7rem))` — already phone-width-safe, no fixed
   pixel width. No fix needed.
6. Keyboard reachability: every interactive element (trigger, close, input,
   send) is a native `<button>`/`<input>` — all reachable. The one
   `ArtifactChip` in the stub is `disabled` intentionally (it's a
   placeholder for Agent 18's real artifact viewer, not a broken control).

### `ArtifactCard.tsx` (Agent 18)
- Native `<button>` for "View" with a descriptive `aria-label`
  (`View {label}: {title}`), decorative icon marked `aria-hidden`. No gap
  found, no fix made.

### `PhysicianBriefView.tsx` (Agent 18)
- Semantic `<section>`/`<h3>` per finding group, decorative icons
  `aria-hidden`. No interactive elements to check reachability on (pure
  display view rendered inside `ArtifactDetailPanel`). No gap found.

### `SuggestedActionChips.tsx` (Agent 19)
- `role="group"` + `aria-label="Suggested questions"` on the wrapper, native
  `<button>` per chip, `flex-wrap` (reflows at any width, no fixed widths).
  No gap found, no fix made.

### `ArtifactDetailPanel.tsx` (Agent 18)
Findings at audit time (before my fix):
1. `role="dialog"` **and** `aria-modal="true"` — but with no focus trap, no
   Escape handling, and no focus restoration. This is the sharpest version
   of the pre-existing gap: `aria-modal="true"` is an explicit assertion to
   assistive tech that content outside the dialog is inert, which was false
   here (a sighted keyboard user could Tab straight out into
   `ArtifactCard`/chat content behind it). Fixed (see below).
2. Close button: already correct (`aria-label="Close artifact detail"`,
   native `<button>`).
3. Responsive: `absolute inset-0` with `mx-auto max-w-2xl` inner content —
   fills its positioned parent and reflows at any width, no fixed pixel
   width. No fix needed.

## Targeted fixes made (exact diffs)

All four are additive — no visual/behavioral change besides accessibility,
no restructuring. Flagging for Agent 16/18 to review on integration.

### `web/components/assistant/BeatITCopilotPanel.tsx`

```diff
-import { useMemo, useState, type FormEvent } from "react";
+import { useMemo, useRef, useState, type FormEvent } from "react";
 import { FileText, PaperPlaneRight, Sparkle } from "@phosphor-icons/react";
 import { sendAssistantMessage, AssistantApiError } from "@/lib/assistantApi";
+import { useFocusTrap } from "@/lib/assistant/useFocusTrap";
 import type { AssistantArtifact, ExecutionClass } from "@/types/assistant";
@@
   const [loading, setLoading] = useState(false);
+  const containerRef = useRef<HTMLDivElement>(null);
+  // Traps Tab inside the panel, closes on Escape, and restores focus to the
+  // trigger button on close — the panel renders via `if (!open) return null`
+  // below rather than unmounting, so `open` doubles as the trap's active flag.
+  useFocusTrap(containerRef, open, onClose);
@@
   return (
     <div
+      ref={containerRef}
       className="ht-panel-raised fixed bottom-20 left-4 flex h-[min(34rem,calc(100dvh-7rem))] w-[min(24rem,calc(100vw-2rem))] flex-col overflow-hidden"
       style={{ zIndex: "var(--ht-z-dock)" }}
       role="dialog"
+      aria-modal="true"
       aria-label="BeatIT Copilot"
     >
@@
-      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-4 py-3">
+      <div
+        className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-4 py-3"
+        role="log"
+        aria-live="polite"
+        aria-relevant="additions"
+      >
@@
           placeholder="Ask about this case"
+          aria-label="Message BeatIT Copilot"
           disabled={loading}
```

### `web/components/assistant/ArtifactDetailPanel.tsx`

```diff
+import { useRef } from "react";
 import { X } from "@phosphor-icons/react";
+import { useFocusTrap } from "@/lib/assistant/useFocusTrap";
 import type { AssistantArtifact } from "./ArtifactCard";
 import { hasRealArtifactView } from "./ArtifactCard";
 import { PhysicianBriefView } from "./PhysicianBriefView";
@@
 }) {
+  const containerRef = useRef<HTMLDivElement>(null);
+  // Mounted only while open (the caller conditionally renders this panel), so
+  // the trap is active for the component's whole lifetime; restores focus to
+  // the ArtifactCard "View" button that opened it on unmount.
+  useFocusTrap(containerRef, true, onClose);
+
   return (
     <div
+      ref={containerRef}
       role="dialog"
       aria-modal="true"
       aria-label={`${artifact.title} detail`}
```

Verified after edit: `npx eslint` clean on both files, and
`npx tsc --noEmit` shows zero errors under `web/components/assistant/` or
`web/lib/assistant/` (ran the full project typecheck and grepped for
`assistant` in the output — none).

**Not fixed / left for integration:** `BeatITCopilotTrigger.tsx` itself
needed no direct edit (the trigger's own markup was already correct); the
focus-trap wiring lives in the panel it renders, as described above.

## New primitives

### `web/lib/assistant/useReducedMotion.ts`

```ts
const reduced = useReducedMotion(); // boolean, false during SSR
```

SSR-safe wrapper around `matchMedia('(prefers-reduced-motion: reduce)')`,
built on `useSyncExternalStore` (the same pattern `DisclaimerModal.tsx`
already uses for its localStorage read) rather than `useState` +
`useEffect(() => setState(...))`, because the latter trips this repo's
`react-hooks/set-state-in-effect` lint rule (confirmed: it did, first draft
failed `npx eslint` with exactly that error; fixed by switching to
`useSyncExternalStore`). Server snapshot is `false`, so there's no hydration
mismatch. The pure read (`readPrefersReducedMotion(host)`) is exported
separately and unit-tested without a DOM.

Note: `motion/react` (used in `CopilotDock.tsx`) already exports its own
`useReducedMotion` — for components already inside a `framer-motion` tree,
keep using that one for consistency. This hook is for the rest of the
`assistant/` surface (plain CSS transitions, or components that shouldn't
need to import the whole animation library just to read a media query).

### `web/lib/assistant/useFocusTrap.ts`

```ts
const containerRef = useRef<HTMLDivElement>(null);
useFocusTrap(containerRef, open /* or `true` if the panel unmounts to close */, onClose);
// ...
<div ref={containerRef} role="dialog" aria-modal="true">
```

While `active`:
- captures `document.activeElement` (typically the trigger button) to
  restore focus to later,
- moves focus to the first focusable element inside the container (or the
  container itself if it has none),
- cycles Tab/Shift+Tab at the container's edges so focus never leaves it,
- calls `onClose()` on Escape,
- restores focus to the captured element when `active` goes false or the
  hook unmounts.

Two call shapes, both used in this pass:
- **Panel that unmounts via `if (!open) return null`** (`BeatITCopilotPanel`):
  pass the `open` boolean as `active` directly.
- **Panel the parent conditionally renders/unmounts** (`ArtifactDetailPanel`):
  pass `true` — the effect's cleanup on unmount does the focus restoration.

`nextTrapFocusTarget(focusable, activeElement, shiftKey)` is exported
standalone (pure array/identity logic, no DOM calls) so the tab-cycling
decision is unit-tested without jsdom.

### `web/components/assistant/VisuallyHidden.tsx`

```tsx
<VisuallyHidden as="label" htmlFor="msg">Message</VisuallyHidden>
```

Standard clip-not-`display:none` pattern (stays in the accessibility tree
and reachable by AT/keyboard, unlike `hidden`/`display:none`). No repo
equivalent existed. Built with `createElement` instead of JSX because using
a generic `ElementType` directly as a JSX tag produces `TS2745` (children
prop narrows to `never`) — confirmed by running `tsc --noEmit`, fixed by
switching to `createElement(as, { style }, children)`.

## Pre-existing utilities check (before building new)

- **Focus trap:** none found (`grep -rli "focus.trap\|focustrap" web` → no
  hits). Built new.
- **Reduced motion:** no standalone hook; `motion/react`'s own
  `useReducedMotion` is used inline in `CopilotDock.tsx` via
  `import { useReducedMotion } from "motion/react"`, but nothing wraps plain
  `matchMedia` for non-framer-motion use. Built new (see note above on when
  to prefer which).
- **Visually-hidden:** none found (`grep -rli "visuallyhidden\|sr-only\|screenreader" web` →
  no hits). Built new.

## Tests

Written, following this repo's actual convention (`node:test`, not
jest/vitest — none of those exist in `web/package.json`):

- `web/lib/assistant/__tests__/useReducedMotion.test.ts` — 5 cases against
  `readPrefersReducedMotion` (SSR/undefined host, no-`matchMedia` host,
  `matches: true`, throwing `matchMedia`, correct query string passed).
- `web/lib/assistant/__tests__/useFocusTrap.test.ts` — 7 cases against
  `nextTrapFocusTarget` (empty list, forward-wrap at the end, no-op in the
  middle, recovering when focus left the trap, shift+tab wrap at the start,
  no-op in the middle, single-element trap in both directions).

Both pass: `node --experimental-strip-types --loader ./tests/alias-loader.mjs --test ./lib/assistant/__tests__/useReducedMotion.test.ts ./lib/assistant/__tests__/useFocusTrap.test.ts` → `12 pass, 0 fail`.

**Explicitly not covered:** this repo has no jsdom or
`@testing-library/react` dependency (checked `web/package.json`), so there is
no way to exercise the two hooks' actual React-lifecycle/DOM behavior
(mounting a real container, real `Tab` keydown cycling across real focusable
elements, a real `document.activeElement`, a real `MediaQueryList` change
event) under this repo's existing test convention. The tests above cover
every pure decision function each hook is built on top of, which is the full
extent of what's unit-testable without adding a new test dependency — adding
jsdom/testing-library is a real (if small) infra decision outside a single
task's scope, flagged here for the lead rather than done unilaterally.

**Also not done (would touch a forbidden file):** `web/package.json`'s
`test:runtime` script lists test files explicitly rather than globbing
`__tests__/**` (confirmed — most existing `__tests__` directories under
`web/lib/twin/*` aren't in that list either, so this predates Wave 4). The
two new test files are runnable directly with the command above but aren't
wired into `test:runtime` since editing `web/package.json` is outside this
task's allowed paths.

## Still needed / open items for integration

1. **`CopilotDock.tsx` and `DisclaimerModal.tsx`** have the same
   trap/Escape/restore gap as the Wave 4 files did — pre-existing, out of
   this task's scope (do-not-touch list), but worth a follow-up now that
   `useFocusTrap` exists to fix it with.
2. If a later wave adds more assistant dialogs/overlays, wire
   `useFocusTrap` the same way shown above rather than re-deriving
   focus-management by hand.
3. Confirm with Agent 16/18 that the four targeted diffs above are wanted as-is
   during integration (they're additive and lint/type-clean, but both files
   are actively owned by those agents this wave).
