# M9 Accessibility Adversarial Review

Date: 2026-09-26
Scope: M9 shared shell and five-space journey under `web/`; drawer keyboard and
focus behavior, headings, live regions, WebGL interaction/fallback, reduced
motion, and browser-test blockers.  Documentation-only review; no production
files were changed.

## Verdict

**Static review: conditional pass with release-blocking follow-up. Browser and
assistive-technology sign-off: blocked.**

The product has a reasonable native-control base and the product drawer is
better than the earlier audit record: it moves focus to the close button, wraps
Tab/Shift+Tab, locks body scrolling, closes on Escape through `AppShell`, and
returns focus to the trigger when it closes
([`ProductNavigation.tsx:19-43`](../../../web/components/product/ProductNavigation.tsx#L19-L43),
[`AppShell.tsx:161-168`](../../../web/components/layout/AppShell.tsx#L161-L168)).
Those source properties are not a browser or screen-reader result.

The release remains blocked by five material risks:

1. the M9 shell has no page-level `h1`;
2. the drawer claims `aria-modal` but does not make the rest of the application
   inert, and its focus lifecycle is not DOM-tested;
3. anatomy selection is pointer-only WebGL with no keyboard equivalent;
4. the primary run status and several telemetry/chat states are not announced;
5. reduced motion does not stop the Split Heart `requestAnimationFrame` loop,
   and the WebGL fallback is only an initialization/error placeholder.

## Findings

### A11Y-M9-01 — product drawer has an incomplete modal focus contract (High)

`ProductNavigation` implements a local Tab wrap and initial focus, but the
dialog is only a `role="dialog"`/`aria-modal="true"` assertion. The background
navigation, shell, rails, and WebGL controls are not marked inert or otherwise
removed from the document's focus model. The keydown handler only wraps when
the active element is exactly the first or last drawer control; it does not
recover focus that is moved outside the drawer by script, browser/AT commands,
or a third-party widget. The overlay listens for `mousedown` outside the drawer,
not a general pointer/touch contract
([`ProductNavigation.tsx:27-36`](../../../web/components/product/ProductNavigation.tsx#L27-L36),
[`ProductNavigation.tsx:57-75`](../../../web/components/product/ProductNavigation.tsx#L57-L75)).

There is also a lifecycle smell: the closed branch focuses the trigger on every
effect run, including the initial mount, so mounting the shell can steal focus
from a user agent or assistive technology that already placed focus elsewhere
([`ProductNavigation.tsx:19-22`](../../../web/components/product/ProductNavigation.tsx#L19-L22)).

Required verification: open the drawer from keyboard focus, tab in both
directions, invoke Escape, click/tap the backdrop, select a space, resize, and
attempt programmatic/virtual-cursor movement. Confirm that no background control
receives focus, focus returns to the actual opener, and the drawer is announced
once. Treat this as unresolved until a DOM/browser test exists.

### A11Y-M9-02 — shell heading hierarchy starts below `h1` (High)

The `/` and `/<mode>` pages render `AppShell` directly, but the shell brand is
plain `div` content and the shared `PanelHeader` begins with `h2`. The drawer's
`h2` exists only while it is open. A heading-navigation user therefore reaches
panel headings without a page-level heading identifying BeatIT and the active
space
([`page.tsx:1-10`](../../../web/app/page.tsx#L1-L10),
[`[mode]/page.tsx:1-10`](../../../web/app/[mode]/page.tsx#L1-L10),
[`AppShell.tsx:219-246`](../../../web/components/layout/AppShell.tsx#L219-L246),
[`Panel.tsx:58-70`](../../../web/components/ui/Panel.tsx#L58-L70)).

The reusable `Panel` is also a bare `section`; its `h2` has no generated ID and
the section has no `aria-labelledby`, so the landmark tree cannot consistently
name the major rails and work surface. This is especially costly when the
visual layout collapses at narrow widths.

Required verification: inspect the accessibility tree at `/`, `/twin`, and all
other modes at narrow and wide widths. The page heading, active space heading,
panel landmarks, and drawer heading must form a coherent hierarchy without
duplicate or skipped labels.

### A11Y-M9-03 — WebGL anatomy interaction has no non-pointer path (Critical)

`SemanticPickLayer` attaches `onPointerOver`, `onPointerOut`, and `onClick` to
React Three Fiber meshes. The meshes are not DOM focus targets and expose no
keyboard event. The canvas wrapper's `aria-label` names the visualization but
does not enumerate or operate its selectable anatomy
([`SemanticPickLayer.tsx:19-21`](../../../web/components/heart/interaction/SemanticPickLayer.tsx#L19-L21),
[`HeartScene.tsx:1107-1123`](../../../web/components/heart/HeartScene.tsx#L1107-L1123)).

The visible findings readout is a text-only `ul`; its rows are not buttons or
links and do not select the corresponding component
([`HeartScene.tsx:1129-1177`](../../../web/components/heart/HeartScene.tsx#L1129-L1177)).
Consequently, a keyboard-only, screen-reader, touch-without-hover, or WebGL
failure user cannot reach the same component report workflow as a mouse user.
The component inspector itself has useful headings and a close button, but that
does not repair the inaccessible entry point
([`ComponentInspector.tsx:75-110`](../../../web/components/heart/inspector/ComponentInspector.tsx#L75-L110)).

Required follow-up: provide a keyboard-reachable anatomy list or equivalent
semantic control model, expose selection and report state textually, and test
that every pointer-selectable anatomy can be selected without WebGL.

### A11Y-M9-04 — WebGL fallback is not a usable accessibility fallback (High)

`CanvasFallback` is only the client-only initialization placeholder. It says
`initializing viewport`, includes decorative pulse/ECG motion, and does not
provide metrics, findings, provenance, anatomy controls, or a retry/return
decision of its own
([`HeartScene.tsx:927-947`](../../../web/components/heart/HeartScene.tsx#L927-L947)).
The surrounding `ErrorBoundary` catches a render failure and offers Retry, but
its fallback exposes the truncated exception message and does not retain a
structured cardiac summary or guarantee that the safety/context content remains
available
([`ErrorBoundary.tsx:23-59`](../../../web/components/ui/ErrorBoundary.tsx#L23-L59)).

There is no source-visible capability check before mounting the scene, no
`webglcontextlost` recovery path, no announcement of a context transition, and
no deterministic static cardiac/finding view. This falls short of the existing
M9 fallback contract, which requires preserving valid metrics/findings and
keyboard navigation when WebGL is unavailable
([`M9_PERFORMANCE.md:120-161`](../M9_PERFORMANCE.md#L120-L161)).

Required verification: disable WebGL, force software rendering, trigger context
loss, and exercise the lower-cost fallback. Confirm that the user can inspect
valid state, reach all controls, hear the transition, retry once, and continue
to another space without a blank or falsely live viewport.

### A11Y-M9-05 — run, trace, and telemetry updates are not consistently live
(High)

The header's changing pipeline status is a plain `span`, so transitions such as
“Extracting evidence”, “Run complete”, and “Run failed” have no declared live
region or atomic update
([`AppShell.tsx:219-246`](../../../web/components/layout/AppShell.tsx#L219-L246)).
Agent trace, evaluation, and Redis rail updates likewise render as ordinary
content; a visual pulse is not an announcement. The M9 audit also identifies
CareGuard logs/errors and third-party CopilotKit streaming semantics as
unverified or non-live
([`M9_ACCESSIBILITY.md:180-205`](../M9_ACCESSIBILITY.md#L180-L205)).

The unified assistant is a positive exception: its local panel uses a tested
focus-trap primitive and `role="log"`/polite additions
([`BeatITCopilotPanel.tsx:142-177`](../../../web/components/assistant/BeatITCopilotPanel.tsx#L142-L177)).
That exception must not be generalized to the separate `CopilotDock`, whose
third-party message DOM and streaming behavior remain unverified
([`CopilotDock.tsx:563-611`](../../../web/components/copilot/CopilotDock.tsx#L563-L611)).

Required verification: with a screen reader or accessibility-tree recorder,
exercise idle, each pipeline stage, success, transport error, trace arrival,
Redis degradation, Copilot streaming, and empty/unavailable states. Verify one
concise announcement per meaningful state change, without flooding from frame
or trace updates.

### A11Y-M9-06 — reduced motion leaves an active comparison clock (High)

The heart canvas reads `useReducedMotion`, switches to `frameloop="demand"`,
and passes `animate={!reduce}`. However, `SplitHeartComparison` starts playing
by default and schedules a new `requestAnimationFrame` from every tick without
reading the preference
([`HeartScene.tsx:895-912`](../../../web/components/heart/HeartScene.tsx#L895-L912),
[`SplitHeartComparison.tsx:51-69`](../../../web/components/twin/comparison/SplitHeartComparison.tsx#L51-L69)).
Reduced-motion users can therefore still receive continuous phase/cursor state
updates in Compare even when the nested canvases stop their own animation.

The global CSS rule covers CSS transitions and smooth scrolling, but it cannot
stop JavaScript animation, WebGL internals, or CopilotKit motion
([`globals.css:456-464`](../../../web/app/globals.css#L456-L464)). The current
pure hook tests do not prove mounted lifecycle behavior, animation cancellation,
or actual `matchMedia` changes in a browser.

Required verification: enable reduced motion before loading each space and
confirm no automatic heart, comparison-clock, camera, chart, drawer, or chat
motion continues. User-requested playback may remain available if it is
explicit, bounded, interruptible, and clearly labeled.

## Browser and tooling blockers

No browser or assistive-technology sign-off is claimed. The existing blocker was
recorded on 2026-09-26 and remains reproducible in this workspace:

```text
playwright --version
Version 1.63.0

ldd ~/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome | rg 'not found|libasound'
libasound.so.2 => not found

playwright screenshot --browser=chromium ...
error while loading shared libraries: libasound.so.2: cannot open shared object file

playwright screenshot --browser=firefox ...
Executable doesn't exist at ~/.cache/ms-playwright/firefox-1543/firefox/firefox
```

The workspace has a cached older Firefox directory, but not the Playwright
revision requested by the CLI. `web/node_modules` also has no Playwright,
`@playwright/test`, or `axe-core`, and no browser-test configuration was found
([`M5.5_BROWSER_QA.md:19-30`](../M5_5_BROWSER_QA.md#L19-L30)). Therefore there
is no screenshot, accessibility tree, real Tab traversal, computed-style scan,
WebGL console result, reduced-motion result, or screen-reader evidence. HTTP
success, TypeScript, lint, and a production build would not close these gates.

## Sign-off gate

Keep this review **BLOCKED — static evidence only** until a compatible Chromium
or Firefox runtime is available and the following evidence is retained:

1. Keyboard-only five-space journey at 360px and wide viewport, including
   drawer open/close, Escape, backdrop, focus trapping/restoration, Back/Forward,
   and no background focus while modal content is open.
2. Accessibility-tree or screen-reader checks for the page heading, panel
   landmarks, run status, trace/telemetry updates, Copilot streaming, and all
   error/empty/loading states.
3. Keyboard and non-WebGL anatomy selection covering every component report.
4. WebGL unavailable, context-loss, reduced-motion, and low-cost fallback
   journeys with metrics, findings, safety text, retry, and return navigation
   intact.
5. A browser-based axe or equivalent scan plus manual focus-visible, zoom,
   contrast, and responsive checks.

No production code, tests, configuration, or other documentation files were
changed for this review.
