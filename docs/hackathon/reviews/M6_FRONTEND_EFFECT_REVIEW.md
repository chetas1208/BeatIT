# M6 Frontend Effect Visualization Review

Date: 2026-09-26
Scope: review of `web/components/twin/shadow-trial/ShadowTrialPanel.tsx` and
`web/types/shadow-trial.ts`; no frontend implementation or API contract was
changed.

## Review boundary

The panel is a Next.js App Router Client Component because it owns button,
select, and status state. The local Next.js `use-client` guidance requires the
directive at the entry point and serializable component boundaries. The local
accessibility guidance requires a descriptive status/error announcement and
does not make visual styling a substitute for accessible text.

The backend remains the sole owner of paired deltas, quantiles, tolerances, and
positive/near-zero/negative classification. The frontend only formats and
describes the returned values.

## Findings

### 1. Unit presentation mismatch — fix before M6 UI sign-off

The backend contract intentionally uses `percentage_points` for
`ejection_fraction_pct`, while the panel passes `distribution.unit` directly to
`format()`. This would render values such as `2.1 percentage_points`, which is
technically the backend unit but not the clear display label used elsewhere in
the application. The paired inspector separately displays EF as `%`, creating
an inconsistent contract presentation.

Recommended presentation mapping (display only; do not change the API):

| Metric | Contract unit | Display label |
| --- | --- | --- |
| Ejection fraction | `percentage_points` | percentage points |
| Stroke volume | `mL` | mL |
| Cardiac output | `L/min` | L/min |
| Heart rate | `bpm` | bpm |
| Mean arterial pressure | `mmHg` | mmHg |
| EDV / ESV | `mL` | mL |

For EF deltas, `%` is acceptable only when the UI explicitly says
“percentage points”; it must not imply a relative percent change.

### 2. Empty distributions need an explicit state — fix before M6 UI sign-off

If a completed response contains no effect distributions, the current panel
renders an empty bordered list with no explanation. If the trial has zero valid
pairs, the backend correctly returns `status: "failed"` and retained invalid
pairs; the UI should state that no effect summary is available and point the
user to the retained rejection reasons.

Required behavior:

- `status: "complete"` with an empty distribution list: show “No effect
  distributions returned for the selected metrics.”
- `status: "failed"` or `valid_pairs === 0`: show a distinct failure/empty
  summary, retain the invalid-pair count, and do not imply zero effect.
- A completed trial with valid pairs but no selected distribution should remain
  distinguishable from a failed trial.

### 3. Failed responses need an explicit visual and live announcement — fix

The run error path uses `role="alert"`, but a server-returned failed trial is
currently stored in `trial` and rendered like a normal result. The status text
only says how many pairs were valid/invalid. Add a textual `role="alert"`
message for a failed result, while keeping the existing polite progress/status
announcement for normal completion. Do not hide the pair inspector: retained
invalid pairs are part of the audit surface, but make their rejection reasons
the primary explanation when no valid pair exists.

### 4. Category labels are direction-only but can be clearer — recommended

The current “Positive · near-zero · negative” counts are accompanied by
“descriptive simulation categories only,” which is the correct safety boundary.
For accessibility and interpretation, the labels should make the direction
explicit:

- “Positive delta (simulation direction)”
- “Near-zero delta (within tolerance)”
- “Negative delta (simulation direction)”

These labels must not use “improved,” “worsened,” “benefit,” “risk,” or other
clinical value judgments. The panel should continue to expose the returned
`neutral_tolerance` in the metric detail or accessible description when the
category counts are shown.

## What is already correct

- The request selects backend metric IDs and does not duplicate physiology
  calculations in TypeScript.
- Distribution text states that values summarize valid paired plausible twins.
- Pair inspection preserves baseline/scenario identity and explains that no
  new scenario draw is made.
- Invalid pairs remain selectable and expose `rejection_reasons` in an alert.
- The PV comparison boundary is honest: the panel does not fabricate a PV
  uncertainty envelope from scalar summaries.
- The panel includes the canonical safety boundary and synthetic-origin warning
  returned by the backend.

## Focused validation matrix

| Input state | Expected frontend behavior | Current review result |
| --- | --- | --- |
| No ensemble/scenario result | Prompt to generate plausible twins and run the bounded experiment | Present |
| Network/request failure | Alert status; no stale trial remains | Present |
| Complete trial with distributions | Render metric summaries, units, counts, and provenance | Present, with EF unit presentation issue |
| Complete trial with empty distributions | Explain that no summary is available | Missing explicit empty state |
| Failed trial with zero valid pairs | Announce failure, retain invalid pairs/reasons, never show zero effects | Missing explicit failed state |
| Invalid selected pair | Preserve pair and show rejection reasons | Present |
| Category counts | Direction-only, tolerance-aware, non-clinical labels | Mostly present; label clarity recommended |

## Recommendation

Keep the current dependency-light panel and backend boundary. Before calling the
M6 frontend gate complete, add a small display-only unit/category formatter and
explicit complete-empty/failed rendering, then cover those states with focused
runtime tests. No M7 split-heart view, M8 missing-piece flow, model-generated
math, or API changes are needed for this review.
