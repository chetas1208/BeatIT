# M6 Accessibility Review

Date: 2026-09-26
Scope: M6 `ShadowTrialPanel` semantics, keyboard access, status and alert
handling, and browser-level accessibility evidence. No implementation files
were changed. M7 Split Heart and M8 Missing Piece are out of scope.

## Verdict

**Static review: conditional pass. Browser sign-off: BLOCKED.** The panel uses
native interactive elements, has explicit result/error states, and exposes the
important paired data in text. A real browser session could not launch in this
environment, so keyboard traversal, focus rendering, live-region delivery,
responsive behavior, and an automated accessibility scan remain unverified.

One implementation follow-up is required before calling the status handling
complete: starting a trial changes the button label to `Running Shadow Trial…`
but does not update the live status paragraph. A screen-reader user may not be
informed that the request has started.

## Guidance and source reviewed

- `web/AGENTS.md`: requires reading the installed Next.js guidance before
  frontend work.
- `web/node_modules/next/dist/docs/03-architecture/accessibility.md`: route
  announcements, JSX accessibility linting, semantic HTML, focus/contrast,
  and reduced-motion guidance.
- `web/components/twin/shadow-trial/ShadowTrialPanel.tsx`
- `web/types/shadow-trial.ts`
- `web/app/globals.css`

The review did not add ARIA or visual behavior and did not duplicate any
frontend numerical calculations.

## Static semantic and keyboard checks

| Area | Source evidence | Result |
|---|---|---|
| Heading structure | Shared `PanelHeader` renders the `Shadow Trial` title as an `h2`; pair inspection uses an `h3` referenced by `aria-labelledby` | Pass statically; heading exposure still needs a browser tree check |
| Primary action | Run control is a native `button` with `type="button"` and a disabled state while loading or without an ensemble | Pass statically; visible focus and activation need browser verification |
| Pair selection | Native `select` is wrapped by a native `label`; options identify valid and invalid pairs | Pass statically; keyboard selection and announcement need browser verification |
| Disclosure | Provenance uses native `details` and `summary` | Pass statically; expanded/collapsed focus behavior needs browser verification |
| Distribution semantics | Effects are exposed as a labeled `ul`; each item includes median, percentile, unit, and category counts in text | Pass statically |
| Decorative visualization | Distribution range bar is marked `aria-hidden="true"`; the accompanying text carries the values | Pass statically |
| Focus indication | Global `:focus-visible` styling provides a 2px signal outline with offset | Present statically; contrast and visibility at runtime are unverified |
| Keyboard model | No custom keyboard handler, roving tabindex, or pointer-only control is used in the panel | Native keyboard behavior expected; not browser-tested |
| Outer panel name | The shared `Panel` is a `section` containing the `h2`, but has no explicit `aria-labelledby` | Low-priority browser-tree check remains open; do not claim a named region until verified |

## Status, loading, and alert checks

| State | Current behavior | Review result |
|---|---|---|
| Idle / missing prerequisites | Status explains that plausible twins and the hypothetical experiment must be generated first; the run button is disabled when no ensemble exists | Present |
| Loading | Button is disabled and changes to `Running Shadow Trial…` | Visible state present; live announcement gap identified because the status text is not changed when loading starts |
| Successful completion | A polite `role="status"` live region reports valid and invalid pair counts; distributions, pair inspection, provenance, and safety text render | Present statically; announcement timing unverified |
| Request failure | Status changes to an `alert` when the message begins with `Unable`; the message includes the error when available | Present statically; assistive-technology announcement unverified |
| Zero valid pairs / failed trial | A separate `role="alert"` explains that no effect summary is presented and retained invalid pairs remain inspectable | Present statically |
| Invalid selected pair | Scalar comparison is withheld and rejection reasons are rendered in `role="alert"` | Present statically |
| No effect distribution | A text fallback explains that at least one valid pair is required | Present statically |
| Empty pair collection | Pair inspector returns no content; the surrounding result surface still shows the distribution fallback | Needs an explicit browser-tested empty-state decision and announcement check |

## Findings and required follow-up

### A11Y-01 — browser verification is blocked

The exact browser attempt was:

```text
/home/923873155/.local/bin/playwright screenshot \
  --browser=chromium --wait-for-timeout=1000 \
  http://127.0.0.1:3100 /tmp/beatit-m6-accessibility.png
```

Playwright 1.63.0 found the cached Chromium headless shell, but launch failed
before navigation:

```text
error while loading shared libraries: libasound.so.2: cannot open shared object file: No such file or directory
```

The cached Firefox directory does not match the installed Playwright browser
revision, and no browser-based axe result was available. This is an
environment dependency failure, not evidence that the panel fails in a real
browser. Until a compatible browser and system dependencies are available,
there is no claimed screenshot, DOM accessibility tree, keyboard traversal,
focus test, live-region test, or axe result.

### A11Y-02 — loading live-region announcement gap

`run()` sets `loading` before awaiting the API, which updates the button label,
but it does not set the `status` state to a loading message. The status live
region therefore remains at its previous idle message until completion or
failure. Add a concise loading status in the implementation follow-up, then
verify that it is announced once and that completion/failure announcements do
not get lost.

### A11Y-03 — runtime focus and scale checks remain open

The result subtree is inserted after the run control without an explicit focus
move. Keeping focus on the button is reasonable for a short synchronous
action, but this must be checked with keyboard and screen-reader behavior. The
small text sizes, warning colors, narrow layout, 200% zoom, reduced-motion
preference, and horizontal overflow also require a real browser pass.

## Validation evidence

Executed from `/home/923873155/BeatIT` on 2026-09-26:

```text
cd web && ./node_modules/.bin/eslint \
  components/twin/shadow-trial/ShadowTrialPanel.tsx
# exit 0

cd web && ./node_modules/.bin/tsc --noEmit
# exit 0

git diff --check
# pass before this documentation-only addition
```

The installed Next.js accessibility guidance notes JSX accessibility linting,
semantic HTML, visible focus, contrast, and reduced-motion checks; those
principles were used for this static review. No M7 or M8 work was introduced.

## Browser sign-off checklist

After installing a compatible browser runtime and its dependencies, rerun the
M6 surface with keyboard-only input and an accessibility scanner:

1. Verify idle, disabled, ready, loading, success, request-error,
   zero-valid, invalid-pair, and empty-pair states.
2. Confirm visible focus order for the run button, pair selector, disclosure,
   and any surrounding scenario controls.
3. Confirm loading, completion, failure, and invalid-pair announcements with a
   screen reader or accessibility-tree inspection.
4. Check 200% zoom, narrow/mobile layout, text contrast, reduced motion, and
   absence of clipped or hidden status text.
5. Run axe or an equivalent browser accessibility scan and retain its output.

Until then, retain this review as **BLOCKED — static evidence present, real
browser unavailable**. This blocker does not authorize M7 or M8 work.
