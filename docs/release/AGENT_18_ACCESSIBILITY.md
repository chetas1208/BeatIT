# Agent 18 — Accessibility E2E Verification

**Audit date:** 2026-09-26 UTC
**Scope:** frozen five-space product: Twin, Experiment, Compare, Evidence, and
Report, including shared shell, dialogs, assistant surfaces, timelines,
scenario controls, Split Heart, and the WebGL heart surface.
**Change boundary:** this contribution added only this document. No production,
test, fixture, or configuration files were modified.

## Executive result

**CONDITIONAL STATIC PASS; E2E ACCESSIBILITY SIGN-OFF BLOCKED.**

The available non-browser checks pass for the focus-trap and reduced-motion
primitives, TypeScript, scoped lint, and product navigation/report contracts.
Real keyboard traversal, focus restoration, accessibility-tree inspection,
screen-reader behavior, contrast, and axe scanning could not run because the
available browser runtime cannot launch in this environment. No browser or axe
success is claimed.

## Checks executed

All commands below were run from `/home/923873155/BeatIT/web` unless noted.

| Check | Command | Result |
| --- | --- | --- |
| TypeScript | `./node_modules/.bin/tsc --noEmit -p tsconfig.json` | **PASS** |
| Scoped frontend lint | `./node_modules/.bin/eslint components/product/ProductNavigation.tsx components/layout/AppShell.tsx components/twin/comparison/SplitHeartComparison.tsx components/heart/interaction/SemanticPickLayer.tsx components/safety/DisclaimerModal.tsx components/copilot/CopilotDock.tsx lib/assistant/useReducedMotion.ts lib/assistant/useFocusTrap.ts` | **PASS** |
| Focus and reduced-motion unit checks | `node --experimental-strip-types --loader ./tests/alias-loader.mjs --test ./lib/assistant/__tests__/useReducedMotion.test.ts ./lib/assistant/__tests__/useFocusTrap.test.ts` | **12 passed, 0 failed** |
| Frozen product runtime checks | `node --experimental-strip-types --loader ./tests/alias-loader.mjs --test ./lib/product/__tests__/navigation.test.ts ./lib/product/__tests__/reportContracts.test.ts` | **3 passed, 0 failed** |
| Package runtime wrapper | `pnpm -C web test:runtime` | **BLOCKED before test execution** |

The package wrapper attempted an install and stopped with
`ERR_PNPM_IGNORED_BUILDS` for `@scarf/scarf`, `es5-ext`, `sharp`, and
`unrs-resolver`. The direct Node test command above ran successfully and is the
authoritative result for these checks in this environment.

## Browser and axe availability

| Capability | Observed result |
| --- | --- |
| Playwright CLI | Present, version `1.63.0` |
| Chromium executable on `PATH` | Absent |
| Cached Chromium headless shell | Present, launch fails because `libasound.so.2` is unavailable |
| Firefox executable on `PATH` | Absent |
| Playwright Firefox build | Missing (`firefox-1543`) |
| `axe-core` in installed `node_modules` | Absent |
| `@axe-core/playwright`, `pa11y`, Puppeteer, Cypress | Absent |
| `axe-core` in lockfile | Referenced, not installed |

Direct probes used `playwright screenshot --browser=chromium ...` and
`playwright screenshot --browser=firefox ...` against `about:blank`. Chromium
exited with:

```text
error while loading shared libraries: libasound.so.2:
cannot open shared object file: No such file or directory
```

Firefox reported that the Playwright-required executable does not exist. As a
result, there is no rendered DOM, accessibility tree, keyboard session,
reduced-motion browser session, screenshot, or axe report attached to this
verification.

## Static/source observations

Positive evidence verified by source inspection and the passing checks:

- `web/app/layout.tsx` declares `lang="en"`.
- `web/app/globals.css` provides `:focus-visible` styling and a
  `prefers-reduced-motion: reduce` rule.
- `web/lib/assistant/useFocusTrap.ts` covers initial focus, Tab and
  Shift+Tab wrapping, Escape, and focus restoration at the pure-logic level.
- `web/lib/assistant/useReducedMotion.ts` handles SSR, missing `matchMedia`,
  matching media queries, and thrown media-query access.
- Product navigation and report contracts pass their direct runtime tests.

Open source risks remain and require browser confirmation or an explicitly
authorized remediation:

1. `DisclaimerModal.tsx`, `CaseIntakePanel.tsx`,
   `ComponentReportPanel.tsx`, and `CopilotDock.tsx` expose dialog roles, but
   do not all use the shared `useFocusTrap` lifecycle. Initial focus, Tab
   containment, Escape, and focus return are therefore not verified uniformly.
2. `SplitHeartComparison.tsx` schedules an unconditional
   `requestAnimationFrame` loop and does not consume `useReducedMotion`.
   CSS reduced-motion rules alone do not prove that this JavaScript clock
   pauses or becomes static.
3. `SemanticPickLayer.tsx` exposes pointer handlers for anatomy selection. A
   keyboard-accessible equivalent for selecting anatomy in the WebGL surface
   is not established by the available checks.
4. Asynchronous shell, trace, evaluation, and telemetry updates need a real
   DOM check to confirm appropriate live-region behavior without excessive
   announcements.

These observations are consistent with the broader M10 accessibility review
in [`M10_ACCESSIBILITY.md`](../hackathon/M10_ACCESSIBILITY.md), but this agent
does not convert them into browser findings because the browser could not
launch.

## Required unblocked E2E run

After installing a compatible browser runtime and an axe runner, execute the
production build or local Next server and verify:

1. Dialog initial focus, Tab/Shift+Tab containment, Escape, backdrop close, and
   focus restoration for the disclaimer, product drawer, Copilot, report, and
   synthetic-vitals surfaces.
2. Keyboard-only navigation across all five product spaces, including reload
   and browser Back/Forward.
3. Enter/Space activation and validation announcements for intake upload and
   other custom controls.
4. `prefers-reduced-motion: reduce` behavior for Split Heart, the heart scene,
   charts, playback, loading states, and Copilot transitions.
5. A keyboard-accessible alternative to every interactive anatomy selection,
   plus the WebGL-unavailable fallback.
6. Live-region announcements for pipeline, trace, evaluation, error, and
   Redis updates.
7. Accessibility-tree snapshots and axe scans for `/`, `/twin`,
   `/experiment`, `/compare`, `/evidence`, `/report`, and applicable CareGuard
   routes.

## Release disposition

**OPEN — DO NOT MARK ACCESSIBILITY E2E COMPLETE.**

The frozen product has passing static and pure-logic accessibility checks, but
the browser, accessibility-tree, keyboard, assistive-technology, reduced-motion
runtime, and axe gates remain unverified. The release must retain the
synthetic/educational boundary and must not claim accessibility sign-off until
the browser blockers are removed and the required E2E checks are rerun.
