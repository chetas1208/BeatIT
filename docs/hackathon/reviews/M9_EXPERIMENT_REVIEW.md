# M9 Experiment Surface Review

Date: 2026-09-26  
Scope: causal explorer, plausible twins, Shadow Trial, and result freshness in
the M9 `EXPERIMENT` journey.

## Verdict

**OPEN — the experiment surface has substantive working pieces, but M9 is not
closed.** The backend ensemble and Shadow Trial authorities preserve lineage,
same-sample pairing, validation, persistence, and safety boundaries. The
frontend does not yet implement M9's complete artifact identity and
invalidation contract, so an earlier experiment can be presented again as if
it belonged to a later scenario revision.

## Pass findings

### EXP-1 — Causal exploration preserves the observed origin and states the safety boundary

**Pass.** The causal surface labels itself `HYPOTHETICAL SIMULATION` and says
that observed history is unchanged (`web/components/twin/scenario/ScenarioPanel.tsx:21-27`).
The scenario engine clones the source state, retains immutable origin metadata,
and emits a deterministic propagation result with graph/version, paths, source
references, warnings, and `deterministic: true`
(`web/lib/twin/scenario/propagation.ts:168-203,236-317`). The inspector exposes
the baseline snapshot, scenario ID, component deltas, provenance, and an
explicit non-diagnosis/non-treatment boundary
(`web/components/twin/scenario/ScenarioInspector.tsx:114-131,163-214`).

### EXP-2 — Active plausible-twin generation uses the backend authority

**Pass.** The production path requests `POST /twin/ensemble` and maps the
response; it does not use the quarantined local ensemble runner
(`web/lib/twin/scenario/useScenario.tsx:24-26,111-129`,
`web/lib/twin/ensemble/backend.ts:53-68`,
`web/lib/twin/ensemble/adapter.ts:5-64`). The backend validates sample counts,
sample lineage, representative IDs, distributions, provenance, and the
canonical disclaimer (`python/hearttwin/ensemble.py:242-315`). The panel
surfaces origin, seed, accepted/rejected counts, percentile summaries, and
explicit uncertainty/model-boundary language
(`web/components/twin/ensemble/PlausibleTwinsPanel.tsx:71-121`).

### EXP-3 — Shadow Trial pairing is identity-preserving and invalid pairs are not promoted

**Pass.** The backend applies one scenario to each stored baseline sample and
does not resample the population (`python/hearttwin/shadow_trial_engine.py:169-245,268-315`).
The contract validates pair identity, counts, status, metric coverage,
provenance, and the safety disclaimer
(`python/hearttwin/shadow_trial_contracts.py:192-227,349-398`). The UI reports
valid and invalid counts, retains rejection reasons, withholds effect
distributions when no valid pair exists, and only offers comparison for a
valid pair (`web/components/twin/shadow-trial/ShadowTrialPanel.tsx:131-149`).

### EXP-4 — The experiment surface does not fabricate pointwise PV uncertainty

**Pass.** The Shadow Trial panel explicitly says that M5.5 does not provide
pointwise PV samples and that the held baseline shape is not an uncertainty
envelope (`web/components/twin/shadow-trial/ShadowTrialPanel.tsx:146-149`).
This matches the M9 boundary that unavailable analysis remains unavailable.

## Open findings

### EXP-O1 — The causal explorer still recalculates physiology in the browser

**Open.** `useScenario` calls `propagateScenario` directly
(`web/lib/twin/scenario/useScenario.tsx:68-71`), and that module contains its
own baseline/evaluation/update formulas (`web/lib/twin/scenario/propagation.ts:108-190`).
M9 defines numerical physiology as a read-only authority that the product
composes, not a calculation to duplicate in the M9 frontend
(`docs/hackathon/M9_AGENT_PLAN.md:9-10`; `docs/hackathon/M9_PREFLIGHT.md:103-107`).
The existing M5.5 audit already records that the frontend evaluator diverges
from the Python evaluator (`docs/hackathon/M5_5_NUMERICAL_AUDIT.md:74-102`).
Until the causal result comes from the authoritative versioned seam, the UI
can disagree with the backend Shadow Trial for the same inputs.

### EXP-O2 — Scenario identity is not revision-safe

**Open.** Every scenario for a snapshot uses the same ID,
`scenario-${snapshot.id}` (`web/lib/twin/scenario/propagation.ts:236-241`),
even when parameter values change. M9 requires an edited scenario to create a
new immutable definition identity or input revision
(`docs/hackathon/M9_PRODUCT_STATE.md:162-172`). The current ID therefore
cannot distinguish two different causal definitions for the same origin.

### EXP-O3 — An old Shadow Trial can reappear after a scenario edit

