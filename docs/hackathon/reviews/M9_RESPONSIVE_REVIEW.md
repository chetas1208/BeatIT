# M9 Responsive Review

Date: 2026-09-26  
Scope: shell/grid/navigation/drawer, heart viewport and overlays, Compare
surface, and table behavior at narrow and wide viewports. Read-only source
review; no production or test files were changed.

## Verdict

**CONDITIONAL PASS — the responsive structure is intentional and has sensible
overflow fallbacks, but browser evidence is still required before responsive
sign-off.**

The shell uses a stacked flow below the `lg` breakpoint and a fixed-height
three-column workspace at `lg` and above. Navigation can scroll horizontally,
the product drawer is width-bounded, Compare collapses its two hearts below
`lg`, and the reviewed tables expose horizontal scrolling. The principal risks
are nested scroll containers, content competing with fixed-height WebGL
viewports, dense controls at 360px, and overlays whose usable interaction area
must be checked on real devices.

## Source-level findings

### RSP-1 — Wide shell has multiple independent vertical scroll owners — P1

**Open for browser validation.** At `lg`, the root is `h-[100dvh]`
with `overflow-hidden`; `main` is also `lg:overflow-hidden`, while the product
surface, every `PanelBody`, and several detail surfaces scroll independently
(`web/components/layout/AppShell.tsx:189-226`,
`web/components/layout/AppShell.tsx:109`, `web/components/ui/Panel.tsx:79-89`).
This is a valid dashboard pattern, but it is sensitive to browser viewport
height, mobile browser chrome, zoom, and nested wheel/touch gestures. A panel
can appear clipped if a child does not receive the expected `min-h-0` chain,
and keyboard users can lose the visual context of the active header while a
different inner region scrolls.

Check at wide viewports with short heights as well as wide widths: 1024x600,
1280x720, and 1440x900. Confirm that intake, product content, trace/evaluation,
and Redis each have a reachable end; wheel, trackpad, touchpad, Page Down, and
keyboard focus should scroll the intended owner without page-level dead zones.

### RSP-2 — Narrow layout stacks large panels but has no explicit height budget — P1

**Open for browser validation.** Below `lg`, all three grid regions become
`col-span-12` and the shell returns to document scrolling
(`web/components/layout/AppShell.tsx:225-241`). The Twin heart still contains a
`min-h-[18rem]` canvas, and Experiment/Evidence/Report add further
`min-h`/`max-h` constraints (`web/components/layout/AppShell.tsx:116-132`).
At 360px this can produce a long page with a large first visual followed by
intake and observability content; that is acceptable only if order, headings,
and the active surface remain obvious and no fixed-height child clips content.

The browser gate must exercise 360x800 and 390x844 with a cold load, a complete
case, an error state, and an empty Compare state. Record document height,
whether every panel can be reached, and whether focusing a lower control causes
the correct ancestor to scroll into view.

### RSP-3 — Shell breakpoint transition is abrupt at the Tailwind `lg` boundary — P2

**Source risk.** The layout changes from one-column document flow to a fixed
three-column viewport at `lg` (`web/components/layout/AppShell.tsx:189,
225-241`). There is no intermediate tablet layout. At widths just below and
above the breakpoint, the same content changes from stacked reading order to
three narrow rails, while Compare changes from stacked hearts to side-by-side
hearts at the same breakpoint (`web/components/twin/comparison/SplitHeartComparison.tsx:85`).

Verify 767px, 1023px, 1024px, and 1280px widths. Resize while a panel is open,
while a comparison is selected, and while a table is horizontally scrolled.
The selected mode, scroll position that should persist, drawer state, and
comparison pair must not be lost or rendered behind a newly constrained rail.

### RSP-4 — Primary nav has a narrow-width fallback, but the fallback competes with five buttons — P2

**Pass with browser check.** The nav uses `overflow-x-auto`; all buttons are
`shrink-0`, so labels should remain intact rather than wrap or compress
(`web/components/product/ProductNavigation.tsx:47-55`). This is preferable to
wrapping a second navigation row, but the active item may be off-screen after
route changes because the implementation does not scroll the active button into
view.

At 320px, 360px, and 390px confirm that the menu trigger and active space are
visible, the nav can be swiped/shift-scrolled, the scrollbar does not obscure
the focus ring, and selecting each space does not leave the active item hidden.
Confirm browser Back/Forward also updates the active item at every width.

### RSP-5 — Drawer geometry is appropriate for a sheet, but its content is not independently scrollable — P1

**Open.** The drawer is `h-full` and width-bounded to `min(22rem, 88vw)` but
does not declare `overflow-y-auto` (`web/components/product/ProductNavigation.tsx:57-74`).
The current five-item menu fits in normal conditions, yet text scaling, browser
zoom, short landscape viewports, or future longer descriptions can push the
bottom action below the viewport. Body scrolling is disabled while it is open,
so an over-height drawer has no reliable recovery path.

