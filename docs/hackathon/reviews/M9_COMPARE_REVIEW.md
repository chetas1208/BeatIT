# M9 Compare Surface Review

Date: 2026-09-26
Scope: `SplitHeartComparison`, comparison contracts and paired store, clock and
difference semantics, provenance projection, and missing/invalid-pair state.
Read-only review; no production or test files were changed.

## Verdict

**CONDITIONAL PASS — the authoritative pair, clock, difference, and provenance
boundaries are mostly sound, but the Compare state contract is not closed.**
Valid pairs are fail-closed and the comparison does not recompute physiology or
replace persisted deltas. The main release blocker is that missing or invalid
pair selection is represented by silent no-ops/nulls rather than an explicit
Compare state, and the store contract is not the state actually used by the
rendered Split Heart surface.

## Pass findings

### CMP-1 — Split Heart consumes the stored pair and preserves the numerical authority

**Pass.** `SplitHeartComparison` receives a `ShadowTrialPair`, derives the two
visual projections from the stored baseline/scenario states, and passes the
pair directly to the difference renderer
(`web/components/twin/comparison/SplitHeartComparison.tsx:12-18,51-57,101-105`).
The UI explicitly says that scalar values and deltas come from the persisted M6
pair and that frontend physiology is not recomputed
(`web/components/twin/comparison/SplitHeartComparison.tsx:102-103`). The
projection only maps stored scalar values into existing visual channels and
marks the PV shape as held from the source visualization
(`web/lib/twin/comparison/projection.ts:15-44`). Invalid pairs are rejected by
the projection before they can become a `PairedHeartState`
(`web/lib/twin/comparison/projection.ts:47-49`).

### CMP-2 — Pair identity and invalid-pair lineage fail closed in provenance

**Pass.** The provenance projection requires non-empty IDs, preserves
`baseline_twin_id == sample_id`, requires distinct scenario and baseline twin
IDs, rejects duplicate sample IDs, and requires rejection reasons for invalid
pairs (`web/lib/twin/comparison/provenance.ts:74-79,153-171,173-196`). It
retains invalid pair lineage by default while allowing an explicit valid-only
projection (`web/lib/twin/comparison/provenance.ts:65-70,194-196`). It also
checks the response definition, baseline ensemble, and origin snapshot for
cross-field consistency (`web/lib/twin/comparison/provenance.ts:215-244`).
The resulting trace is deterministic and bounded to relationships actually
present in M6; it does not invent physiological causal edges
(`web/lib/twin/comparison/provenance.ts:206-213`).

### CMP-3 — Clock behavior is deterministic and mathematically separated from physiology

**Pass.** The clock validates heart rates, modes, playback speed, phase, and
elapsed time, normalizes phase to `[0, 1)`, and returns immutable reducer-style
states (`web/lib/twin/comparison/clock.ts:37-92`). Phase-locked mode uses one
shared visual phase while retaining each side's displayed heart rate;
physiologic-rate mode advances each side by its own BPM
(`web/lib/twin/comparison/clock.ts:172-213`). Seek, resync, pause, and reset
operate on the visual cursor only and do not mutate the paired cardiac state.
The focused phase-lock tests cover unequal rates, seek, pause/reset, and input
immutability.

### CMP-4 — Difference rendering treats persisted deltas as authoritative and missing values as unavailable

**Pass.** `buildMetricDelta` refuses invalid pairs, missing/non-finite deltas,
and unit contradictions; it uses the DTO delta rather than subtracting the
displayed cardiac states (`web/lib/twin/comparison/differences.ts:39-55`). It
uses metric-specific units and neutral tolerances, labels EF changes as
percentage points, and only derives a relative display percentage when a
finite non-zero baseline exists (`web/lib/twin/comparison/differences.ts:6-8,39-55`).
The difference-only mode preserves unsupported anatomy, suppresses floating
point noise, and exposes an explicit no-modeled-difference state
(`web/lib/twin/comparison/__tests__/difference-mode.test.ts`; UI at
`web/components/twin/comparison/SplitHeartComparison.tsx:102-103`).

## Open findings

### CMP-O1 — Missing or invalid pair selection has no explicit state and can silently retain the old comparison — P1

**Open.** The paired store represents the selected result only as nullable
`paired`, while `ComparisonViewState.selectedPairId` is always a string
(`web/lib/twin/comparison/store.ts:9-22`; `web/lib/twin/comparison/contracts.ts:67-89`).
`open` and `selectPair` call `buildPair`, but if the requested pair is absent,
invalid, or fails projection, they simply do nothing
(`web/lib/twin/comparison/store.ts:29-39`). That leaves an already-open valid
pair visible even after a user selects a missing/invalid pair, and gives the
caller no `missing`, `invalid`, or `unavailable` reason to render.