**Open.** The frontend stores a trial only with `ensembleId` and `scenarioId`
and considers it current when those two values match
(`web/components/twin/shadow-trial/ShadowTrialPanel.tsx:82-92`). The trial
response contains a backend `fingerprint`, but the frontend does not use it as
a freshness guard. Changing a parameter clears the ensemble association, but
does not clear the stored trial (`web/lib/twin/scenario/useScenario.tsx:84-99`).
Because the scenario ID is snapshot-only and ensemble generation is independent
of the scenario, regenerating the same baseline ensemble can make the prior
trial pass the two-ID check and display as the current result. This violates
M9's required context key and scenario-change invalidation
(`docs/hackathon/M9_PRODUCT_STATE.md:120-140,204-222`).

### EXP-O4 — Prior results remain visible while a replacement request is loading

**Open.** Starting plausible-twin generation increments a revision but does
not clear the previous `ensembleSession` before awaiting the response
(`web/lib/twin/scenario/useScenario.tsx:111-129`); the panel continues rendering
the old ensemble while `loading` is true (`web/components/twin/ensemble/PlausibleTwinsPanel.tsx:77-123`).
Likewise, starting a Shadow Trial calls `closeComparison()` but does not clear
`trialRun` before the request, so the previous trial can remain rendered while
the replacement is in flight (`web/components/twin/shadow-trial/ShadowTrialPanel.tsx:94-127,141-151`).
M9 requires loading to avoid presenting an old value as current and requires a
new trial to remove or mark the previous trial stale
(`docs/hackathon/M9_PRODUCT_STATE.md:185-196,204-214,334-354`).

### EXP-O5 — Late Shadow Trial responses have no commit-time context guard

**Open.** Ensemble generation has a revision check before committing its
response (`web/lib/twin/scenario/useScenario.tsx:111-129`), but Shadow Trial
submission has no request ID, revision, context key, cancellation, or response
fingerprint check before `setTrialRun` (`web/components/twin/shadow-trial/ShadowTrialPanel.tsx:94-127`).
The M9 async contract requires the response to match the current request,
context key, parent IDs, and operation before visible commit
(`docs/hackathon/M9_PRODUCT_STATE.md:308-327`).

### EXP-O6 — Compare state is not invalidated when Experiment ancestors change

**Open.** The comparison store retains its trial and pair until explicit
`close()` (`web/lib/twin/comparison/store.ts:34-47`). Scenario edits and
ensemble resets do not call that close path; it is only called when starting a
new Shadow Trial (`web/components/twin/shadow-trial/ShadowTrialPanel.tsx:94-103`).
`AppShell` renders the stored comparison whenever it exists, without checking
the current origin, ensemble, scenario revision, trial fingerprint, or case
(`web/components/layout/AppShell.tsx:83-94,115-127`). A user can therefore
edit the Experiment and later open Compare with the old pair still visible,
contrary to M9's descendant invalidation rule
(`docs/hackathon/M9_PRODUCT_STATE.md:198-222`).

### EXP-O7 — Persisted artifacts are not rehydrated into the M9 journey

**Open.** The backend exposes persisted GET routes for ensembles and Shadow
Trials (`python/hearttwin/api.py:189-197,362-370`), but the active frontend
keeps the ensemble in `ensembleSession` and the trial in component-local
`trialRun`; neither is loaded on direct navigation or reload
(`web/lib/twin/scenario/useScenario.tsx:51-60`,
`web/components/twin/shadow-trial/ShadowTrialPanel.tsx:87-92`). The M9 audit
also records that artifact identity remains in memory and is not in the URL
(`docs/hackathon/M9_PREFLIGHT.md:150-158`). This leaves the required persisted
ensemble → scenario → trial chain unavailable after reload and prevents
fail-closed lineage validation.

### EXP-O8 — Evidence mounts the full plausible-twin workflow outside its owner

**Open.** `PlausibleTwinsPanel` is part of the Experiment surface
(`web/components/twin/scenario/ScenarioPanel.tsx:42-53`) and is also mounted as
the entire Evidence workspace (`web/components/layout/AppShell.tsx:128-130`).
M9 assigns scenario definition, ensemble workflow, and Shadow Trial to
`EXPERIMENT`; `EVIDENCE` may show a read-only summary but must not provide a
second editor or recompute the owner's result
(`docs/hackathon/M9_INFORMATION_ARCHITECTURE.md:36-40,64-73`).

## Verification evidence

- Frontend TypeScript check: `./node_modules/.bin/tsc --noEmit` — passed.
- Focused frontend ESLint for the reviewed paths — passed.
- Backend ensemble/Shadow Trial focused tests: **96 passed**, 8 existing
  deprecation warnings.
- Non-browser ensemble contract/runtime tests: **5 passed**.
- Browser/manual sign-off was not attempted for this review; no browser result
  is claimed.
