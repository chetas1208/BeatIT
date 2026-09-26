# M9 Visual Product Review

Date: 2026-09-26  
Scope: visual hierarchy, heart continuity, five-space navigation, shared visual
tokens, and internal telemetry prominence in the M9 product shell. Read-only
review; no production or test files were changed.

## Verdict

**OPEN — the M9 shell has a coherent flat visual foundation and the required
five-space navigation, but the visual product is not ready for sign-off.** The
main risks are that the shared heart can silently display a simulated branch
while the user is in `TWIN`, the promised Weave trace link is not mounted in
the rendered shell, and several Evidence surfaces bypass the shared token
system. Browser visual, responsive, WebGL, and reduced-motion behavior remain
unverified.

## Pass findings

### VIS-P1 — The shell establishes the intended reading order

**Pass, bounded to source structure.** `AppShell` renders the compact BeatIT
header and run status, then the product navigation, then a three-column layout
with the active product workspace in the center and intake/observability rails
on either side (`web/components/layout/AppShell.tsx:188-241`). The center
workspace is six of twelve columns while each supporting rail is three, which
supports the M9 rule that the owned artifact receives more visual weight than
utility telemetry. The active-space context line appears before the owned
surface (`web/components/layout/AppShell.tsx:107-133`).

This is a static hierarchy pass only; no browser screenshot or viewport
inspection was available.

### VIS-P2 — The primary navigation contains exactly the five M9 spaces

**Pass, statically.** `PRODUCT_SPACES` defines `TWIN`, `EXPERIMENT`,
`COMPARE`, `EVIDENCE`, and `REPORT` in the normative order
(`web/lib/product/contracts.ts:1,25-31`). `ProductNavigation` renders those
five items with an accessible navigation label and exposes the current item
through `aria-current="page"` (`web/components/product/ProductNavigation.tsx:45-55`).
The menu button opens a drawer containing the same five spaces rather than
introducing a sixth primary destination (`web/components/product/ProductNavigation.tsx:57-71`).

### VIS-P3 — The heart surface keeps lineage and runtime labels adjacent to the visual

**Pass for the implemented labels.** `HeartScene` places EF, `LIVE` versus
`REPLAY · DEMO STREAM`, selected-snapshot provenance, ECG context, plausible
simulated-twin status, and BPM in the viewport header next to the cardiac
visual (`web/components/heart/HeartScene.tsx:1061-1104`). It also derives the
display state and visualization from the selected temporal snapshot or
scenario artifacts rather than calculating new physiology in the render path
(`web/components/heart/HeartScene.tsx:1038-1048`).

The distinction is not yet sufficient to establish continuity across spaces;
that remains open below.

### VIS-P4 — The shared token foundation is present and visually coherent

**Pass for the foundation.** `globals.css` defines the surface, ink, signal,
accent, ECG, warning, spacing, z-index, motion, radius, and elevation tokens
and maps them into the Tailwind theme (`web/app/globals.css:35-158`). The core
panel and hairline primitives use the token surfaces and seams with square
corners and no default shadow (`web/app/globals.css:219-239`). Global focus
styling also uses the signal token (`web/app/globals.css:190-194`). This matches
the M9 flat clinical-console direction and gives new surfaces a usable shared
vocabulary.

### VIS-P5 — Internal telemetry is persistently visible as a supporting rail

**Pass, bounded to visibility and basic state treatment.** The desktop shell
always mounts `AgentTraceTimeline`, `EvalScorecard`, and `RedisStatsRail` in a
dedicated right rail, with trace and evaluation occupying the rail and Redis
remaining compact (`web/components/layout/AppShell.tsx:234-241`). Each has a
visible title, status chip, and token hairline. Trace shows agent completion
counts and per-agent durations (`web/components/trace/AgentTraceTimeline.tsx:252-310`);
evaluation shows score rows and explicit failed-check reasons
(`web/components/eval/EvalScorecard.tsx:90-145`); Redis shows stored cases and
stream entries without inventing fallback data (`web/components/redis/RedisStatsRail.tsx:91-114,116-153`).

This supports the M9 rule that telemetry is visible but subordinate. It does
not yet prove sponsor telemetry completeness or browser legibility.

## Open findings

### VIS-O1 — TWIN can silently display a simulated branch instead of the observed heart

**Severity: P0 continuity and hierarchy gap.** `HeartScene` chooses
`scenario.selectedEnsembleSample` first, then `scenario.result`, and only then
the selected temporal snapshot or store state (`web/components/heart/HeartScene.tsx:1038-1048`).
The same `HeartScene` is mounted in `TWIN`, `EXPERIMENT`, `EVIDENCE`, and
`REPORT` without a mode-specific display contract
(`web/components/layout/AppShell.tsx:116-133`). Therefore, after selecting a
plausible twin or completing a scenario, navigating to `TWIN` can leave the
simulated state in the primary Twin viewport. The header may retain a plausible
twin chip, but the product's primary question in `TWIN` is supposed to be the
selected source-backed state.

Required gate: make the owning space explicit in the heart projection. `TWIN`
must render the selected observed/derived source snapshot; hypothetical or
ensemble output must be rendered only in its owning Experiment/Compare context,
with a visible return path that never rebinds the observed origin.

