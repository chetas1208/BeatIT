# M9 Provenance and Click-to-Inspect Review

Date: 2026-09-26  
Scope: read-only review of click-to-inspect and provenance presentation across
`HeartScene`, `ProvenanceBadge`, the M6/M7 lineage surfaces, M8 evidence
outputs, and the M9 five-space shell. No production or test files were edited.

## Verdict

**OPEN — component inspection works for pointer users and the M6/M7 lineage
projection is source-preserving, but provenance is not yet a complete
click-to-inspect surface.** The current UI can select anatomy and open a
component inspector/report, and comparison selection preserves semantic IDs.
The selected snapshot's provenance is reduced to a non-interactive badge, with
no source-detail disclosure or evidence-ID inspection path. M9 also leaves
keyboard access, modal focus behavior, and artifact rehydration unverified or
open.

## Reviewed sources

- `web/components/heart/HeartScene.tsx`
- `web/components/heart/interaction/SemanticPickLayer.tsx`
- `web/components/heart/interaction/useHeartInteraction.ts`
- `web/components/heart/inspector/ComponentInspector.tsx`
- `web/components/heart/report/ComponentReportPanel.tsx`
- `web/components/twin/provenance/ProvenanceBadge.tsx`
- `web/lib/twin/provenance/index.ts`
- `web/lib/heart/patient/adapter.ts`
- `web/components/twin/comparison/SplitHeartComparison.tsx`
- `web/lib/twin/comparison/provenance.ts`
- `docs/hackathon/M6_PROVENANCE.md`
- `docs/hackathon/M7_SPLIT_HEART.md`, `M7_COMPONENT_COMPARISON.md`, and
  `M7_SIGNAL_BOUNDARY.md`
- `docs/hackathon/M8_COMPLETION.md`, `M8_PREFLIGHT.md`, and `M8_QA.md`
- `docs/hackathon/M9_INFORMATION_ARCHITECTURE.md`, `M9_INTERACTIONS.md`,
  `M9_ACCESSIBILITY.md`, and `M9_PREFLIGHT.md`

## Pass findings

### PROV-P1 — Pointer selection reaches a real component inspector

**Pass for pointer interaction.** `SemanticPickLayer` creates stable semantic
pick meshes from the registered heart components and sends the registry ID to
`onSelect`; hover and selection are separate states
(`web/components/heart/interaction/SemanticPickLayer.tsx:19-21`).
`HeartScene` converts the selected ID into a report and mounts
`ComponentInspector`; the inspector can then open the component report
(`web/components/heart/HeartScene.tsx:1053-1057,1108-1123`). Canvas misses clear
the selection, and Escape clears the interaction controller
(`web/components/heart/HeartScene.tsx:892-904`,
`web/components/heart/interaction/useHeartInteraction.ts:9-16`).

This is consistent with M9's information architecture: component inspection is
a contextual detail surface owned by TWIN/COMPARE, not a sixth primary space
(`docs/hackathon/M9_INFORMATION_ARCHITECTURE.md:128-139`).

### PROV-P2 — M7 linked and independent selection preserve semantic identity

**Pass for the implemented selection contract.** Split Heart stores baseline
and counterfactual semantic IDs. Linked selection writes the same registered ID
to both panes; unlinked selection changes only the clicked pane
(`web/components/twin/comparison/SplitHeartComparison.tsx:51-80`). Each pane is
an independently mounted `HeartTwinInstance`, and the selected component opens
the same inspector/report path with that pane's state
(`web/components/twin/comparison/SplitHeartComparison.tsx:85`,
`web/components/heart/HeartScene.tsx:967-1019`). This matches the M7 contract
that the two panes are real same-sample baseline/scenario renderers and that
pair identity and scenario provenance remain visible above them
(`docs/hackathon/M7_SPLIT_HEART.md:9-14`).

### PROV-P3 — Backend-authoritative M6 lineage is projected without invented edges

**Pass for the comparison projection boundary.** The frontend projection
requires trial, ensemble, and scenario identities, checks origin and ensemble
consistency when those fields are present, carries evidence IDs, and emits only
the supplied origin → ensemble → scenario → same-sample pair relationships
(`web/lib/twin/comparison/provenance.ts:215-248,258-329`). Its tests cover
stable ordering, evidence-ID deduplication, invalid-pair rejection lineage,
and broken identity/origin failures
(`web/lib/twin/comparison/__tests__/provenance.test.ts:72-140`). This respects
the M6 rule that the frontend may display provenance but must not reconstruct or
infer missing lineage (`docs/hackathon/M6_PROVENANCE.md:30-32`).

### PROV-P4 — M8 evidence language retains explicit limits

**Pass for the reviewed boundary language.** M8 labels its outputs as an
uncertainty-impact heuristic and Evidence Priority Score, preserves unavailable
reasons and provenance, and explicitly excludes posterior uncertainty,
probabilities, diagnoses, treatment, and clinical measurement recommendations
(`docs/hackathon/M8_COMPLETION.md:14-22,37-48`). The QA record also confirms
that invalid/unavailable analysis is not replaced with fabricated values
(`docs/hackathon/M8_QA.md:12-19`). The click-to-inspect review should therefore
continue to expose missing provenance as missing rather than substituting a
plausible source.

### PROV-P5 — Simulation status is visibly separated from observed context

**Pass in the reviewed shell paths.** TWIN exposes the selected snapshot's
quality/source summary through `ProvenanceBadge`; plausible samples are marked
`PLAUSIBLE SIMULATED TWIN`; and Split Heart labels its output as a hypothetical
simulation (`web/components/heart/HeartScene.tsx:1084-1095`,
`web/components/twin/comparison/SplitHeartComparison.tsx:83-91`). The underlying
lineage helper copies evidence IDs and provenance records without mutating the
snapshot (`web/lib/twin/provenance/index.ts:9-24`).

