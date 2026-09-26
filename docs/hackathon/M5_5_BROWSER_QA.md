# M5.5 Browser and Accessibility QA

## Verdict

**Browser QA: BLOCKED — no browser pass claimed.**

The local Next.js app served HTML successfully, but no Playwright browser could
complete a launch in this environment. Chromium exits before page navigation
because `libasound.so.2` is unavailable. The Playwright CLI also expects a
Firefox build that is not installed. No screenshot, DOM accessibility tree,
keyboard traversal, or browser-based axe scan was obtained.

M6, M7, and M8 were not started.

## Environment evidence

Collected 2026-09-26 in `/home/923873155/BeatIT`:

| Check | Result |
|---|---|
| Node | `v22.22.2` |
| pnpm | `11.23.0` |
| Playwright CLI | `/home/923873155/.local/bin/playwright`, version `1.63.0` |
| Chromium executable | Cached at `/home/923873155/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome` and headless shell present |
| Firefox executable | Playwright-required `firefox-1543` absent; older `firefox-1538` exists but also fails dependency loading |
| `libasound.so.2` | Absent; `ldd` reports `libasound.so.2 => not found` |
| `web/node_modules/playwright` | Absent |
| `web/node_modules/@playwright/test` | Absent |
| `web/node_modules/axe-core` | Absent |
| Browser test config | No Playwright/Cypress browser test configuration found |

The Playwright browser commands attempted were:

```text
playwright screenshot --browser=chromium --wait-for-timeout=1000 \
  http://127.0.0.1:3000 /tmp/beatit-home.png
```

Result: exit `1`; the cached Chromium headless shell exited with:

```text
error while loading shared libraries: libasound.so.2: cannot open shared object file: No such file or directory
```

```text
playwright screenshot --browser=firefox --wait-for-timeout=1000 \
  http://127.0.0.1:3000 /tmp/beatit-home-firefox.png
```

Result: exit `1`; Playwright reported that
`/home/923873155/.cache/ms-playwright/firefox-1543/firefox/firefox` does not
exist and recommended `playwright install`.

## Local flow attempt

The normal command was attempted first:

```text
pnpm -C web dev --hostname 127.0.0.1
```

It did not start because pnpm stopped on its ignored-build-scripts policy with
`ERR_PNPM_IGNORED_BUILDS` for `@scarf/scarf`, `es5-ext`, `sharp`, and
`unrs-resolver`.

To separate that bootstrap issue from the app itself, the installed Next binary
was run directly:

```text
cd web
./node_modules/.bin/next dev --hostname 127.0.0.1 --port 3000
```

Next.js 16.2.7 reported `Ready` at `http://127.0.0.1:3000`. HTTP probes then
returned:

```text
GET /                     -> 200 text/html; charset=utf-8, 98670 bytes
GET /does-not-exist       -> 404
```

These probes establish server response only; they do not establish that the UI
renders or that interactions work in a browser.

## Static keyboard and accessibility review

This is source inspection only because browser execution was unavailable.

### Findings requiring follow-up before browser sign-off

1. **Modal focus management is not implemented.**

   `DisclaimerModal` declares `role="dialog"` and `aria-modal="true"`, but
   does not move focus into the dialog, trap `Tab`/`Shift+Tab`, close on
   `Escape`, or restore focus after dismissal
   ([`DisclaimerModal.tsx:25-75`](../../web/components/safety/DisclaimerModal.tsx)).
   The synthetic-vitals dialog has the same pattern and has only Cancel/Generate
   actions ([`CaseIntakePanel.tsx:780-817`](../../web/components/intake/CaseIntakePanel.tsx)).
   The active Copilot dialog also has no focus return/trap handling
   ([`CopilotDock.tsx:563-615`](../../web/components/copilot/CopilotDock.tsx)).

2. **The cardiac view tabs are only partially wired to the ARIA tabs pattern.**

   The tab buttons expose `role="tab"` and `aria-selected`, but do not expose
   `aria-controls`; the rendered tab panels do not expose `role="tabpanel"`, an
   associated `aria-labelledby`, or an explicit tab-panel focus target. There is
   also no ArrowLeft/ArrowRight/Home/End handling or roving `tabIndex`
   ([`AppShell.tsx:135-169`](../../web/components/layout/AppShell.tsx)).

3. **The custom upload dropzone needs browser verification.**

   It correctly exposes `role="button"`, `tabIndex={0}`, an accessible name, and
   Enter/Space activation ([`CaseIntakePanel.tsx:514-525`](../../web/components/intake/CaseIntakePanel.tsx)).
   Because it is a custom `div`, its disabled state is conveyed with
   `aria-disabled` rather than native button behavior; keyboard and screen-reader
   behavior should be verified once a browser is available.

### Positive static evidence

- The root document sets `lang="en"` ([`web/app/layout.tsx:32-40`](../../web/app/layout.tsx)).
- Vital inputs use explicit `<label htmlFor>`, `aria-invalid`, and conditional
  `aria-describedby` for validation errors
  ([`CaseIntakePanel.tsx:842-861`](../../web/components/intake/CaseIntakePanel.tsx)).
- Pipeline and ensemble status/error messages use `role="status"` or
  `role="alert"` with live-region behavior.
- Visible focus styling is defined with `:focus-visible`; reduced-motion support
  exists in the stylesheet and motion components.
- Copilot open/close controls have accessible names and `aria-expanded`; the
  plausible-twin selector and sample buttons expose labels/pressed state.

## Non-browser validation

These checks passed, but are not substitutes for browser QA:

```text
node --experimental-strip-types --loader ./web/tests/alias-loader.mjs \
  --test ./web/tests/m5-runtime.test.ts
2 passed, 0 failed

web/node_modules/.bin/tsc --noEmit -p web/tsconfig.json
passed

cd web && ./node_modules/.bin/eslint \
  components/layout/AppShell.tsx \
  components/safety/DisclaimerModal.tsx \
  components/intake/CaseIntakePanel.tsx \
  components/copilot/CopilotDock.tsx \
  components/twin/ensemble/PlausibleTwinsPanel.tsx
passed
```

## Exact files changed by this QA task

- `docs/hackathon/M5_5_BROWSER_QA.md` — this evidence record only.

No production code, tests, formulas, or M6/M7/M8 files were changed.

## Re-run when browser dependencies are available

Install system audio/browser dependencies and the project browser runner, then
repeat the screenshot/navigation flow and add actual keyboard and accessibility
tree results. A browser pass must include the disclaimer dismissal, tab changes,
upload-dropzone keyboard activation, Copilot open/close, and plausible-twin
controls. Until then, M5.5 browser QA remains **incomplete**.