The panel does retain and explain invalid pairs, but it only offers the
comparison button for valid pairs (`web/components/twin/shadow-trial/ShadowTrialPanel.tsx:69-77`).
When there are no `paired_results`, `PairInspector` returns `null` rather than
rendering an explicit empty state (`web/components/twin/shadow-trial/ShadowTrialPanel.tsx:55-59`).
This conflicts with the M9 Compare requirement that setup, loading, failed,
and no-valid-pair states be distinct and that absence not mean zero or a
computed unavailable measurement (`docs/hackathon/M9_PRODUCT_STATE.md:150-158`).

Recommended closure:

- Model an explicit comparison load/result state with `empty`, `invalid`, and
  `unavailable` branches, including the requested pair ID and rejection reason.
- Clear or replace the current pair when selection cannot resolve; never leave
  the previous pair presented as the selected one.
- Render a visible no-pairs/no-valid-pairs state in `PairInspector` and cover
  zero pairs, missing IDs, invalid selection, and projection rejection.

### CMP-O2 — The paired store contract is not the source of truth for the rendered Split Heart controls — P1

**Open.** The store exposes clock mode, playing, phase, component selection,
linked selection, linked camera, and difference-only state
(`web/lib/twin/comparison/store.ts:13-22`). However, `SplitHeartComparison`
creates independent local state for all of those controls and advances its own
clock (`web/components/twin/comparison/SplitHeartComparison.tsx:56-78`). The
component does not read or write `useComparisonStore`; the store's
`ComparisonViewState` is therefore not updated by the visible Compare UI.
`linkedCamera` and the store's selected component/phase are consequently dead
contract surface for this path.

This is a consistency and reload/invalidation risk: another surface such as
the report reads `useComparisonStore().paired`, but there is no single owner
for the comparison view state. M9 requires computation payloads and selected
presentation state to remain coherent across the product spaces
(`docs/hackathon/M9_PRODUCT_STATE.md:101-118,185-196`). Choose one owner and
test it: either make the component controlled by the store, or remove the
unused store view commands and define a separate local-only contract.

### CMP-O3 — Pair-level provenance does not carry evidence IDs into pair/twin steps — P2

**Open.** The provenance projection canonicalizes and exposes response-level
`evidence_ids` on the trace and origin/ensemble steps
(`web/lib/twin/comparison/provenance.ts:244-249,258-288`), but every pair sets
`pairEvidenceIds` to an empty array before creating baseline-twin,
scenario-twin, paired-comparison, and paired-delta steps
(`web/lib/twin/comparison/provenance.ts:310-317`). This is honest if M6 has no
pair-specific evidence, but the resulting trace does not make that boundary
explicit: a consumer can see global evidence IDs while each displayed pair
appears to have no evidence linkage.

Recommended closure: retain the current no-invention behavior, but document
the distinction in the trace contract/UI (global trial evidence versus
pair-specific evidence unavailable), or add a typed `evidenceScope`/explicit
unavailable marker rather than an indistinguishable empty list.

## Verification evidence

Focused comparison tests were run from `web/`:

```text
node --experimental-strip-types --loader ./tests/alias-loader.mjs --test \
  ./lib/twin/comparison/__tests__/phase-lock.test.ts \
  ./lib/twin/comparison/__tests__/differences.test.ts \
  ./lib/twin/comparison/__tests__/difference-mode.test.ts \
  ./lib/twin/comparison/__tests__/provenance.test.ts \
  ./lib/twin/comparison/__tests__/selection.test.ts

28 passed, 0 failed
```

The test run covered clock phase semantics, persisted-delta handling and unit
policy, difference-mode empty/unsupported behavior, provenance ordering and
lineage rejection, and semantic component selection. It did not cover the
store's missing/invalid transition behavior, `PairInspector` zero-pair UI, or
store/component synchronization. Browser/manual sign-off was not attempted;
no browser result is claimed.

## Gate recommendation

Keep the valid-pair Split Heart available for synthetic/demo review. Do not
mark the M9 Compare contract fully complete until CMP-O1 is closed and the
store/component ownership decision in CMP-O2 is made and tested. CMP-O3 can be
closed as a documentation/schema-boundary item if pair-specific evidence is
intentionally unavailable.
