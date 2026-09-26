# M9 Performance Audit

**Status:** audit and performance contract; no runtime measurements are claimed
here.

**Scope:** the Next.js frontend, the `HeartScene` renderer, the five product
spaces, the CareGuard routes, and the browser evidence needed before making a
performance claim.

This document deliberately separates observed implementation facts from proposed
acceptance budgets. No frame rate, memory value, bundle size, Web Vital, GPU
capability, or hosted-capacity result is recorded as measured evidence unless a
future run retains the command output and environment details.

## Audit basis and evidence boundary

This is a source audit. It records the route entries, import boundaries, render
loops, resource ownership, and fallback code visible in the checked-out files.
No build, browser trace, Web Vital, frame-time, heap, GPU, transfer-size, or
hosted-capacity measurement is recorded here. The route table below is an
expected source route matrix, not proof that the routes built or rendered.

Run the build and browser commands in the evidence section on the exact
revision, environment, and device under review before recording any measured
result or declaring a budget passed.

## Route and loading audit

| Route or space | Current entry | Expected rendering load | Performance boundary |
|---|---|---|---|
| `/` | `web/app/page.tsx` → `AppShell` | Defaults to the Twin shell; the shell includes the cardiac viewport and right/left rails. | Treat as the Twin baseline. Do not use the root page as evidence for a non-3D route. |
| `/twin` | `web/app/[mode]/page.tsx` with `mode=twin` | `AppShell` renders `HeartScene`. | Measure first load, idle viewport, live case, and route return. |
| `/experiment` | `[mode]` → `AppShell` | `ScenarioPanel`; the heart is not rendered by the selected branch. | Verify that 3D dependencies are not fetched or initialized merely because the shared client shell imports them. |
| `/compare` | `[mode]` → `AppShell` | `SplitHeartComparison`, which mounts two `HeartTwinInstance` views. | Highest GPU/render case. Measure independently from Twin. |
| `/evidence` | `[mode]` → `AppShell` | `PlausibleTwinsPanel` and Missing Piece surfaces. | No canvas should be mounted for the selected surface. |
| `/report` | `[mode]` → `AppShell` | `ReportSurface`; the Copilot dock is suppressed by the current shell branch. | Verify that report navigation does not retain an active animation loop. |
| `/careguard` | `web/app/careguard/page.tsx` | `CareGuardConsole`, outside the product-space shell. | No 3D scene is expected. Measure as a separate route. |
| `/careguard/cases` | `web/app/careguard/cases/page.tsx` | Case browser. | No 3D scene is expected; large case data must not be loaded before needed. |
| `/careguard/runner` | `web/app/careguard/runner/page.tsx` | Case runner/import surface. | No 3D scene is expected; upload and validation work must remain responsive. |

Product-space navigation currently uses `history.pushState` in
`web/lib/product/navigation.ts:16-20`, while `AppShell` keeps the same client
shell and switches the center branch (`web/components/layout/AppShell.tsx:159-212`).
This preserves the mounted session, but a URL alone does not prove a new route
request, route-level code splitting, or disposal of the previous surface. The
static imports at `web/components/layout/AppShell.tsx:20-39` are a client-entry
bundle hotspot: HeartScene, Compare, Experiment, Evidence, and Report code are
all candidates for the shared shell transfer and must be checked in the
generated chunk graph and browser network log.

The Copilot provider is mounted in the root layout
(`web/app/layout.tsx:34-45`) and imports the Copilot UI stylesheet at module
scope (`web/components/copilot/CopilotProvider.tsx:15-16`). The Copilot runtime
is a separate server route at `/api/copilotkit`. The browser audit must report
whether Copilot client code and stylesheet work are part of the initial route
transfer even when the dock is closed.

## HeartScene render audit

Source-backed hotspots in `web/components/heart/HeartScene.tsx`:

