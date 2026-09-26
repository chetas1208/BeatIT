# M9 Design System

Status: **design-system audit and M9 contract**
Last audited: **2026-09-26**

This document records the CSS and component system that exists today and the
visual rules M9 must follow while consolidating `TWIN → EXPERIMENT → COMPARE →
EVIDENCE → REPORT`. It is a design contract, not evidence that the browser,
responsive, accessibility, or visual gates have passed. The M9 preflight keeps
those gates open until a browser-capable environment is available.

## 1. Current audit

### Token foundation observed

The source of truth is [`web/app/globals.css`](../../web/app/globals.css):

| Role | Existing selectors/tokens | M9 interpretation |
|---|---|---|
| Page and panel surfaces | `--ht-bg`, `--ht-surface-1`, `--ht-surface-2`, `--ht-surface-3`, `--ht-overlay` | Use the light clinical surface ramp. `surface-1` is the primary work surface; `surface-2` is a toolbar/raised context; `surface-3` is hover/selected fill. |
| Seams and dividers | `--ht-line`, `--ht-line-strong`, `.ht-hairline` | Prefer the existing puzzle-grid seam and hairline model over individual card borders. |
| Text hierarchy | `--ht-ink`, `--ht-ink-2`, `--ht-muted`, `--ht-faint` | `ink` is current content, `ink-2` is supporting content, `muted` is metadata, and `faint` is decorative/disabled only. |
| Accent | `--ht-accent*`, `text-accent`, `text-accent-bright` | Systolic crimson is for primary actions and hypothetical/simulated emphasis; it is not a clinical severity scale. |
| Data/agent signal | `--ht-signal*`, `text-signal`, `text-signal-bright` | Use for trace, agent, source, and data connectivity cues. |
| Recovery/status positive | `--ht-ecg*`, `--ht-ok` | Use for completed/available states, never as a claim that a physiological result is clinically good. |
| Caution | `--ht-warn*` | Use for missing evidence, limitations, prior assumptions, synthetic replay, and incomplete work. |
| Geometry | `--ht-r-xs` through `--ht-r-lg` are `0px`; `--ht-r-pill` is `999px` | The product is intentionally flat and square. A pill is reserved for compact badges/dots, not cards. |
| Motion | `--ht-dur-fast` `150ms`, `--ht-dur-mid` `220ms`, `--ht-dur-slow` `360ms`; standard and ease-out curves | Keep interaction motion short and bounded. Do not add bounce, elastic easing, or decorative autoplay. |
| Elevation | `--ht-shadow-panel: none`, `--ht-shadow-raised: none` | Spatial hierarchy comes from layout, surface, and seam; a shadow is not a default card treatment. |

`@theme inline` maps the color/radius tokens to Tailwind utilities. The root
also sets `color-scheme: light` and loads Inter through `--font-ui` in
[`web/app/layout.tsx`](../../web/app/layout.tsx). All new M9 UI should consume
these tokens rather than introduce another palette.

### Existing primitives and component vocabulary

These selectors are the current reusable vocabulary and should be composed,
not forked:

