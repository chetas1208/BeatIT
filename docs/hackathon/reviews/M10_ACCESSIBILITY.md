# M10 Accessibility and Browser Readiness Review

Status: **STATIC SOURCE AUDIT PASS; BROWSER/AT SIGN-OFF BLOCKED**  
Contribution: **A08**  
Date: **2026-09-26**  
Scope: current frontend under `web/`, including the M9 five-space shell,
Split Heart comparison, assistant surfaces, intake, and CareGuard routes.

This review does not claim browser rendering, keyboard traversal, accessibility
tree, screen-reader, contrast, or axe results. The required browser runtime could
not launch in this environment.

## Executive verdict

The source has a solid baseline: semantic native controls are used for most
actions, the document declares `lang="en"`, global `:focus-visible` styling is
present, asynchronous M9 panels commonly expose `role="status"` or
`role="alert"`, and the assistant focus-trap primitive has unit coverage.

Release accessibility sign-off remains **blocked** by unresolved source and
environment risks:

1. several `role="dialog"` surfaces do not share the tested focus-trap,
   Escape, and focus-restoration contract;
2. Split Heart schedules an unconditional `requestAnimationFrame` loop and does
   not consume the reduced-motion hook;
3. 3D anatomy selection is pointer-only, with no equivalent keyboard control or
   exposed anatomy list in the WebGL surface;
4. the global pipeline status and some telemetry/CareGuard updates are not
   consistently announced as live regions; and
5. no browser or assistive-technology run can currently verify the findings.

## Browser and Playwright availability

Checks run from `/home/923873155/BeatIT` on 2026-09-26:

| Check | Result |
| --- | --- |
| Global Playwright CLI | Present at `/home/923873155/.local/bin/playwright`, version `1.63.0` |
| `web/node_modules/playwright` | Absent |
| `web/node_modules/@playwright` | Absent |
| `web/node_modules/puppeteer` | Absent |
| Shell `chromium`, `chromium-browser`, `google-chrome`, `firefox` | Not on `PATH` |
| Cached Chromium | Present, but launch fails before navigation |
| Cached Firefox | Older binary exists, but Playwright-required `firefox-1543` is absent |
| `libasound.so.2` | Absent |

Direct launch attempts were made against `about:blank`:

```text
playwright screenshot --browser=chromium --wait-for-timeout=250 about:blank ...
exit 1: chrome-headless-shell: error while loading shared libraries:
libasound.so.2: cannot open shared object file: No such file or directory

playwright screenshot --browser=firefox --wait-for-timeout=250 about:blank ...
exit 1: Executable doesn't exist at .../firefox-1543/firefox/firefox
```

Therefore this contribution contains no browser claim, screenshot, DOM
accessibility tree, keyboard result, screen-reader result, or axe result. The
prior detailed environment record is [M5.5 browser QA](../M5_5_BROWSER_QA.md),
which records the same Chromium audio-library blocker and missing Firefox
build.

## Non-browser verification

The following checks passed from `web/`:

```text
./node_modules/.bin/tsc --noEmit -p tsconfig.json
passed

node --experimental-strip-types --loader ./tests/alias-loader.mjs --test \
  ./lib/assistant/__tests__/useReducedMotion.test.ts \
  ./lib/assistant/__tests__/useFocusTrap.test.ts
12 passed, 0 failed

./node_modules/.bin/eslint \
  components/product/ProductNavigation.tsx \
  components/layout/AppShell.tsx \
  components/twin/comparison/SplitHeartComparison.tsx \
  components/heart/interaction/SemanticPickLayer.tsx \
  components/safety/DisclaimerModal.tsx \
  components/copilot/CopilotDock.tsx \
  lib/assistant/useReducedMotion.ts \
  lib/assistant/useFocusTrap.ts
passed
```

These checks establish static type/lint health and pure focus/reduced-motion
logic only. They do not establish DOM behavior.

## Positive source evidence