| Location | Current behavior | Why it is a hotspot |
|---|---|---|
| `120-148` | Builds an `IcosahedronGeometry` with subdivision `24` and warps every vertex. | High vertex count is paid during scene construction and every independently mounted heart owns its render resources. |
| `399-489` | Renders the heart body and a second glow-shell mesh over the same geometry, with two shader materials. | Two passes increase vertex/fragment work and additive blending can increase overdraw. |
| `425-482` | `HeartBody` updates uniforms, smoothing, transforms, and glow state in `useFrame`. | Continuous work is correctly kept out of React state, but remains per active canvas. |
| `514-643` | Creates `PARTICLE_COUNT = 520`; rewrites all particle positions and marks the buffer dirty on every animated frame. | CPU trigonometry plus a full dynamic buffer upload is a predictable steady-state cost. |
| `649-693` | Camera/parallax and focus pose are updated in `useFrame`. | Adds another per-frame path and can remain active while focus motion is settling. |
| `748-797` | Each anchored finding adds a mesh and a Drei `Html` marker. | DOM overlays and projection work grow with finding count; no explicit display cap is visible in this component. |
| `801-835` | Composes clock driver, camera rig, body, flow, electrical layer, picking layer, and markers. | The complete layer stack is active in each mounted canvas. |
| `893-923` | Uses `dpr={[1, 2]}`, antialiasing, alpha, `powerPreference: "high-performance"`, and `preserveDrawingBuffer: true`. | DPR can multiply pixel work; antialiasing and preserved drawing buffers have device-dependent cost. Each option needs evidence before being retained for every device class. |
| `902` | Uses `frameloop="always"` unless reduced motion is requested. | The normal scene continuously renders even when the case is idle unless a future policy pauses it. |
| `928-931` | Wraps the Canvas component with `next/dynamic({ ssr: false })`. | This is an SSR/hydration boundary, not proof that Three/R3F are in an isolated network chunk. Verify the output graph. |
| `1039-1047` | Uses `structuredClone` for selected scenario state during `HeartScene` render. | Candidate allocation hotspot during scenario selection or frequent parent updates; profile before changing it. |

Additional scene costs:

- `ElectricalLayer` creates two Drei `Line` paths and one sphere mesh/material
  per electrical node (`web/components/heart/electrical/ElectricalLayer.tsx:19-67`)
  and gives each node its own `useFrame` callback.
- `SemanticPickLayer` creates one transparent pick mesh for each non-functional
  registry component (`web/components/heart/interaction/SemanticPickLayer.tsx:19-21`).
- Finding markers use `Html`, which is DOM work in addition to WebGL work. The
  findings readout is also a potentially long DOM list
  (`HeartScene.tsx:1129-1187`).
- `SplitHeartComparison` owns a browser `requestAnimationFrame` loop that calls
  `setClock` on every tick (`web/components/twin/comparison/SplitHeartComparison.tsx:63-69`)
  and mounts two independent `HeartTwinInstance` canvases
  (`SplitHeartComparison.tsx:85`). This is the primary render-risk path.
- The chart wrapper client-loads `react-plotly.js` and `plotly.js-dist-min`
  (`web/components/charts/Plot.tsx:19-34`). It is a heavy candidate dependency
  and must not be counted as a Twin measurement unless the route actually loads
  it. Confirm all consumers before changing or removing it.

## Proposed performance budgets

These are proposed acceptance thresholds, not current measurements. A budget is
only accepted after the evidence command records the browser, OS, device/GPU,
viewport, DPR, revision, route, fixture, warm-up period, and raw output.

