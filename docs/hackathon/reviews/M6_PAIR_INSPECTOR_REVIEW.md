# M6 Pair Inspector Review

Date: 2026-09-26  
Scope: read-only review of the M6 paired-twin contract, pair retrieval route,
and `ShadowTrialPanel`. No implementation files were changed. M7 Split Heart
and M8 Missing Piece are out of scope.

## Verdict

The pair inspector is directionally correct for the current demo: it selects a
stored baseline sample, shows the corresponding scenario state, retains and
displays invalid-pair reasons, and states that no scenario resampling occurred.
The API route and focused tests also preserve the safety disclaimer.

The surface is **CONDITIONAL**, not a complete audit-grade pair inspector. The
main remaining issues are that the displayed identity is not bound to the
trial/scenario digest, the contract does not validate all duplicated pair
fields against one another, and invalid/empty pairs can be displayed without a
clear metric-level comparison state.

## Evidence executed

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  pytest -q \
  python/hearttwin/tests/test_shadow_trial_api.py \
  python/hearttwin/tests/test_shadow_trial_contracts.py \
  python/hearttwin/tests/test_shadow_trial_engine.py \
  python/hearttwin/tests/test_shadow_trial_identity.py \
  python/hearttwin/tests/test_shadow_trial_store.py

30 passed, 8 warnings in 1.54s
```

The frontend TypeScript check also passed:

```text
./node_modules/.bin/tsc --noEmit
exit code 0
```

The checked tests cover route creation/retrieval, missing pair resources,
invalid baseline retention, no-op immutability, deterministic ordering, and
the standalone identity helper. They do not cover all UI state transitions or
tampered cross-field pair payloads.

## Findings

### 1. Pair identity is understandable but not fully trial-bound — P1

The backend contract requires `baseline_twin_id == sample_id` and requires a
different `scenario_twin_id` (`python/hearttwin/shadow_trial_contracts.py:187-216`).
The engine then emits `scenario-{sample_id}`
(`python/hearttwin/shadow_trial_engine.py:208-218`). This is deterministic, but
the engine does not use the trial-namespaced form supported by
`scenario_sample_id(trial_id, sample_id)` (`python/hearttwin/shadow_trial_identity.py:40-63`).
The same sample ID can therefore receive the same scenario twin ID in multiple
trials, even when the scenario definition differs.

The route retrieves by `trial_id` and `sample_id` and returns the first matching
record (`python/hearttwin/api.py:250-261`). That is adequate for the current
unique-sample contract, but it does not independently verify a pair identity
against the requested trial, scenario digest, sample index, or parameter
digest.

The panel displays `sample_id ↔ scenario_twin_id`
(`web/components/twin/shadow-trial/ShadowTrialPanel.tsx:73`), which is useful
for a demo, but omits the explicit `baseline_twin_id`, scenario definition ID,
and any pair-level digest. A judge can see the naming convention but cannot
audit the complete identity from this surface.

Recommended closure:

- Bind `scenario_twin_id` to the trial/scenario identity, or expose a separate
  immutable pair identity object containing trial ID, sample ID/index, and
  scenario digest.
- Validate `baseline_parameters == parameters`, canonical units, and the
  scenario parameter digest in the contract.
- Add a route/UI test proving that a pair from trial A cannot be presented as a
  pair from trial B after identity fields are tampered.

### 2. Invalid reasons are retained and visible, but not structured — P1

Invalid pairs must contain at least one rejection reason in the Pydantic
contract (`shadow_trial_contracts.py:205-217`). The engine retains the pair and
excludes it from effect distributions while preserving the reason
(`shadow_trial_engine.py:200-229`). The API returns that full pair, including
`rejection_reasons`, and the panel renders the reasons in an alert
(`ShadowTrialPanel.tsx:73-74`). This is a correct no-silent-drop behavior.

The remaining weakness is presentation and contract precision:

- Reasons are free-form strings rather than stable reason codes plus human
  text, so clients cannot group or reliably localize failure classes.
- The engine can add a delta before a later metric fails. An invalid pair can
  consequently contain partial deltas, while the UI shows baseline and
  scenario scalar values without identifying which metric comparison failed.
- The panel does not show `delta_units`, `baseline_parameters`, or
  `scenario_parameters`, so the inspector cannot prove which latent values
  changed for the selected pair.

Recommended closure:

- Use a bounded rejection-code vocabulary with an optional detail string.
- Make invalid pairs carry no effect deltas, or add explicit per-metric status
  so partial data cannot be mistaken for a complete paired comparison.
- Display the changed parameter values and the exact unavailable metrics in the
  inspector.

### 3. Runtime immutability is protected, but persisted lineage is incomplete — P1

The engine deep-copies the baseline state before constructing the pair and the
no-op test verifies that running a trial does not mutate the ensemble. The
Shadow Trial store is create-once/idempotent, and the panel is read-only. These
are positive controls.

The contract models themselves are not frozen: `PairedTwinResult` uses the
default mutable Pydantic configuration (`shadow_trial_contracts.py:187-203`).
More importantly, the result records only `baseline_ensemble_id` and copied
states/parameters. It does not carry a baseline content digest, sample index,
or per-pair parameter digest. The M5.5 ensemble store remains replaceable by ID
(`python/hearttwin/storage/ensemble_store.py:88-115`). Therefore, a later
replacement under the same ensemble ID can make the referenced baseline differ
from the baseline used to create the trial without the pair inspector showing
that mismatch.

Recommended closure:

- Persist and display a baseline ensemble content digest and pair parameter
  digest in provenance/identity.
- Verify the digest when loading a trial's baseline or explicitly reject a
  changed baseline record.
- Add tests that mutate a retrieved baseline payload after trial creation and
  assert a deterministic mismatch rather than silent reuse.

### 4. Missing edge cases in the inspector — P1/P2

The following cases are not fully represented by the current UI or focused
tests:

1. **Trial replacement in the same mounted panel.** `selectedId` is initialized
   only once from the first trial (`ShadowTrialPanel.tsx:53-55`). If a new trial
   arrives with different sample IDs, the fallback may show the first pair while
   the select value still references the old ID. The selection should reset or
   be reconciled when `trial.id`/`paired_results` changes.
2. **Zero requested pairs.** The panel now has an explicit failed/no-effects
   message (`ShadowTrialPanel.tsx:131-136`), but `PairInspector` returns `null`
   without an explicit “no pairs available” state (`:53-56`). This is a silent
   omission in the pair-specific surface.
3. **Invalid pair scalar display.** An invalid pair can still render both state
   cards. The scenario state may be a copied baseline placeholder, but the cards
   do not mark each metric as unavailable or placeholder data. The alert is
   present, yet the visual comparison remains easy to misread as valid.
4. **Duplicate or malformed IDs at the client boundary.** The backend validates
   unique sample IDs in a result (`shadow_trial_contracts.py:318-325`), but the
   panel assumes unique `sample_id` keys and does not surface a malformed
   payload. A defensive empty/error state would be safer for a persisted record
   that fails validation before rendering.
5. **Exact delta inspection.** The panel shows EF, SV, and CO values but not the
   corresponding scenario-minus-baseline deltas. A reviewer must mentally
   subtract values and cannot see units or tolerance classification for the
   selected pair.

## Positive controls to preserve

- Pair lookup is scoped by trial ID and returns 404 for a missing trial or pair.
- Safety disclaimers are asserted on creation and retrieval route tests and are
  returned by the pair endpoint.
- The UI states “no new draw is made” and identifies the surface as a
  hypothetical simulation, not treatment guidance.
- Invalid pairs remain inspectable instead of being silently filtered.
- M5.5 PV comparison limits remain visible; the inspector does not fabricate a
  pointwise PV comparison.

## Gate recommendation

Keep the current pair inspector available for synthetic/demo review, but do not
mark the M6 pair-inspection gate fully complete until the P1 identity and
lineage gaps are closed and the edge-case tests cover trial changes, zero
pairs, invalid metric display, and tampered pair fields. No M7 or M8 work is
required for this review.
