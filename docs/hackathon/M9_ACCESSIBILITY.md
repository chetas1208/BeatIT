# M9 Accessibility Audit

Status: **STATIC AUDIT COMPLETE — browser and assistive-technology validation
blocked**
Date: 2026-09-26
Scope: current React surfaces under `web/app/` and `web/components/`, including
the M9 five-space shell and the separate CareGuard routes.

This is a source and token audit, not an accessibility conformance claim. The
existing browser record says Playwright cannot launch Chromium because
`libasound.so.2` is missing, Firefox is unavailable, and no accessibility-tree,
keyboard, screen-reader, or axe result exists
([M5.5 browser QA](./M5_5_BROWSER_QA.md#L1-L11)).

## Verdict

The codebase has a useful accessibility foundation: native controls are used
for most actions, the document declares `lang="en"`, `:focus-visible` is
defined globally, many async M9 states use `role="status"`/`role="alert"`, and
the new assistant panel has a tested focus-trap primitive. It is not ready for
browser or AT sign-off.

The highest-risk gaps are:

1. the main shell has no document `h1`, while the shared panel primitive starts
   most content at `h2`;
2. several elements claim to be modal dialogs without focus containment,
   Escape handling, or focus restoration;
3. the primary 3D heart interaction is pointer-only WebGL, with no keyboard
   anatomy-selection equivalent;
4. dynamic trace/status and the legacy CareGuard workflow are inconsistently
   announced;
5. reduced motion does not cover the comparison clock's unconditional
   `requestAnimationFrame` loop; and
6. the amber and faint text tokens used in light surfaces are below the
   contrast target for normal text.

## Surface inventory

| Surface | Entry point | Accessibility-relevant implementation | Audit result |
| --- | --- | --- | --- |
| M9 shared shell | `/`, `/<mode>` | `AppShell`, `ProductNavigation`, `Panel`, intake, Twin/Experiment/Compare/Evidence/Report | Good native-control baseline; heading, modal, live-region, and WebGL gaps remain. |
| Cardiology Copilot | `CopilotDock` in non-Report M9 modes | Third-party `CopilotChat` inside a floating `role="dialog"` | Trigger is named and expanded state is exposed; focus behavior and generated chat semantics are unverified and the dialog has no local focus trap. |
| Flagged unified assistant | `BeatITCopilotTrigger` | Plain React panel plus `useFocusTrap`, `role="log"`, `aria-live="polite"` | Strongest dialog implementation in the repo; lifecycle behavior still lacks a real DOM test. |
| CareGuard console | `/careguard` | React with inline styles, separate copilot and long result workflow | Native controls exist, but labels, live feedback, dialog behavior, and focus styling are incomplete. |
| CareGuard browser/runner | `/careguard/cases`, `/careguard/runner` | React forms and case list | Several visible labels are not programmatically associated; errors and run logs are not live regions. |

## Keyboard and focus

### Positive findings

- The main actions are generally native `<button>`, `<input>`, `<select>`,
  `<textarea>`, `<details>`, and `<summary>` controls. Timeline playback,
  range inputs, playback-rate buttons, scenario sliders, and pair selectors
  therefore inherit browser keyboard behavior. Examples:
  [`Timeline.tsx:178-266`](../../web/components/twin/timeline/Timeline.tsx#L178-L266)
  and [`ParameterControls.tsx:29-50`](../../web/components/twin/scenario/ParameterControls.tsx#L29-L50).
- The upload dropzone has an accessible name, `tabIndex={0}`, and explicit
  Enter/Space activation
  ([`CaseIntakePanel.tsx:514-525`](../../web/components/intake/CaseIntakePanel.tsx#L514-L525)).
  Vital inputs use real labels and conditional validation descriptions
  ([`CaseIntakePanel.tsx:842-868`](../../web/components/intake/CaseIntakePanel.tsx#L842-L868)).
- Global keyboard focus styling exists as a two-pixel signal outline
  ([`globals.css:192-198`](../../web/app/globals.css#L192-L198)), and the
  assistant panel's `useFocusTrap` handles Tab/Shift+Tab, Escape, and focus
  restoration in its own implementation
  ([`useFocusTrap.ts:65-101`](../../web/lib/assistant/useFocusTrap.ts#L65-L101)).

### Findings requiring remediation or browser verification

- **Modal focus management is inconsistent.** The disclaimer, product-space
  drawer, synthetic-vitals dialog, component report, and Cardiology Copilot
  declare dialog semantics or behave as overlays but do not all move focus into
  the surface, contain Tab, close on Escape, and restore focus to the trigger:
  [`DisclaimerModal.tsx:45-75`](../../web/components/safety/DisclaimerModal.tsx#L45-L75),
  [`ProductNavigation.tsx:27-44`](../../web/components/product/ProductNavigation.tsx#L27-L44),
  [`CaseIntakePanel.tsx:780-817`](../../web/components/intake/CaseIntakePanel.tsx#L780-L817),
  [`ComponentReportPanel.tsx:6-10`](../../web/components/heart/report/ComponentReportPanel.tsx#L6-L10),
  and [`CopilotDock.tsx:563-614`](../../web/components/copilot/CopilotDock.tsx#L563-L614).
  `aria-modal="true"` is therefore not yet a reliable assertion that the
  background is inert. The flagged assistant panel and artifact detail panel
  are exceptions because they use `useFocusTrap`
  ([`BeatITCopilotPanel.tsx:65-147`](../../web/components/assistant/BeatITCopilotPanel.tsx#L65-L147),
  [`ArtifactDetailPanel.tsx:59-88`](../../web/components/assistant/ArtifactDetailPanel.tsx#L59-L88)).
- **The product drawer has an Escape listener but no focus restoration or
  containment.** `AppShell` closes it from a window key listener
  ([`AppShell.tsx:100-107`](../../web/components/layout/AppShell.tsx#L100-L107));
  it does not establish the dialog focus contract described by M9's interaction
  rules ([`M9_INTERACTIONS.md:36-64`](./M9_INTERACTIONS.md#L36-L64)).
- **The 3D anatomy selection is pointer-only.**
  `SemanticPickLayer` attaches `onPointerOver`, `onPointerOut`, and `onClick` to
  React Three Fiber meshes, with no focusable DOM equivalent or keyboard event
  ([`SemanticPickLayer.tsx:19-21`](../../web/components/heart/interaction/SemanticPickLayer.tsx#L19-L21)).
  The canvas wrapper's `aria-label` names the visualization but does not expose
  its selectable anatomy to keyboard or screen-reader users
  ([`HeartScene.tsx:994-1019`](../../web/components/heart/HeartScene.tsx#L994-L1019)).
  The findings list is text-only, so it does not provide a fallback selection
  path.
- **The custom dropzone remains tabbable while disabled.** It uses
  `aria-disabled` on a `div role="button"` rather than native disabled behavior
  ([`CaseIntakePanel.tsx:514-542`](../../web/components/intake/CaseIntakePanel.tsx#L514-L542)).
  Its handlers guard activation, but browser/AT behavior and whether the
  disabled state is sufficiently communicated still require verification.
- **Some focus indicators are weaker than the global default.** The unified
  assistant input uses `outline-none` and only changes its border on focus
  ([`BeatITCopilotPanel.tsx:182-190`](../../web/components/assistant/BeatITCopilotPanel.tsx#L182-L190));
  CareGuard inline-styled inputs do not define a focus-visible style
  ([`CareGuardRunner.tsx:116-138`](../../web/components/careguard/runner/CareGuardRunner.tsx#L116-L138)).
  Confirm that the browser's default indicator remains visible where the global
  rule is not applied or is overridden.

## Semantic headings, landmarks, and labels

### Positive findings

- The root document has `lang="en"`
  ([`layout.tsx:31-40`](../../web/app/layout.tsx#L31-L40)).
- The CareGuard route pages have a page-level `h1`
  ([`careguard/cases/page.tsx:10-17`](../../web/app/careguard/cases/page.tsx#L10-L17),
  [`careguard/runner/page.tsx:10-17`](../../web/app/careguard/runner/page.tsx#L10-L17)).
- Many nested sections correctly use `aria-labelledby`, and the report,
  comparison, scenario, evidence, and missing-piece surfaces contain useful
  `h2`/`h3`/`h4` structure.
- Several complex visual surfaces have text alternatives: PV SVGs use
  `role="img"` and an `aria-label`
  ([`SplitHeartComparison.tsx:36-48`](../../web/components/twin/comparison/SplitHeartComparison.tsx#L36-L48)),
  while the causal graph includes a screen-reader-only relationship list
  ([`CausalGraph.tsx:9-32`](../../web/components/twin/scenario/CausalGraph.tsx#L9-L32)).

### Findings

- **The M9 shell has no page-level `h1`.** `AppShell` renders a visual brand
  as `div` elements and the center mode name as a paragraph, then mounts shared
  `PanelHeader` components whose titles are `h2`
  ([`AppShell.tsx:127-177`](../../web/components/layout/AppShell.tsx#L127-L177),
  [`Panel.tsx:58-70`](../../web/components/ui/Panel.tsx#L58-L70)). A screen-reader
  heading navigation on `/` or `/<mode>` therefore starts at `h2` and does not
  identify the current product/page as a top-level heading.
- **Panel landmarks are not named.** The reusable `Panel` emits a bare
  `<section>` while its `h2` has no generated `id` and the section has no
  `aria-labelledby` ([`Panel.tsx:22-37`](../../web/components/ui/Panel.tsx#L22-L37)).
  The right-rail panels consequently rely on their descendants rather than
  exposing consistently named regions.
- **Several form labels rely only on placeholder or adjacent text.** The intake
  notes textarea has no label or `aria-label`
  ([`CaseIntakePanel.tsx:632-649`](../../web/components/intake/CaseIntakePanel.tsx#L632-L649));
  the CareGuard runner's labels have no `htmlFor`/matching `id`
  ([`CareGuardRunner.tsx:115-138`](../../web/components/careguard/runner/CareGuardRunner.tsx#L115-L138));
  the case browser search input is placeholder-only
  ([`CaseBrowser.tsx:41-48`](../../web/components/careguard/cases/CaseBrowser.tsx#L41-L48));
  and the CareGuard copilot input is also placeholder-only
  ([`CareGuardCopilot.tsx:83-90`](../../web/components/careguard/CareGuardCopilot.tsx#L83-L90)).
  The clinical question in the runner is similarly adjacent text without a
  programmatic association.
- **The navigation is a button-driven route switch, not link navigation.** The
  five primary items are native buttons with `aria-current="page"`
  ([`ProductNavigation.tsx:17-24`](../../web/components/product/ProductNavigation.tsx#L17-L24)).
  This is keyboard reachable, but browser link affordances, open-in-new-tab
  behavior, and native navigation semantics are absent. Browser Back/Forward
  behavior is therefore a product-level verification item, not established by
  markup alone.

## Live regions and asynchronous state

### Positive findings

- Timeline cursor changes are announced through a visually hidden polite live
  region ([`Timeline.tsx:222-246`](../../web/components/twin/timeline/Timeline.tsx#L222-L246)).
- Scenario, plausible-twin, Shadow Trial, and Missing Piece status/error paths
  use polite or assertive status regions; Missing Piece also exposes
  `aria-busy` while loading
  ([`MissingPiecePanel.tsx:77-129`](../../web/components/twin/missing-piece/MissingPiecePanel.tsx#L77-L129)).
- The flagged assistant panel exposes its conversation as `role="log"` with
  `aria-live="polite"` and `aria-relevant="additions"`
  ([`BeatITCopilotPanel.tsx:142-177`](../../web/components/assistant/BeatITCopilotPanel.tsx#L142-L177)).
- Intake validation/upload and error messages use `role="alert"`
  ([`CaseIntakePanel.tsx:619-626`](../../web/components/intake/CaseIntakePanel.tsx#L619-L626),
  [`CaseIntakePanel.tsx:740-750`](../../web/components/intake/CaseIntakePanel.tsx#L740-L750)).

### Findings

- **The global run status is not live.** The header status chip changes with
  pipeline state but is a plain `<span>` without `role="status"`,
  `aria-live`, or `aria-atomic`
  ([`AppShell.tsx:144-155`](../../web/components/layout/AppShell.tsx#L144-L155)).
  A screen-reader user may not hear transitions such as “Extracting evidence,”
  “Run complete,” or “Run failed.”
- **Agent trace, evaluation, and Redis telemetry update without an announcement
  contract.** Their changing content is rendered as ordinary lists/chips
  ([`AgentTraceTimeline.tsx:252-310`](../../web/components/trace/AgentTraceTimeline.tsx#L252-L310),
  [`EvalScorecard.tsx:90-169`](../../web/components/eval/EvalScorecard.tsx#L90-L169),
  [`RedisStatsRail.tsx:116-153`](../../web/components/redis/RedisStatsRail.tsx#L116-L153)).
  The visual pulse/spinner is not an AT announcement.
- **CareGuard async states are mostly visual.** Console errors are ordinary
  `div` content, the decision confirmation is an ordinary paragraph, and the
  runner's agent log is a plain `<pre>` without `role="log"` or a status region
  ([`CareGuardConsole.tsx:282-294`](../../web/components/careguard/CareGuardConsole.tsx#L282-L294),
  [`CareGuardRunner.tsx:140-190`](../../web/components/careguard/runner/CareGuardRunner.tsx#L140-L190)).
  CareGuard Copilot's “analyzing…” text and appended answers likewise have no
  live-region semantics ([`CareGuardCopilot.tsx:50-90`](../../web/components/careguard/CareGuardCopilot.tsx#L50-L90)).
- **The third-party CopilotKit chat is not statically auditable from the local
  wrapper.** `CopilotDock` supplies labels and instructions, but the message
  semantics, streaming announcements, focus movement, and error behavior are
  owned by `CopilotChat` and need a browser/AT pass
  ([`CopilotDock.tsx:598-611`](../../web/components/copilot/CopilotDock.tsx#L598-L611)).

## Reduced motion

### Positive findings

- Global CSS shortens all CSS animations and transitions and disables smooth
  scrolling under `prefers-reduced-motion: reduce`
  ([`globals.css:453-465`](../../web/app/globals.css#L453-L465)).
- The heart canvas switches to `frameloop="demand"` and passes
  `animate={!reduce}` when reduced motion is requested
  ([`HeartScene.tsx:843-912`](../../web/components/heart/HeartScene.tsx#L843-L912)).
- Motion-based cards/charts and intake spinners read `useReducedMotion`; the
  standalone hook has pure tests for SSR, missing `matchMedia`, and the media
  query result ([`useReducedMotion.ts:24-68`](../../web/lib/assistant/useReducedMotion.ts#L24-L68)).

### Findings

- **Split Heart continues a frame loop regardless of the preference.** Its
  effect schedules `requestAnimationFrame` on mount and on every tick, while the
  component does not read `useReducedMotion`
  ([`SplitHeartComparison.tsx:51-69`](../../web/components/twin/comparison/SplitHeartComparison.tsx#L51-L69)).
  The comparison clock is initially playing, so reduced-motion users may still
  receive continuous phase updates and visual cursor movement even though the
  nested heart canvases reduce their own animation.
- **Reduced motion is not a complete browser guarantee for third-party or
  non-CSS motion.** CopilotKit's internal transitions and any motion inside
  Plotly/WebGL must be checked in a real browser. The CSS rule also uses a
  `0.001ms` duration rather than removing every animation, so the resulting
  accessibility experience needs visual confirmation.
- The heartbeat/status pulse, skeleton shimmer, and ECG sweep are covered by
  the global media query, but their non-motion replacement is not explicitly
  announced; users should still receive text status for loading/running states.

## Contrast, color, and visual-only status

The source token comments claim approximately WCAG-AA contrast, but a direct
OKLCH-to-sRGB calculation from the values in `globals.css` gives these ratios
against `--ht-surface-1`:

| Token | Ratio | Current use | Finding |
| --- | ---: | --- | --- |
| `--ht-ink` | 15.30:1 | primary text | Passes AA. |
| `--ht-ink-2` | 8.33:1 | secondary text | Passes AA. |
| `--ht-muted` | 4.98:1 | labels and supporting text | Passes the 4.5:1 normal-text target, but many uses are 0.62–0.72rem and need readability testing. |
| `--ht-accent-bright` | 6.30:1 | action/status text | Passes AA. |
| `--ht-signal-bright` | 6.23:1 | action/status text | Passes AA. |
| `--ht-ecg` | 5.12:1 | success text | Passes narrowly. |
| `--ht-warn` | 4.00:1 | warning text and headings | **Fails 4.5:1 for normal text.** |
| `--ht-signal-dim` | 3.24:1 | supporting/icon-adjacent text | Fails normal-text AA; keep decorative or darken. |
| `--ht-faint` | 3.06:1 | origin IDs, units, unavailable/de-emphasized text | Fails normal-text AA; current use includes readable text, not only decoration. |

Concrete affected examples include the hypothetical warning footer and
electrical context in `SplitHeartComparison`, warning headings in
`EvalScorecard`, and `text-faint` origin/provenance text
([`SplitHeartComparison.tsx:83-91`](../../web/components/twin/comparison/SplitHeartComparison.tsx#L83-L91),
[`EvalScorecard.tsx:141-163`](../../web/components/eval/EvalScorecard.tsx#L141-L163)).
Status must not rely on hue alone; the app usually pairs color with text, but
the severity dots and animated pulse still need browser inspection at zoom and
with color-vision simulation.

The CareGuard legacy colors also contain a clear low-contrast use: `#94a3b8`
on white is approximately 2.56:1 and is used for small case metadata and
copilot metadata ([`CaseBrowser.tsx:61-70`](../../web/components/careguard/cases/CaseBrowser.tsx#L61-L70),
[`CareGuardCopilot.tsx:52-70`](../../web/components/careguard/CareGuardCopilot.tsx#L52-L70)).
The CopilotKit theme pair `#fdeef0` on `#e0506b` calculates to approximately
3.38:1 if used as foreground on primary buttons; this needs confirmation and
likely darkening of the primary or lightening of the text
([`CopilotProvider.tsx:27-37`](../../web/components/copilot/CopilotProvider.tsx#L27-L37)).

## Browser and AT limitations

The following are limitations of the current evidence, not claims that the
implementation passes:

- No browser rendered the app for this audit. Existing direct HTTP `200` smoke
  evidence does not establish DOM behavior, WebGL behavior, focus order,
  responsive reflow, or keyboard activation
  ([M5.5 browser QA](./M5_5_BROWSER_QA.md#L66-L83)).
- No screen reader output was captured. The audit cannot confirm how nested
  `aria-label`s, status updates, Plotly, React Three Fiber, or CopilotKit's
  generated DOM are announced in NVDA/Firefox, JAWS/Chrome, or VoiceOver/Safari.
- The repository has no jsdom or Testing Library dependency. Existing focus and
  reduced-motion tests cover pure decisions, not mounted React lifecycle,
  `document.activeElement`, real Tab traversal, or real `MediaQueryList`
  changes ([wave 4 accessibility notes](../assistant/wave4/chat-accessibility.md#L298-L307)).
- The current environment lacks a configured axe/Playwright browser test
  suite, so no automated WCAG scan or computed-style contrast result has been
  collected. The ratios above are source-token calculations and should be
  rechecked against actual composited backgrounds.
- WebGL and Plotly require a browser-capable environment for meaningful
  testing. A static `aria-label` on a canvas or SVG does not prove that the
  interactive visual model is operable or perceivable.

## Required verification before M9 accessibility sign-off

1. In a browser with Chromium and Firefox available, run the five-space journey
   at narrow and wide widths using keyboard only. Record Tab/Shift+Tab order,
   trigger-to-dialog focus movement, Escape behavior, focus restoration, and
   browser Back/Forward.
2. Test the disclaimer, product drawer, synthetic-vitals dialog, Cardiology
   Copilot, CareGuard Copilot, component inspector, and component report as
   independent dialog/overlay cases. Confirm background controls cannot receive
   focus while modal content is open.
3. Add a keyboard-accessible anatomy list or equivalent semantic control path;
   then verify that every selection available in the 3D heart can be reached
   without a pointer and that the selected report is announced.
4. Verify all loading, completion, error, trace, Redis, CareGuard, and Copilot
   updates with a screen reader. Add live-region semantics where the current
   source findings above identify ordinary text only.
5. Test `prefers-reduced-motion` in OS/browser settings, including the Split
   Heart clock, WebGL beat, CSS pulses, charts, drawers, and CopilotKit chat.
6. Recheck contrast at actual rendered states, especially amber/faint tokens,
   CareGuard metadata, disabled controls, focus outlines, and CopilotKit
   buttons. Do not close the browser blocker based only on TypeScript, lint, or
   an HTTP response.

## Audit boundary

This file is documentation only. No production code, tests, configuration, or
other documentation files were changed as part of this audit.
