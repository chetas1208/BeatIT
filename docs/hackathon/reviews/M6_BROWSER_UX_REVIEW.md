# M6 Browser and UX Review

Date: 2026-09-26  
Scope: M6 Shadow Trial frontend surface, local HTTP serving, browser tooling,
and source-level UX/accessibility states. No implementation files were changed.
M7 Split Heart and M8 Missing Piece are out of scope.

## Verdict

**Browser sign-off: BLOCKED.** The Next.js application serves successfully over
HTTP, but a real browser session cannot launch in this environment. Therefore
there is no claimed screenshot, DOM accessibility tree, keyboard traversal,
focus validation, or browser-based axe result.

The M6 surface is statically reviewable and has explicit idle, loading,
request-error, completed, failed/zero-valid, invalid-pair, provenance, and PV
boundary states. Those states still require a real browser pass before the M6
frontend gate can be called complete.

## Environment evidence

Checks were run from `/home/923873155/BeatIT` on 2026-09-26:

| Check | Result |
|---|---|
| Node | `v22.22.2` |
| pnpm | `11.23.0` |
| Next.js | `16.2.7` |
| Playwright CLI | `/home/923873155/.local/bin/playwright`, version `1.63.0` |
| Chromium | Cached executable and headless shell present |
| Firefox | Older cached `firefox-1538` present; Playwright-required `firefox-1543` absent |
| Project browser package | `playwright`, `@playwright/test`, `puppeteer`, and `cypress` not installed in `web` |
| axe | `axe-core` not installed |
| Browser configuration | No Playwright or Cypress config found |

The exact Chromium attempt was:

```text
/home/923873155/.local/bin/playwright screenshot \
  --browser=chromium --wait-for-timeout=1000 \
  http://127.0.0.1:3100 /tmp/beatit-m6-shadow-trial.png
```

It failed before navigation because the cached headless shell could not load
`libasound.so.2`:

```text
error while loading shared libraries: libasound.so.2: cannot open shared object file: No such file or directory
```

`ldd` reports the same missing library for the cached Chromium binary. This is
an environment dependency failure, not evidence that the page or M6 controls
render correctly in a browser.

## Direct HTTP versus real browser

The installed Next binary was run directly because the normal package-manager
bootstrap can apply ignored-build-script policy to optional packages:

```text
cd web
./node_modules/.bin/next dev --hostname 127.0.0.1 --port 3100
```

The server reported ready, and direct probes returned:

```text
GET /                 -> 200 text/html; charset=utf-8; 98670 bytes
GET /does-not-exist   -> 404 text/html; charset=utf-8; 33548 bytes
```

The direct HTTP result proves only that Next.js emitted responses. It does not
prove hydration, the Shadow Trial interaction, responsive layout, focus order,
keyboard behavior, WebGL behavior, live-region announcements, or accessibility
tree correctness.

## M6 UX state review

Source reviewed: `web/components/twin/shadow-trial/ShadowTrialPanel.tsx`,
`web/components/twin/scenario/ScenarioPanel.tsx`,
`web/lib/api.ts`, and `web/types/shadow-trial.ts`.

| State | Current source evidence | Review result |
|---|---|---|
| No usable baseline/scenario | Scenario panel says to select an observed snapshot; Shadow Trial status asks the user to generate twins and run the experiment | Present; browser visibility unverified |
| Ready | Native `Run Shadow Trial` button is disabled until an ensemble exists | Present; keyboard/focus behavior unverified |
| Loading | Button becomes disabled and changes to `Running Shadow Trial…` | Present; timing and announcement unverified |
| Request error | Error text is placed in a polite live region with `role="alert"` | Present; backend error rendering unverified |
| Completed result | Counts, effect distributions, paired inspector, provenance, safety text, and PV boundary are rendered | Present; layout and overflow unverified |
| Failed/zero valid pairs | Alert says no valid paired outcomes are available; retained invalid pairs remain inspectable | Present; empty-result visual behavior unverified |
| Invalid selected pair | Scalar comparison is withheld and rejection reasons use an alert | Present; screen-reader and selection behavior unverified |
| Empty pair list | Inspector returns no content; the result surface still shows the distribution fallback | Needs browser verification and explicit product decision for a completely empty pair collection |
| Persistence/reload | Client exposes GET methods, but this panel creates a trial and does not restore one after a reload | Known UX limitation; no browser persistence test possible |

The panel keeps the single-heart boundary: it provides scalar baseline/scenario
inspection and does not add a second canvas, split viewport, or missing-piece
workflow. It also displays hypothetical/synthetic and non-clinical warnings.

## Static accessibility evidence

Positive source evidence:

- Native `button`, `select`, `label`, and `details` elements are used for the
  primary controls and disclosure.
- Request status is a live region; request failures and invalid-pair reasons
  use `role="alert"`.
- The paired inspector has a heading referenced by `aria-labelledby`.
- The distribution list has an accessible label, while the decorative range
  bar is marked `aria-hidden`.
- The page-level app already sets document language and shared focus-visible
  styles, as recorded in the M5.5 browser audit.

Not verifiable without a browser:

- Focus placement and focus return after the result replaces the idle state.
- Keyboard traversal and select behavior for the paired inspector.
- Whether tiny status/distribution text has sufficient contrast and readable
  scaling at narrow viewport sizes.
- Live-region announcement timing while the request is in flight.
- Hydration warnings, responsive overflow, and any WebGL/runtime interaction.
- Automated axe findings or an accessibility tree snapshot.

## Required follow-up before browser sign-off

Install a compatible browser runtime and its system dependencies, then run a
real browser pass covering:

1. idle state with no snapshot, disabled/enabled run control, and visible focus;
2. loading state and live status announcement;
3. successful result with distribution cards, pair selection, provenance, and
   safety boundary;
4. failed request, zero-valid result, invalid-pair selection, and empty result;
5. changing the scenario after a result, including stale-result behavior;
6. narrow/mobile viewport, keyboard-only navigation, reduced motion, and a
   browser accessibility scan.

Until those checks run, retain this review as **BLOCKED — HTTP verified, real
browser unavailable**. No M7 or M8 work is implied by this blocker.
