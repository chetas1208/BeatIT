# Wave 4 — Artifact UI (Agent 18)

Scope: render `AssistantArtifact` (`python/hearttwin/assistant/schemas.py`) as
compact chat-referenceable cards with expandable detail, per
`docs/assistant/GLOBAL_ARCHITECTURE.md`'s "ARTIFACT ARCHITECTURE" / "ARTIFACT
UX" — chat text and artifacts stay separate; the chat surface never dumps a
payload inline.

## Files added

- `web/components/assistant/ArtifactCard.tsx` — compact card: icon + label by
  `type`, title, one-line summary derived defensively from `payload`, "View"
  button. Never fabricates a summary for a type it doesn't understand.
- `web/components/assistant/PhysicianBriefView.tsx` — full detail view for
  `PHYSICIAN_BRIEF` only.
- `web/components/assistant/ArtifactDetailPanel.tsx` — dispatcher/modal
  container. Routes `type === "physician_brief"` to `PhysicianBriefView`;
  every other type gets `RawPayloadFallback`, an explicitly-labeled raw
  key/value dump.

## Which artifact type has a real view (this wave)

| `AssistantArtifactType`     | Backend generator                         | UI this wave                    |
|------------------------------|--------------------------------------------|----------------------------------|
| `physician_brief`            | `physician_brief.generate_physician_brief` (real, Wave 3) | **Real view** — `PhysicianBriefView` |
| `cardiac_component_report`   | none yet                                    | Raw-payload fallback |
| `timeline_summary`           | none yet                                    | Raw-payload fallback |
| `evidence_table`              | none yet                                    | Raw-payload fallback |
| `pv_comparison`               | none yet                                    | Raw-payload fallback |
| `shadow_trial_summary`        | none yet                                    | Raw-payload fallback |
| `uncertainty_analysis`        | none yet                                    | Raw-payload fallback |

`PHYSICIAN_BRIEF` is the only type with a real backend generator as of this
wave (Wave 2's tool registry produces raw `ToolResult`s for the others, not
artifacts — see `docs/assistant/WAVE_3_HANDOFF.md`). Building a real payload
contract + view for the other 6 without a backend shape to render against
would mean inventing UI-side data that doesn't exist yet, which the task
brief and `GLOBAL_ARCHITECTURE.md`'s "never fabricate" principle both rule
out. `ArtifactDetailPanel`'s dispatch is a single `switch`-shaped branch
(`hasRealArtifactView` in `ArtifactCard.tsx`), so adding a real view later is
a one-line addition, not a rewrite.

## Transparency in `PhysicianBriefView`

`DecisionSupportBundle` (`physician_brief.py`) ships several lists that are
honestly empty today — `observed_evidence` (no tool exposes a true
non-computed value yet), `simulated_results`/`uncertainty` (empty without an
`ensemble_id`), `missing_evidence`, `conflicts`, `possible_interpretations`
(no detection/ranking logic exists yet). Per `GLOBAL_ARCHITECTURE.md`'s
physician decision-support philosophy, an empty list is a fact the physician
needs ("not yet computable"), not something to hide.

Every section in `PhysicianBriefView` (`Section` component) renders
unconditionally, with a count chip (`data-status="warning"` when zero) and an
explicit, per-section empty-state sentence (e.g. "Not yet checked — no
cross-source conflict detection exists yet. This does not mean no conflicts
exist.") instead of being conditionally omitted. No section is ever silently
skipped.

## No treatment-recommendation UI

`DecisionSupportBundle`'s TS mirror in `PhysicianBriefView.tsx` is a
field-for-field copy of the Python model — `question`, `clinical_context`,
`observed_evidence`, `derived_evidence`, `simulated_results`, `uncertainty`,
`missing_evidence`, `conflicts`, `assumptions`, `provenance`, `limitations`,
`possible_interpretations`. There is no `recommended_treatment` field, no
"Recommended treatment:" label, and no other UI element anywhere in
`ArtifactCard.tsx` / `PhysicianBriefView.tsx` / `ArtifactDetailPanel.tsx` that
reads as a therapy/treatment recommendation. Confirmed by grep across all
three files for `recommend`, `treatment`, `therapy`, `prescri` — the only
hits are in `PhysicianBriefView.tsx`'s own code comments stating this
constraint (lines 15-16, 37); no UI-rendered string or JSX element matches.

## Types

`web/types/assistant.ts` (Agent 16) did not exist when this task started; it
landed mid-task. `ArtifactCard.tsx` now imports `AssistantArtifact` /
`AssistantArtifactType` / `ProvenanceRef` from `@/types/assistant` and
re-exports them so `PhysicianBriefView.tsx` / `ArtifactDetailPanel.tsx` have
one shared import path — no second, drifting type definition was left behind.

## Tests

No React component render-test convention exists in this repo today. All
existing `web/**/__tests__` and `web/tests` files test pure logic (`lib/**`)
with Node's built-in `--test` runner and `--experimental-strip-types`; there
is no `@testing-library/react`, `jsdom`, or any DOM-rendering test harness in
`web/package.json`'s devDependencies. Rather than inventing a new test
convention unilaterally for three files, this wave ships without component
tests — a future wave should decide the harness (e.g. `@testing-library/react`
+ `jsdom`/`happy-dom`) once, for the whole `web/` tree, not per-component.

## Next-wave dependency

Once a future wave gives `CARDIAC_COMPONENT_REPORT`, `TIMELINE_SUMMARY`,
`EVIDENCE_TABLE`, `PV_COMPARISON`, `SHADOW_TRIAL_SUMMARY`, or
`UNCERTAINTY_ANALYSIS` a real backend generator (a typed `payload` contract,
analogous to `DecisionSupportBundle`), that wave should:

1. Add a `<Type>View.tsx` component analogous to `PhysicianBriefView.tsx`.
2. Add one line to `ArtifactDetailPanel.tsx`'s dispatch and to
   `hasRealArtifactView` in `ArtifactCard.tsx`.
3. Extend `ArtifactCard.tsx`'s `summarize()` with a payload-aware one-liner
   for that type, mirroring the `physician_brief` branch.

`BeatITCopilotPanel.tsx` (Agent 16) currently renders artifacts as disabled
`[ View evidence ]` chips — wiring those chips to open `ArtifactDetailPanel`
is an integration step for whoever next touches that file, not done here
(out of this task's file-ownership scope: new files only).