### VIS-O2 — The live Weave trace entry point is not present in the rendered shell

**Severity: P1 sponsor-telemetry prominence gap.** `WeaveBadge` implements the
intended prominent live-trace/project link and documents that it belongs in the
AppShell header (`web/components/eval/WeaveBadge.tsx:3-15,57-103`). However,
`AppShell` imports and renders the run status, trace, evaluation, Redis, and
Copilot surfaces without importing or rendering `WeaveBadge`
(`web/components/layout/AppShell.tsx:20-27,188-220,247-257`). A static search
finds no other consumer of the component. The most important internal
telemetry link can therefore be absent even when the store has a live Weave
URL.

Required gate: mount the Weave status/link in the shell's intended header or
observability slot, keep it subordinate to the active cardiac artifact, and
verify connected, standby, error, and no-run-URL states in a browser.

### VIS-O3 — Redis telemetry is visible but does not expose the full internal telemetry story

**Severity: P1 observability-content gap.** The Redis rail currently renders
only `Cases stored` and `Stream entries` (`web/components/redis/RedisStatsRail.tsx:99-114,132-151`).
The product requirements call for load-bearing Redis breadth including case
state, trace streams, case-memory KNN and/or semantic cache, and token/cost
counters. The current rail does not make KNN, cache, or token/cost activity
visible, so the on-screen hierarchy gives Redis prominence without showing the
full claimed internal telemetry value.

Required gate: expose the available load-bearing Redis uses as compact labeled
rows or an explicit detail disclosure, with honest unavailable states. Do not
add fabricated counters or make the rail taller than the primary work surface
requires.

### VIS-O4 — Several Evidence surfaces bypass the shared visual tokens

**Severity: P1 visual-system consistency gap.** The M9 design audit identifies
`MissingPiecePanel`, `EvidenceMap`, `SensitivityTable`, and `UncertaintyOverlay`
as using raw `slate`, `white`, `cyan`, `amber`, and `rose` utilities, creating a
dark or differently colored island inside the light console
(`docs/hackathon/M9_DESIGN_SYSTEM.md:59-70`). `MissingPiecePanel` also uses
rounded corners while `ProductNavigation` and `ComponentInspector` use
`shadow-xl`, conflicting with the zero-radius/zero-shadow foundation. These
exceptions can pull visual attention away from the active Evidence artifact
and make lineage/status colors inconsistent across spaces.

Required gate: migrate the shared M9 surfaces to the established
`surface`/`ink`/`signal`/`accent`/`warn` tokens, and remove or explicitly review
rounded/shadow treatments before calling the visual system complete.

### VIS-O5 — Browser-level visual hierarchy and responsive behavior are not signed off

**Severity: P1 verification blocker.** The static structure is plausible, but
the documented M9 browser blocker prevents Chromium from launching because
`libasound.so.2` is missing, and Firefox is not installed. The preflight states
that no DOM rendering, screenshot, accessibility tree, keyboard traversal,
responsive, WebGL, or frame-time evidence was produced
(`docs/hackathon/M9_PREFLIGHT.md:86-103`). This leaves unverified whether the
three-column shell stays readable, whether the mobile stacked order preserves
the heart-first hierarchy, and whether fixed drawers/telemetry overlap the
heart.

Required gate: run the mandatory journey at a narrow and wide viewport with a
browser-capable environment, including screenshot review, WebGL console check,
keyboard navigation, and reduced-motion verification.

### VIS-O6 — Reduced motion does not yet prove a continuous-heart/comparison freeze

**Severity: P1 motion-integrity gap.** The design contract requires reduced
motion to stop or freeze continuous playback and comparison-clock advancement
(`docs/hackathon/M9_DESIGN_SYSTEM.md:250-281`). The M9 audit specifically notes
that `SplitHeartComparison` runs a `requestAnimationFrame` loop that CSS
reduced-motion rules cannot stop by themselves (`docs/hackathon/M9_DESIGN_SYSTEM.md:80-83`).
The loop is visible in `web/components/twin/comparison/SplitHeartComparison.tsx:52-69`.

Required gate: verify component-level reduced-motion behavior for the heart,
comparison clock, Plotly/camera motion, pulses, and drawers. A reduced-motion
run must retain labels and controls while freezing continuous visual motion.

## Verification evidence

- Static source review completed for `AppShell`, `ProductNavigation`,
  `HeartScene`, the shared CSS tokens, `WeaveBadge`, trace/evaluation/Redis
  rails, and the M9 design, interaction, human-factors, accessibility, and
  preflight contracts.
- The source structure confirms five-space ordering, a center-weighted shell,
  adjacent heart lineage labels, shared token primitives, and visible internal
  telemetry rails.
- No browser screenshot, DOM, WebGL, accessibility-tree, responsive, or
  reduced-motion result is claimed. The existing M9 preflight records the
  Chromium/Firefox launch blockers before page navigation.
- No production or test files were edited. The only file created by this
  review is `docs/hackathon/reviews/M9_VISUAL_PRODUCT_REVIEW.md`.