## Open findings

### PROV-O1 — ProvenanceBadge is passive text, not click-to-inspect provenance

**Open — P1 interaction gap.** `ProvenanceBadge` renders a `<span>` with a
summary and a native `title` containing comma-separated evidence IDs
(`web/components/twin/provenance/ProvenanceBadge.tsx:4-8`). It has no button or
disclosure semantics, no keyboard activation, no source-detail panel, and no
way to inspect the individual `TwinProvenance` records returned by
`lineageForSnapshot`. The browser tooltip is not a durable or accessible
provenance inspection mechanism. The M9 contract explicitly places provenance
drawers in contextual inspection and requires stable detail identity when a
drawer is deep-linked (`docs/hackathon/M9_INTERACTIONS.md:26-50`).

### PROV-O2 — Component inspection does not carry selected-snapshot lineage

**Open — P1 lineage visibility gap.** `HeartScene` builds the component report
from `displayState` and cardiac findings only
(`web/components/heart/HeartScene.tsx:1039-1056`). The patient adapter derives
component evidence from the state's `source_map` and localized findings
(`web/lib/heart/patient/adapter.ts:192-219`), then the report exposes those
labels, but no selected snapshot ID, snapshot quality, top-level evidence IDs,
or full provenance records are passed into the inspector/report
(`web/lib/heart/patient/adapter.ts:241-266`). A user can inspect anatomy and
component-level source-map evidence, but cannot establish from that drawer
which immutable snapshot or broader lineage produced the visible twin.

### PROV-O3 — Findings are not a second click-to-inspect path

**Open — P2 discoverability gap.** Finding markers are rendered as numbered
3D/HTML readouts, while the findings list is ordinary text
(`web/components/heart/HeartScene.tsx:748-797,1129-1150`). The text rows do not
select or focus the corresponding anatomy, and the markers have no accessible
selection control. M9 accessibility explicitly records that the 3D anatomy
path is pointer-only and that the findings list is text-only
(`docs/hackathon/M9_ACCESSIBILITY.md:90-98`). Thus a user who starts from a
provenance-bearing finding cannot click through to the same component inspector
as a user who starts from the pick mesh.

### PROV-O4 — Modal inspection behavior does not meet the M9 drawer contract

**Open — P1 accessibility/interaction gap.** `ComponentInspector` is an
`aside` without dialog semantics or focus management
(`web/components/heart/inspector/ComponentInspector.tsx:80-97`), while
`ComponentReportPanel` declares `role="dialog"` and `aria-modal` but only
provides a close button, with no focus capture, focus trap, Escape handling, or
focus restoration (`web/components/heart/report/ComponentReportPanel.tsx:6-12`).
The M9 interaction contract requires all of those behaviors for a drawer
(`docs/hackathon/M9_INTERACTIONS.md:33-47,52-105`), and the accessibility audit
already identifies the component report as an inconsistent modal
(`docs/hackathon/M9_ACCESSIBILITY.md:71-89`).

### PROV-O5 — Provenance inspection is session-local and not rehydratable

**Open — P1 continuity gap.** The M9 shell derives the selected snapshot and
artifact IDs from mounted React providers/stores; the product URL carries only
the mode and does not encode snapshot, ensemble, trial, pair, component, or
drawer identity (`docs/hackathon/M9_PREFLIGHT.md:150-165`). The shell therefore
cannot reopen the same provenance detail after reload or direct navigation, and
it cannot fail closed on a stale or mismatched artifact. This conflicts with the
M9 requirement that stable inspection details carry enough context to reopen
the same detail and that absent/stale identities fail closed
(`docs/hackathon/M9_INTERACTIONS.md:45-50`,
`docs/hackathon/M9_INFORMATION_ARCHITECTURE.md:54-58,94-107`).

### PROV-O6 — Browser and assistive-technology verification is still absent

**Open — evidence gap.** The M8 and M9 records explicitly state that browser,
WebGL, keyboard, screen-reader, and focus behavior were not signed off because
Chromium lacks `libasound.so.2` and Firefox is unavailable
(`docs/hackathon/M8_COMPLETION.md:44-48`, `docs/hackathon/M8_QA.md:21-25`,
`docs/hackathon/M9_ACCESSIBILITY.md:275-297`). Source inspection establishes
the gaps above but does not prove rendered hit targets, focus order, tooltip
announcements, or responsive drawer behavior. No browser pass is claimed by
this review.

## Required closure evidence

Before provenance interaction can be marked PASS, the repository needs:

1. A keyboard-accessible provenance trigger/disclosure that exposes snapshot
   quality, source records, evidence IDs, and missing/unavailable reasons.
2. A clear lineage handoff from the selected snapshot into component and
   comparison inspection, including artifact identity and source status.
3. A keyboard or equivalent semantic fallback for every anatomy/finding
   selection available in the 3D view.
4. Dialog/drawer focus entry, containment, Escape behavior, outside-click rules,
   and focus restoration for component inspection and reports.
5. Persisted or URL-addressable artifact identity with fail-closed reload and
   mismatch behavior.
6. Browser and assistive-technology evidence at narrow and wide viewports.

## Verification boundary

This was a source-and-contract review only. Existing focused provenance and
comparison tests were inspected as evidence of pure projection behavior; no
browser or screen-reader result is asserted. No production or test files were
modified.