| Primitive | Current behavior | Existing consumers / evidence |
|---|---|---|
| `.ht-panel`, `.ht-panel-raised` | Borderless `surface-1`/`surface-2` blocks; grid seams provide separation | `Panel` in [`components/ui/Panel.tsx:22-37`](../../web/components/ui/Panel.tsx#L22-L37); used by the heart, trace, evaluation, Redis, scenario, and report surfaces. |
| `PanelHeader`, `PanelBody`, `PanelEmpty` | Shared header/body rhythm and composed empty state | [`components/ui/Panel.tsx:40-121`](../../web/components/ui/Panel.tsx#L40-L121). `PanelEmpty` is the preferred honest first-load state. |
| `.ht-hairline` | One-pixel token divider | Panel headers and telemetry surfaces, including `HeartScene`, `AgentTraceTimeline`, and `EvalScorecard`. |
| `.ht-eyebrow`, `.ht-panel-title` | Small uppercase context label and compact panel title | Panel headings, provenance headings, and shell context labels. |
| `.ht-btn`, `.ht-btn-primary`, `.ht-btn-secondary`, `.ht-btn-ghost` | One button geometry with primary, secondary, and quiet states | Primary actions in `ScenarioPanel`, `PlausibleTwinsPanel`, `ProductNavigation`, and compare controls. |
| `.ht-chip`, `.ht-chip-dot`, `.ht-chip[data-status]` | Compact operational state badge; `data-status` currently maps idle/running/success/warning/failed families to the existing palette | Shell run status, heart telemetry, trace, Redis, Weave, evaluation, and report section status. |
| `.ht-pulse` | Expanding ring for a live state dot | Live trace/Weave/run indicators. It must never be the only status signal. |
| `.ht-skeleton`, `.ht-ecg-sweep` | Shape-matching loading shimmer and telemetry sweep | Loading/telemetry placeholders only; neither may imply a value or clinical signal. |
| `.ht-mono` | Tabular numeric/telemetry helper | IDs, counts, durations, metrics, and source references. |

The foundation has an important implementation detail: `--font-mono` currently
resolves to the same Inter stack as `--font-sans` in `globals.css:149-154`.
`.ht-mono` still provides tabular figures and stable spacing, but it is not a
distinct monospace face today. M9 should preserve the selector contract and
must not describe it as a separate font until the token is actually changed.

### Audit gaps to keep visible

The following are observed deviations, not reasons to invent a second system:

- [`MissingPiecePanel.tsx:77-185`](../../web/components/twin/missing-piece/MissingPiecePanel.tsx#L77-L185), `EvidenceMap`, `SensitivityTable`, and
  `UncertaintyOverlay` use raw `slate`, `white`, `cyan`, `amber`, and `rose`
  utilities. They bypass the OKLCH token ramp and render a dark island inside
  the light console. M9 must migrate those surfaces to the shared tokens before
  calling the visual system complete.
- `MissingPiecePanel` uses `rounded-xl` and `rounded-lg`; `ProductNavigation`
  and `ComponentInspector` use `shadow-xl`. Those selectors conflict with the
  zero-radius/zero-shadow foundation and the no-fake-card rule below.
- `PanelHeader` accepts `eyebrow` and `accent` for compatibility but does not
  render them ([`Panel.tsx:40-57`](../../web/components/ui/Panel.tsx#L40-L57)).
  M9 hierarchy must therefore use the visible title and a separate contextual
  line where needed; callers must not assume an unrendered eyebrow establishes
  hierarchy.
- The direct shell uses the correct seam model in
  [`AppShell.tsx:127-200`](../../web/components/layout/AppShell.tsx#L127-L200),
  while some child surfaces add their own bordered/rounded containers. Those
  nested boundaries should be reduced when each surface is next touched.
- `SplitHeartComparison` runs a `requestAnimationFrame` loop for its comparison
  clock. The CSS reduced-motion rule cannot stop that loop by itself. M9 browser
  verification must confirm that reduced motion also suppresses continuous
  heart/clock presentation at the component level.

## 2. M9 hierarchy

M9 has one product story, not a dashboard of equally weighted cards. Visual
weight follows ownership and decision order:

```text
application frame
├─ brand + operational run status
├─ five-space primary navigation
├─ active space context (name + one-line purpose)
├─ owned primary artifact/work surface
│  ├─ primary action or current result
│  ├─ supporting controls and comparison/detail rows
│  └─ provenance, limitations, and safety boundary
├─ contextual drawers/inspectors
└─ utility telemetry (trace, evaluation, Redis, Copilot)
```

### Fixed shell order

The current shell in `AppShell` is the baseline M9 composition:

1. The compact header identifies BeatIT and shows the run state using
   `.ht-chip[data-status]`.
2. `ProductNavigation` exposes exactly `TWIN`, `EXPERIMENT`, `COMPARE`,
   `EVIDENCE`, and `REPORT`, in that order. A menu/drawer is a navigation aid,
   not a sixth space.
3. The center column owns the active space and receives the strongest visual
   weight. Its context band is the existing `.ht-eyebrow` plus one concise
   purpose line.
4. The left intake rail and right observability rail support the center; they do
   not compete with its primary artifact. `AgentTraceTimeline`, `EvalScorecard`,
   and `RedisStatsRail` remain utility telemetry.
5. Copilot, drawers, inspectors, and the safety modal are contextual layers.
   They must preserve the underlying space and never become alternate primary
   navigation.

### Hierarchy inside each space

| Space | First visual question | Order of content |
|---|---|---|
| `TWIN` | What is the selected source-backed state? | Current state/heart → timeline and anatomy → source/provenance → limitations. |
| `EXPERIMENT` | What bounded hypothetical is being changed? | Scenario definition and action → plausible simulated ensemble → Shadow Trial → assumptions/limitations. |
| `COMPARE` | Which valid pair is being compared? | Pair identity and baseline/counterfactual hearts → modeled deltas → signal/provenance context → scalar limitations. |
| `EVIDENCE` | What target and evidence coverage are available? | Target and coverage → local sensitivity/uncertainty-impact heuristic → evidence priorities → unavailable reasons and safety. |
| `REPORT` | What does this exact artifact chain contain? | Journey summary → supporting sections → source IDs, omitted/unavailable inputs, limitations, and safety disclaimer. |

The absence of a child artifact is an honest state, not an invitation to fill a
space with a plausible value. A summary in a non-owning space links to its
owner; it does not become a second primary workflow.

## 3. Provenance badges

### Keep operational state separate from data lineage

`data-status` is already used for operational state (`idle`, `running`,
`success`, `warning`, `failed`, and related aliases) by `.ht-chip`. M9 must not
use it to mean observed, simulated, or synthetic. Add lineage semantics at the
content boundary with a separate attribute when implementation work begins:

```tsx
<span className="ht-chip" data-lineage="observed">OBSERVED</span>
```

The visible word is mandatory. Color, dots, and motion are supporting cues, not
the classification. A badge should sit next to the value or artifact it
qualifies and include source, method, snapshot, or scenario context when that
context exists.

### M9 lineage vocabulary

| `data-lineage` | Required visible label | Meaning | Visual treatment using existing tokens | Forbidden wording |
|---|---|---|---|---|
| `observed` | `OBSERVED` | Directly present in a supplied input record or measurement, with source/evidence identity retained | Signal family: `--ht-signal-soft` background, `--ht-signal-line` border, `--ht-signal-bright` text. No pulse unless the separate operational stream is live. | Do not imply that every observed field is current, complete, or a live feed. |
| `derived` | `DERIVED` | Deterministically calculated from classified inputs | Neutral: `--ht-surface-2`, `--ht-line-strong`, `--ht-ink-2`. Keep it visibly different from observed without making it look worse. | Do not call it observed, measured, or an independent source. |
| `simulated` | `SIMULATED` or `PLAUSIBLE SIMULATED TWIN` | Produced by the deterministic physiology engine, a bounded scenario, or a visual projection | Accent family: `--ht-accent-soft`, `--ht-accent-line`, `--ht-accent-bright`; pair with explanatory text such as `educational projection only`. | Do not call it patient evidence, measured, probable, beneficial, harmful, diagnosis, or treatment. |
| `prior` | `PRIOR` | A bounded model assumption used because evidence is missing | Warning family: `--ht-warn-soft`, `--ht-warn-line`, `--ht-warn`; use a visible `assumption` descriptor. | Do not call it an individual estimate, observation, confidence, or probability. |
| `synthetic` | `SYNTHETIC` / `REPLAY` | Generated or replayed fixture input | Warning family with a dashed or otherwise non-color-only boundary; always include `replay`, `demo stream`, or `fixture` text. | Never label it `LIVE`, `OBSERVED`, or patient evidence. |

The five labels are compatible with the existing lineage policy:
`INTERPOLATED` remains a source-specific timeline classification and should be
rendered as `DERIVED` only when the UI also says `INTERPOLATED`; it must not be
silently collapsed into observed. A plausible twin's origin can be synthetic,
but the twin output remains `SIMULATED`.

Recommended selector contract for a future shared badge implementation:

```css
.ht-chip[data-lineage="observed"]  { /* signal tokens */ }
.ht-chip[data-lineage="derived"]   { /* neutral tokens */ }
.ht-chip[data-lineage="simulated"] { /* accent tokens */ }
.ht-chip[data-lineage="prior"]     { /* warning tokens */ }
.ht-chip[data-lineage="synthetic"] { /* warning + non-color-only replay cue */ }
```

Do not replace existing operational selectors such as
`.ht-chip[data-status="running"]` or `.ht-chip[data-status="success"]`; combine
the two attributes only when both facts are true, for example an observed
record being currently loaded. `LIVE` describes transport/runtime activity,
not clinical provenance.

### Existing badge examples to preserve or clarify

- `HeartScene` already distinguishes `LIVE` from `REPLAY · DEMO STREAM`, shows a
  selected snapshot's `ProvenanceBadge`, and explicitly labels
  `PLAUSIBLE SIMULATED TWIN` ([`HeartScene.tsx:1070-1101`](../../web/components/heart/HeartScene.tsx#L1070-L1101)).
  Keep those distinctions adjacent to the visual.
- `PlausibleTwinsPanel` correctly says `PLAUSIBLE SIMULATED TWIN` and adds
  `synthetic replay origin` when applicable ([`PlausibleTwinsPanel.tsx:117-121`](../../web/components/twin/ensemble/PlausibleTwinsPanel.tsx#L117-L121)).
- `SplitHeartComparison` correctly labels the pair as a hypothetical simulation
  and says the PV shape is held ([`SplitHeartComparison.tsx:82-91`](../../web/components/twin/comparison/SplitHeartComparison.tsx#L82-L91)).
  This wording is more important than a color change.

## 4. Typography

Typography should make the current artifact and its status scannable before
metadata. Use the existing Inter family and selectors; do not add a display
face for M9.

| Role | Existing implementation | M9 rule |
|---|---|---|
| Product/surface title | `text-lg`, `text-xl`, or `text-[0.95rem]` in call sites; `.ht-panel-title` is `0.95rem/600` | One title per surface. Use a compact sentence-case title; reserve all-caps for short operational labels. |
| Panel title | `PanelHeader` uses `text-[0.8rem] font-semibold tracking-tight text-ink` | Keep the compressed rail/header scale. Do not promote every panel title to an `h1`-sized heading. |
| Context label | `.ht-eyebrow`: `0.6875rem`, weight 500, `0.14em`, uppercase | Use once for a surface context or small section label, not on every row. |
| Body/explanation | Common `text-xs` to `text-sm` with `leading-relaxed` | Explanations need readable line height and should stay beside the result they qualify. Avoid dense all-caps prose. |
| Metadata | `text-[0.6rem]` to `text-[0.68rem]`, `text-muted`/`text-faint` | Use for IDs, origin, method, timestamps, and limitations; never use faint text for required meaning. |
| Numerics/IDs | `.ht-mono`, tabular numerics | Use for units, counts, durations, IDs, seeds, and percentages. Preserve units and source labels. |
| Buttons | `.ht-btn` with `0.875rem`, weight 560, minimum 2.5rem | Use verb + object labels. Do not encode provenance or action state in typography alone. |

Avoid using tiny text to fit more cards. If a section cannot hold its title,
value, lineage, and limitation at readable scale, reduce the number of visible
items or move detail into an explicit drawer.

## 5. Color and contrast rules

The palette is deliberately small. One color must not carry multiple claims in
the same local context:

- **Neutral surfaces and ink** establish structure and reading order.
- **Signal teal** identifies source/data/agent connectivity.
- **Crimson accent** identifies primary action and hypothetical/simulated
  branch emphasis.
- **ECG green** identifies available/completed transport or process state, not
  health, benefit, or clinical safety.
- **Amber** identifies caution, incomplete evidence, priors, synthetic replay,
  and limitations.

Every status or lineage badge must include a readable label or adjacent text.
Do not use a green/red pair as the only distinction. Focus must remain the
existing `:focus-visible` outline (`--ht-signal`) and must not be conveyed by
color, hover, or motion alone.

M9 color rules:

1. Use `bg-surface-*`, `text-ink*`, `text-muted`, `text-signal*`,
   `text-accent*`, `text-ecg`, `text-warn`, `border-line`, or
   `var(--ht-...)` tokens.
2. Do not add one-off hex, RGB, HSL, or raw Tailwind palette colors to a
   product surface.
3. Do not introduce dark islands such as `bg-slate-950 text-white` inside the
   light console. If a high-attention state needs stronger contrast, use the
   existing surface and line ramp plus a semantic accent.
4. Preserve the canonical safety disclaimer and keep caution/limitation text
   adjacent to the simulated or incomplete result.

## 6. Motion

Motion communicates a state transition; it never supplies evidence or makes a
result look more certain.

### Allowed motion

- Use `--ht-dur-fast` for button/hover response, `--ht-dur-mid` for local
  selection or disclosure, and `--ht-dur-slow` for a bounded drawer/route
  transition.
- Use `.ht-pulse` only for an actually active transport/run state, with a
  persistent label such as `Live` or `Running`.
- Use `.ht-skeleton` only when the final geometry is known. Use
  `.ht-ecg-sweep` only as a telemetry/loading cue, never as a generated ECG.
- Keep the heart and comparison clock moving only while the user has an active
  live/play state. A paused, stale, failed, or unavailable result must not keep
  animating as if current.
- Components using `motion/react` must honor `useReducedMotion()`, as
  `WeaveBadge` already does for its entry/hover/tap motion.

### Required reduced-motion behavior

The global `@media (prefers-reduced-motion: reduce)` block in `globals.css`
reduces CSS animation and transition durations. M9 still needs component-level
checks for `motion/react`, requestAnimationFrame loops, Plotly animation, WebGL
camera/heart motion, and drawer focus scrolling. Reduced motion must:

- stop or freeze continuous playback and comparison clock advancement;
- remove pulse, shimmer, sweep, camera easing, and route/drawer travel, or use
  an immediate state change;
- preserve the same text, value, lineage, controls, and error/empty state;
- never replace a label with a spinner or animated dot.

No animation may show a synthetic trend, improvement, causal effect, or
clinical trajectory that the underlying artifact does not contain.

## 7. No-fake-card rules

The console's primary unit is a surface or an evidence row, not a decorative
card. A bounded container is allowed only when it has a clear owner and a
real payload.

### A container may be a panel when it

- owns one M9 space or one persistent utility rail;
- has a visible heading and a single responsibility;
- contains a real result, action, loading state, error, empty state, or
  limitation;
- preserves the artifact's lineage and safety boundary; and
- participates in the shell's seam/surface hierarchy through `.ht-panel`,
  `.ht-panel-raised`, or an explicit drawer/inspector treatment.

### Use a row, section, or disclosure instead of a card when it

- only contains one metric, source ID, warning, or status label;
- repeats a parent heading or duplicates a result owned elsewhere;
- is a summary link from a non-owning space;
- exists only to create visual rhythm around an empty value; or
- would need a shadow, large radius, or a new color to be noticed.

Concrete examples: `AgentTraceTimeline`, `EvalScorecard`, and
`RedisStatsRail` should remain compact rows inside their existing panels;
`ReportSurface` sections should remain bordered report sections, not nested
dashboard cards; provenance should remain a list/detail disclosure; and the
M8 sensitivity/priority output should be a readable table/list inside the
Evidence surface.

### Prohibited treatments

- No nested rounded cards inside every panel or one card per metric.
- No fake values, placeholder percentages, fabricated charts, or empty cards
  that look like completed results.
- No shadow or color treatment that makes an unavailable, stale, prior, or
  simulated artifact look more authoritative than an observed source.
- No duplicate primary navigation or duplicate artifact owner in a summary
  card.
- No dark `bg-slate-950` research island, `shadow-xl`, `rounded-xl`, or
  `rounded-lg` treatment in a shared M9 surface unless the foundation tokens
  are deliberately changed and the change is reviewed as a system change.
- No `LIVE` badge on a synthetic replay, prior, simulated output, or a static
  demo fixture. No green badge that says or implies clinical correctness.

## 8. Verification

### Source and token audit

Run from the repository root:

```bash
# Shared tokens and primitives exist where this contract expects them.
rg -n '^\.[A-Za-z0-9_-]+|^@keyframes|^@media|--ht-' web/app/globals.css
rg -n 'ht-panel|ht-panel-raised|ht-hairline|ht-eyebrow|ht-panel-title|ht-btn|ht-chip|ht-pulse|ht-skeleton|ht-ecg-sweep|ht-mono' web/components web/app

# Find raw palette/radius/shadow escapes that require review before M9 sign-off.
rg -n -e 'bg-(slate|white|black|cyan|amber|rose|red|blue|green)' \
  -e 'text-(white|black|slate|cyan|amber|rose|red|blue|green)' \
  -e 'border-(white|cyan|amber|rose|red|slate)' \
  -e 'rounded-(sm|md|lg|xl|2xl|full)' \
  -e 'shadow-(sm|md|lg|xl|2xl)' web/components web/app
```

The second command is an audit list, not a claim that every rounded dot or
floating trigger is wrong. Each hit must be classified as a permitted control
shape, a modal/drawer treatment, a visualization mark, or a system deviation.
The known M9 deviations are listed in section 1.

### Automated implementation checks

When frontend implementation changes land, run:

```bash
pnpm --dir web exec tsc --noEmit
pnpm --dir web exec eslint .
pnpm --dir web exec next build
```

Then run the repository gates required by the project:

```bash
pnpm test:py
pnpm check
```

### Browser acceptance checks

In a browser-capable environment, inspect all five spaces at narrow and wide
widths and verify:

1. The five primary destinations are visible in the required order and the
   active state is not conveyed by color alone.
2. The center artifact outranks rails and utility docks; no surface has nested
   decorative cards that compete with it.
3. Every observed, derived, simulated, prior, and synthetic value has the
   correct visible lineage label and adjacent source/limitation context.
4. Synthetic replay never says `LIVE`; simulated output never appears as
   observed evidence; missing/unavailable output has no plausible replacement.
5. Focus-visible outlines, drawer close/return paths, empty/error/loading
   states, safety text, and keyboard traversal remain visible and usable.
6. Reduced motion stops CSS animation, motion/react transitions, the comparison
   clock, heart playback, chart animation, and camera easing while preserving
   equivalent content and controls.
7. Contrast and readability are checked for normal text, metadata, badges,
   focus, disabled controls, and warning/error states. No state depends on hue
   alone.

Until that browser pass is recorded, this document should be cited as a
source audit and design contract only; it must not be used to close the M9
visual, accessibility, responsive, or interaction gates.

## Source references

- [`web/app/globals.css`](../../web/app/globals.css) — token declarations and CSS primitives.
- [`web/components/ui/Panel.tsx`](../../web/components/ui/Panel.tsx) — shared panel/header/body/empty primitives.
- [`web/components/layout/AppShell.tsx`](../../web/components/layout/AppShell.tsx) — current shell hierarchy and five-space mounting seam.
- [`web/components/product/ProductNavigation.tsx`](../../web/components/product/ProductNavigation.tsx) — primary navigation and space drawer.
- [`docs/hackathon/M9_INFORMATION_ARCHITECTURE.md`](./M9_INFORMATION_ARCHITECTURE.md) — space ownership and hierarchy.
- [`docs/hackathon/M9_INTERACTIONS.md`](./M9_INTERACTIONS.md) — focus, loading, empty, and reduced-motion interaction rules.
- [`docs/hackathon/OBSERVED_SYNTHETIC_POLICY.md`](./OBSERVED_SYNTHETIC_POLICY.md) — lineage meanings and synthetic replay boundary.
- [`docs/hackathon/M7_SIGNAL_BOUNDARY.md`](./M7_SIGNAL_BOUNDARY.md) — simulated electrical/signal labeling boundary.