Browser-check 360x640, 360x800, 844x390 landscape, 200% text/zoom, and keyboard
navigation. The close and Return controls must remain reachable, the sheet must
not create horizontal overflow, outside click must be limited to the scrim, and
Escape/Tab behavior must match the M9 interaction contract. Source already
focuses the close button, wraps Tab inside the drawer, restores body overflow,
and attempts to refocus the trigger (`ProductNavigation.tsx:19-43`); the
browser pass must confirm that this remains true after route selection and
outside-click close.

### RSP-6 — Heart overlays can consume most of a narrow viewport — P1

**Open.** The main findings overlay uses `w-[58%]`, `max-w-[300px]`, a capped
height, and its own vertical scroll inside the canvas
(`web/components/heart/HeartScene.tsx:1129-1137`). The component inspector uses
`w-[min(23rem,92%)]` and also scrolls independently
(`web/components/heart/inspector/ComponentInspector.tsx:84-97`). These are
reasonable desktop overlays, but at 320–360px they can leave only a thin heart
interaction region or obscure labels, close controls, and canvas affordances.

With findings present, select anatomy, open the inspector, and open the report
at 360px portrait and landscape. Confirm the overlay's close control remains
visible, text does not clip, the canvas is not the only way to discover or
dismiss the overlay, and touch scrolling inside the overlay does not move the
underlying page or heart surface.

### RSP-7 — WebGL sizing and animation are browser-gated, especially in Compare — P1

**Open.** The canvas uses `dpr={[1, 2]}`, `preserveDrawingBuffer`, and an
always-running frameloop unless reduced motion is detected
(`web/components/heart/HeartScene.tsx:892-903`). Compare fixes each heart host
to `h-[22rem]` and renders two instances side-by-side at `lg`, stacked below it
(`web/components/twin/comparison/SplitHeartComparison.tsx:85`). This can be
expensive on high-density wide displays and can dominate the first screen on
narrow devices.

Run a real browser with WebGL enabled and disabled/failing. At 360px, wide
desktop, reduced-motion, and a short viewport, confirm the fallback is readable,
canvas dimensions track their containers, both Compare hearts render without
clipping, and there is no sustained layout shift or unusable frame rate. Check
that `prefers-reduced-motion: reduce` stops visual animation in both the single
heart and comparison clocks; the comparison component has an unconditional
`requestAnimationFrame` loop (`SplitHeartComparison.tsx:64-70`) and therefore
needs explicit browser verification even when the canvas respects reduced
motion.

### RSP-8 — Tables correctly preserve columns through horizontal scrolling, but the scroll affordance is implicit — P2

**Pass at source level; browser check required.** Comparison metrics set
`min-w-[40rem]` inside `overflow-x-auto`
(`web/components/twin/comparison/ComparisonMetrics.tsx:109-112`). Scenario and
Missing Piece tables use the same pattern with `42rem`
(`web/components/twin/scenario/ScenarioInspector.tsx:69-73`,
`web/components/twin/missing-piece/SensitivityTable.tsx:28-35`). This avoids
illegible squeezed columns and retains semantic table markup, but at 360px the
right-side columns are intentionally off-screen and there is no visible cue
that more content exists.

At 360px, verify that a touch swipe or Shift+wheel moves the table, the focused
cell/control is not stranded outside the viewport, sticky browser focus rings
remain visible, and the table does not expand the shell width. Check long
metric/provenance text, unavailable values, empty rows, and 200% zoom. A visible
horizontal-scroll cue would be a UX improvement if the browser pass shows the
overflow is undiscoverable.

## Browser-gated matrix

| Area | Narrow checks | Wide checks | Evidence to record |
|---|---|---|---|
| Shell/grid | 320x800, 360x800, 390x844; portrait and landscape | 1024x600, 1280x720, 1440x900 | screenshots plus scroll-owner notes; no clipped panel or page dead zone |
| Navigation | nav swipe, active item visibility, route changes | active state, resize across `lg` | keyboard focus, Back/Forward, active route at each width |
| Drawer | 360x640, short landscape, 200% zoom | normal and short-height desktop | focus entry/trap/restore, Escape, scrim close, internal reachability |
| Heart | idle, live, findings, inspector, report, WebGL failure | same states with high-DPR display | canvas bounds, overlay reachability, fallback, console errors |
| Compare | stacked hearts, controls wrapping, metrics/table scroll | side-by-side hearts, PV grids, rail height | no clipping; clock controls and both hearts remain usable |
| Tables | 40–42rem content scrolls without shell expansion | full table readability and no unnecessary scroll | headers/rows, unavailable and empty states, keyboard/touch scroll |

## Release recommendation

Keep the responsive implementation available for continued M9 work, but do not
claim responsive/browser completion until the matrix above is run in a real
browser. The highest-priority checks are RSP-1, RSP-2, RSP-5, RSP-6, and RSP-7.
The existing M9 QA record notes that the current environment lacks a launchable
Chromium audio library and Firefox, so automated TypeScript/build checks cannot
substitute for this evidence.