- The root document sets `lang="en"` in [`web/app/layout.tsx`](../../../web/app/layout.tsx).
- Global keyboard focus styling is defined with `:focus-visible` in
  [`web/app/globals.css`](../../../web/app/globals.css#L190-L194).
- The global stylesheet has a `prefers-reduced-motion: reduce` rule that shortens
  CSS animation and transition durations and disables smooth scrolling
  ([`globals.css`](../../../web/app/globals.css#L453-L464)).
- [`useReducedMotion`](../../../web/lib/assistant/useReducedMotion.ts) is
  SSR-safe and has coverage for SSR, missing `matchMedia`, matching media
  queries, thrown media-query access, and query forwarding.
- [`useFocusTrap`](../../../web/lib/assistant/useFocusTrap.ts) handles initial
  focus, Tab/Shift+Tab wrapping, Escape, and restoration of the prior focus
  target. Its tab-cycling behavior has seven focused unit tests.
- Intake vital fields use native labels and validation descriptions; the upload
  dropzone has a name, `tabIndex={0}`, and Enter/Space activation in
  [`CaseIntakePanel.tsx`](../../../web/components/intake/CaseIntakePanel.tsx#L514-L542).
- Timeline, scenario, plausible-twin, Shadow Trial, and Missing Piece surfaces
  expose useful status/error semantics. Timeline playback and scenario controls
  are native buttons, range inputs, and selects.
- The main visualizations provide some alternatives: SVG PV loops use `role="img"`
  and an accessible label, and the causal graph includes a screen-reader-only
  relationship list.

## Findings

### A11Y-M10-01 — dialog focus behavior is inconsistent (high)

The shared assistant panel and artifact detail panel use `useFocusTrap`, but
these current dialogs do not:

- [`DisclaimerModal.tsx`](../../../web/components/safety/DisclaimerModal.tsx#L45-L75)
  declares `role="dialog"` and `aria-modal="true"` without focus placement,
  Tab containment, Escape handling, or focus restoration;
- [`CaseIntakePanel.tsx`](../../../web/components/intake/CaseIntakePanel.tsx#L780-L817)
  has a synthetic-vitals dialog with the same missing lifecycle contract;
- [`ComponentReportPanel.tsx`](../../../web/components/heart/report/ComponentReportPanel.tsx#L1-L30)
  declares a dialog but does not use the shared trap; and
- [`CopilotDock.tsx`](../../../web/components/copilot/CopilotDock.tsx#L563-L614)
  exposes a dialog and close button, but the wrapper does not establish focus
  entry, containment, or return to its opener.

The product drawer has an explicit local Tab wrap and Escape listener in
[`ProductNavigation.tsx`](../../../web/components/product/ProductNavigation.tsx#L19-L75),
but it is independently implemented and has no DOM/browser test. `aria-modal`
is not itself a guarantee that background controls are inert. Verify opening,
forward and reverse traversal, Escape, backdrop close, route selection, and
focus restoration with a real browser before release.

### A11Y-M10-02 — Split Heart does not honor reduced motion (high)

[`SplitHeartComparison.tsx`](../../../web/components/twin/comparison/SplitHeartComparison.tsx#L60-L69)
starts an unconditional `requestAnimationFrame` loop and updates the comparison
clock on every frame. The component does not read `useReducedMotion`, so the
CSS media query and the nested heart canvas's `frameloop="demand"` setting do
not stop the comparison cursor and phase updates. Add an explicit reduced-motion
state for this non-CSS loop or provide a paused/static initial state, then verify
the media preference in a browser.

### A11Y-M10-03 — WebGL anatomy selection has no keyboard equivalent (high)

[`SemanticPickLayer.tsx`](../../../web/components/heart/interaction/SemanticPickLayer.tsx#L19-L21)
binds selection and hover to React Three Fiber pointer events. The surrounding
canvas has a descriptive label in [`HeartScene.tsx`](../../../web/components/heart/HeartScene.tsx#L994-L1015),
but it does not expose selectable anatomy as focusable DOM controls or a
keyboard-navigable list. A pointer user can inspect a component; a keyboard or
screen-reader user has no equivalent selection path. Provide a visible or
screen-reader-accessible anatomy list/control group, or explicitly make the
visualization non-interactive and expose the report data separately.

### A11Y-M10-04 — live-region coverage is incomplete (medium/high)

The shell status chip in [`AppShell.tsx`](../../../web/components/layout/AppShell.tsx#L225-L245)
is a plain `span`; transitions such as extracting, complete, and failed are not
announced through `role="status"`/`aria-live`. Agent trace, evaluation, and
Redis telemetry also update as ordinary visual content. The CareGuard runner
and copilot have additional async output that needs live-region review.

The M9 panels are stronger: Timeline has a polite cursor announcement, and
Scenario, Plausible Twins, Shadow Trial, and Missing Piece expose status/error
regions. The final browser pass should confirm that announcements are neither
missing nor excessively repeated.

### A11Y-M10-05 — heading, labeling, and fallback paths need browser confirmation (medium)

The M9 shell still has no clear page-level `h1`; shared panel headings commonly
start at `h2`. The reusable panel/rail structure should be checked for named
landmarks. The main five-space navigation uses buttons with `aria-current`, so
keyboard activation exists, but native link behavior and browser history should
be verified. The CareGuard and legacy intake surfaces retain adjacent or
placeholder-only labels documented in the M9 audit.

The WebGL loading/error fallback is important for environments without WebGL,
but its actual announcement and keyboard usability cannot be confirmed without
browser execution.

## Required browser verification when unblocked

Run the production build or local Next server, then cover at minimum:

1. open and dismiss the first-use disclaimer; verify initial focus, Escape or
   the named action, and focus return;
2. open the product-space drawer, traverse Tab and Shift+Tab at both ends,
   select each space, use Escape/backdrop close, and verify focus return;
3. open and close Copilot, report, and synthetic-vitals dialogs; check focus
   containment and that the background cannot be reached by keyboard;
4. navigate the five spaces using keyboard only, including a reload and browser
   Back/Forward;
5. activate the intake upload dropzone with Enter and Space, and verify its
   disabled state and validation announcements;
6. run a deterministic case and confirm pipeline, trace, evaluation, error,
   and Redis updates are announced appropriately;
7. set `prefers-reduced-motion: reduce`, then inspect the shell, charts, heart,
   Split Heart clock, playback, loading states, and Copilot transitions;
8. verify a keyboard-accessible alternative for every anatomy selection and
   inspect the WebGL fallback with JavaScript/WebGL unavailable; and
9. capture an accessibility tree and run an axe scan on `/`, `/twin`,
   `/experiment`, `/compare`, `/evidence`, `/report`, and the CareGuard routes.

## Release disposition

**Conditional static pass only. Do not mark accessibility/browser readiness
complete.** TypeScript, scoped lint, and pure focus/reduced-motion tests pass,
but the release gate remains open until a browser can launch and the high-risk
dialog, reduced-motion, WebGL keyboard, live-region, and fallback paths receive
real DOM/browser verification. This review made no production-code changes.