| Area | Proposed budget | Required test cases |
|---|---:|---|
| First Contentful Paint | `≤ 1.8 s` in a controlled lab run | `/twin`, `/experiment`, `/compare`, `/evidence`, `/report`, and each CareGuard route. |
| Largest Contentful Paint | `≤ 2.5 s` in a controlled lab run | Same route matrix; report whether the WebGL canvas or a text panel is the LCP candidate. |
| Interaction to Next Paint | `≤ 200 ms` p75 for primary navigation and controls | Space navigation, intake submit, compare play/pause, scrub, and Copilot open/close. |
| Cumulative Layout Shift | `≤ 0.10` per route load | Cold load and reload at the agreed viewport. |
| Initial application JavaScript | `≤ 350 kB` gzip for `/twin`; `≤ 200 kB` gzip for non-3D spaces | Measure transferred route chunks, excluding browser cache and backend requests; state whether shared chunks are included. |
| 3D dependency isolation | Three/R3F code is absent from non-3D route initial transfer; Plotly is absent unless a chart consumer is mounted | Compare generated chunk graph and browser network log. |
| Single-heart steady state | Frame time `≤ 16.7 ms` median and `≤ 33.3 ms` p95 over a 30-second run | Idle, live case, findings present, and pointer motion. |
| Split-heart steady state | Frame time `≤ 33.3 ms` p95 over a 30-second run | Two active canvases, phase-locked mode, pointer stationary and moving. |
| Main-thread responsiveness | No unexplained task over `100 ms` during steady-state animation; record all tasks over `50 ms` | Single and split heart, plus route transitions. |
| Canvas/resource lifecycle | At most one active canvas in Twin and two in Compare; zero detached canvases after three enter/leave cycles | Twin → Compare → Twin and Twin → Report → Twin. |
| Heap stability | After three mount/unmount cycles, post-GC heap returns within `20%` of the pre-cycle baseline, or the browser's GC limitation is recorded | Chromium with the same tab and fixture; do not infer GPU memory from JS heap. |

The byte, frame, and heap values above are gates to validate, not claims about
the current implementation. If the hardware or browser cannot support a stable
measurement, retain the raw evidence and mark the gate environment-limited
rather than silently changing the threshold.

## Graceful WebGL fallback contract

The current `CanvasFallback` is an initialization placeholder
(`HeartScene.tsx:933-947`), and the surrounding `ErrorBoundary` isolates a
render failure and offers Retry (`web/components/ui/ErrorBoundary.tsx:23-59`).
That is useful containment, but it is not yet a complete capability or context-
loss fallback. The production expectation is:

1. **Capability check:** detect unavailable WebGL before repeatedly attempting
   to mount the full scene. WebGL1/WebGL2 availability, context creation
   failure, blocked GPU acceleration, and browser denial are all unavailable
   states.
2. **Useful fallback:** keep the panel, case identity, safety disclaimer,
   canonical metrics, findings list, provenance, timeline state, and route
   controls available. Replace only the 3D viewport with an accessible static
   cardiac silhouette/diagram or structured text summary. Do not fabricate a
   new physiological value merely because the renderer is unavailable.
3. **Context loss:** stop animation and particle updates, preserve the last
   valid data state, announce that the 3D view is unavailable, and offer one
   explicit retry/reinitialize action. A lost context must not blank the whole
   console or imply that the backend run failed.
4. **Performance fallback:** if a sustained frame-budget breach is detected,
   provide a deterministic lower-cost mode in this order: cap DPR at `1`, pause
   particles and electrical pulses, reduce marker overlays, pause animation, and
   then switch to the static/structured fallback. The user must be able to
   return to the full view deliberately.
5. **Reduced motion:** honor `prefers-reduced-motion` without removing meaning
   or controls. The current demand-loop path (`HeartScene.tsx:844,
   893-911`) must be tested for store updates, timeline changes, and comparison
   controls; no hidden animation loop may continue after the visual motion is
   disabled.
6. **Accessibility:** the fallback has a visible status, an accessible name,
   keyboard-reachable controls, and an `aria-live` announcement for the
   transition. WebGL-only markers, color, motion, or hover affordances cannot be
   the only way to access findings or state.
7. **Privacy and safety:** fallback/error text contains no raw uploaded content,
   secrets, or patient identifiers, and retains the canonical educational/safety
   boundary required by the API and product surfaces.

The fallback is successful only when a user can continue to inspect valid case
state and navigate to another space without a blank viewport, uncaught error,
or false claim that a live visualization is still running.

## Evidence commands

Run from the repository root. Keep raw output with the revision and environment
used for any sign-off.

### Build and route evidence

```bash
# Normal project build gate.
pnpm -C web build

# Diagnostic fallback when pnpm stops at ignored dependency build scripts;
# this bypasses pnpm's install/status wrapper and runs the installed binary.
(cd web && ./node_modules/.bin/next build)

# Type/lint checks for the frontend.
pnpm -C web lint
```

The diagnostic fallback is not a clean-install proof. Resolve the pnpm build
policy for release evidence and retain both the Node/pnpm versions and the
build output.

