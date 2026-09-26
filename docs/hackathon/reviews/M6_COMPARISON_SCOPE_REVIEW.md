# M6 Comparison Scope Review

**Agent:** M6 agent #22
**Date:** 2026-09-26
**Scope:** review of the active M6 UI and M6 scope documents; documentation only.
**Verdict:** **PASS — scalar paired comparison boundary preserved**

## Reviewed surface

The active `ShadowTrialPanel` presents a bounded hypothetical experiment. It
shows effect distributions for scalar metrics and a pair inspector with two
scalar cards: one for the stored baseline state and one for the corresponding
scenario state. The panel identifies the same plausible twin, states that no
new draw is made, and retains invalid-pair reasons for inspection.

Evidence: `web/components/twin/shadow-trial/ShadowTrialPanel.tsx:53-74,
121-139`.

## Comparison contract

M6 comparisons are strictly:

```text
scenario scalar value - baseline scalar value
```

The baseline and scenario values belong to the same paired plausible twin.
The UI does not compare unrelated ensemble members, rank treatments, or turn
direction categories into clinical recommendations. Distribution labels remain
descriptive simulation categories only.

The current scalar inspector displays EF, SV, and CO. The distribution surface
also supports the explicitly returned scalar metrics configured by the panel,
including heart rate and MAP. This is not a pointwise pressure-volume
comparison: the panel explicitly states that M5.5 does not provide pointwise PV
samples and that no PV uncertainty envelope is fabricated.

Evidence: `ShadowTrialPanel.tsx:10-16,45-48,67-74,135-139` and
`docs/hackathon/reviews/M6_PV_BOUNDARY_REVIEW.md`.

## One-heart rule

M6 does not render a second heart, split viewport, or baseline/scenario heart
pair. The existing application shell mounts one `HeartScene`, and that scene
owns the single 3D cardiac viewport. Shadow Trial comparison stays in scalar
cards, distributions, pair identity, and provenance text.

Evidence: `web/components/layout/AppShell.tsx:157-160` and
`docs/hackathon/reviews/M6_HEART_VIEW_REVIEW.md`.

## Explicit exclusions

- **No treatment ranking:** effect direction and category counts are
  descriptive simulation outputs. M6 makes no clinical value judgment and does
  not rank interventions or scenarios.
- **No M7 Split Heart:** M6 does not add a second heart, split-heart view, or
  side-by-side anatomical rendering.
- **No M8 Missing Piece:** M6 does not perform sensitivity analysis,
  information-gain analysis, missing-piece discovery, or uncertainty-driven
  data acquisition.
- **No scope redesign:** these exclusions apply to both the UI and the backend
  comparison contract; future milestones must not be smuggled into the M6
  scalar inspection surface.

## Review result

**PASS.** The inspected M6 surface is a baseline-vs-scenario scalar comparison
for paired plausible twins, retains the one-heart rule, and does not introduce
treatment ranking, M7 Split Heart, or M8 Missing Piece behavior. No production
code was changed for this review.

## Validation

- Read-only inspection of the active Shadow Trial panel, application shell, M6
  architecture, PV boundary review, and heart-view review.
- `git diff --check` passed after adding this document.
- No frontend or backend implementation files were modified.