### Bundle evidence

```bash
# List generated JavaScript chunks by raw byte size.
find web/.next/static/chunks -type f -name '*.js' -printf '%s %p\n' | sort -n

# Report raw, gzip, and (when installed) Brotli sizes for each JavaScript chunk.
while IFS= read -r -d '' file; do
  raw=$(wc -c < "$file")
  gzip_bytes=$(gzip -9 -c "$file" | wc -c)
  if command -v brotli >/dev/null 2>&1; then
    br_bytes=$(brotli -q 11 -c "$file" | wc -c)
  else
    br_bytes="unavailable"
  fi
  printf '%s raw=%s gzip=%s brotli=%s\n' "$file" "$raw" "$gzip_bytes" "$br_bytes"
done < <(find web/.next/static/chunks -type f -name '*.js' -print0)

# Inspect the browser's actual transfer set for each route after a clean build.
pnpm -C web dev
# Then use DevTools Network with Disable cache enabled and save a HAR for:
# /twin, /experiment, /compare, /evidence, /report, /careguard,
# /careguard/cases, and /careguard/runner.
```

The chunk list identifies large outputs but does not map a chunk to a package.
Use the Next/Turbopack analyzer available in the checked-in toolchain, or the
browser Coverage panel, to attribute a large chunk before changing imports.
Do not call a raw `.next` directory size a network bundle size.

### Browser timing and frame evidence

For each route, use a fresh tab with the agreed viewport and record a cold load,
one reload, and a warmed interaction run. In DevTools Console, the following
captures navigation timing and long tasks without adding a dependency:

```js
performance.getEntriesByType("navigation").map((entry) => ({
  name: entry.name,
  duration: entry.duration,
  domContentLoaded: entry.domContentLoadedEventEnd,
  load: entry.loadEventEnd,
  transferSize: entry.transferSize,
}));

performance.getEntriesByType("longtask").map((entry) => ({
  startTime: entry.startTime,
  duration: entry.duration,
}));
```

For render evidence, record a 30-second Performance-panel trace for:

1. `/twin` before a case, after a live case, with findings visible, and with
   pointer movement.
2. `/compare` with two active hearts, phase-locked playback, scrub, and
   difference mode.
3. A route transition from Twin to each non-3D space and back to Twin.

Report median and p95 frame time from the trace, not an FPS number read from a
single moment. Include dropped frames, long tasks, main-thread time, canvas
dimensions, DPR, and whether the browser used hardware acceleration.

### Resource lifecycle evidence

In DevTools Memory/Performance tooling:

1. Record the JS heap before mounting Twin.
2. Enter and leave Compare three times, then return to Twin.
3. Force GC where the browser permits it and record heap, canvas count, and
   detached DOM nodes.
4. Repeat after opening/closing findings, component inspection, and the Copilot
   dock.

GPU memory is not portable across browsers. If it is available in the selected
   tool, record it separately; never substitute JS heap for GPU memory.

### WebGL fallback evidence

Exercise all of the following in a real browser and retain screenshots plus the
console/network result:

- WebGL disabled or unavailable at launch.
- GPU acceleration disabled or software rendering forced.
- WebGL context loss, using the browser's WebGL diagnostics or a controlled test
  harness if available.
- A device-class or browser where the measured frame budget is exceeded.
- `prefers-reduced-motion: reduce` enabled before loading Twin.
- Compare entered and exited after a fallback has been shown.

For each case, verify that the structured fallback retains valid metrics and
findings, exposes a retry or return action, preserves the safety disclaimer,
and leaves the other routes usable. A successful Next build or HTTP response is
not WebGL fallback evidence.

## Sign-off record

Before marking M9 performance complete, attach or link the raw evidence for:

- build revision, Node/pnpm versions, and route table;
- compressed initial transfer and largest-chunk attribution per route;
- Web Vitals or equivalent lab timing per route;
- single-heart and split-heart frame traces;
- long-task and interaction results;
- resource lifecycle/heap results;
- WebGL-unavailable, context-loss, reduced-motion, and low-performance fallback
  checks.

Until those records exist, the honest status is **audit complete, performance
measurement gate open**.
