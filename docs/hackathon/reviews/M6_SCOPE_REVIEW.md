# M6 Scope and Documentation Review

Date: 2026-09-26  
Scope: substantive review of the M6 documentation, root decision/progress
records, implemented M6 files, and the explicit M7/M8 boundary. This review
adds only this report; no implementation files were edited.

## Verdict

**M6 implementation scope is contained, but the documentation set is not yet
internally consistent.** The active code implements a bounded same-sample
Shadow Trial over one persisted ensemble, with backend numerical authority,
durable trial storage, API projections, and a scalar frontend inspection
surface. The source audit found no M7 Split Heart or M8 Missing Piece
implementation. However, several M6 records still contain pre-repair claims or
conflicting totals and should not be used as a single completion authority.

## Evidence executed

Current workspace checks:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  pytest -q python/hearttwin/tests/test_shadow_trial_*.py
40 passed, 8 warnings

PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  pytest -q
943 passed, 1 skipped, 461 warnings

cd web && npx tsc --noEmit
PASS

cd web && npm run test:runtime
5 passed, 0 failed

cd web && npm run lint
0 errors, 2 existing warnings
```

The implementation audit found:

- [`shadow_trial_engine.py`](../../../python/hearttwin/shadow_trial_engine.py#L169-L239)
  sorts baseline samples, copies each sample's parameters, calls the canonical
  M5.5 evaluator, and creates a trial-namespaced scenario ID. No sampler or
  second ensemble is used in this path.
- [`api.py`](../../../python/hearttwin/api.py#L235-L295) exposes create, full
  retrieval, effects, and pair retrieval routes. The effects and pair routes
  have typed response models, persisted results are revalidated, and the M6
  error handlers add the canonical disclaimer.
- [`ShadowTrialPanel.tsx`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L79-L143)
  renders backend results and does not calculate cardiac physiology or paired
  effect statistics. It adds one panel to the existing scenario surface; no
  second heart or split viewport is mounted.
- A repository search across `python/` and `web/` found no active M7 Split
  Heart or M8 Missing Piece implementation. Future-milestone mentions are in
  documentation and explanatory limitation text, not executable M7/M8
  surfaces.

## Findings

### F-01 — Completion test totals are stale and conflict with Progress

**Severity: P1 documentation integrity.**

[`M6_COMPLETION.md:36-49`](../M6_COMPLETION.md#L36-L49) reports 39 focused
tests and 929 full-suite tests. The current focused run reports 40 tests, and
the current full run reports 943 passed with one skipped. [`Progress.md:46-48`](../../Progress.md#L46-L48)
also reports 929 for the full suite while [`Progress.md:84-90`](../../Progress.md#L84-L90)
reports 40 focused tests. The completion record and root progress record
therefore cannot both be the current evidence summary.

Recommendation: update the completion record and root progress to the same
dated command results, and distinguish current results from historical
snapshots when a later run changes the count.

### F-02 — Contribution totals and campaign labels do not reconcile

**Severity: P1 documentation integrity.**

[`M6_COMPLETION.md:62-63`](../M6_COMPLETION.md#L62-L63) says that 21
non-duplicative contributions are evidenced. The dispatch ledger in
[`M6_AGENT_PLAN.md:75-107`](../M6_AGENT_PLAN.md#L75-L107) contains 31 rows marked
`Counted: yes` and two explicitly uncounted duplicate rows. The ledger summary
at [`M6_AGENT_PLAN.md:109-110`](../M6_AGENT_PLAN.md#L109-L110) and root
[`Progress.md:87-90`](../../Progress.md#L87-L90) now describe 31 cumulative
contributions, while also using a separate “21 completed in this campaign
wave” label that is not self-evident from the row grouping.

The 20-contribution gate may be met, but the documents do not define whether
21 is a campaign-only count, 31 is cumulative, or which rows belong to each
set. Recommendation: name the campaign boundary, state the cumulative and
non-duplicative totals once, and link each counted row to its evidence.

### F-03 — Workstream status is stale inside the authoritative M6 plan

**Severity: P1 coordination/documentation integrity.**

The gate checklist in [`M6_AGENT_PLAN.md:113-129`](../M6_AGENT_PLAN.md#L113-L129)
marks contracts, engine, persistence, API, frontend, performance, and reviews
complete. The workstream table immediately above it still labels the same
areas as “scaffold present,” “pending,” or “integration pending” at
[`M6_AGENT_PLAN.md:38-69`](../M6_AGENT_PLAN.md#L38-L69). For example, the API
workstream is pending even though the four routes are implemented in
`python/hearttwin/api.py`, and the frontend workstream is pending even though
`ShadowTrialPanel.tsx` is mounted and the frontend checks pass.

Recommendation: mark each completed workstream as complete, leave only the
browser/accessibility and explicitly bounded limitations open, and preserve
the old scaffold wording in a dated historical subsection if it is useful.

### F-04 — Historical reviews are not consistently separated from current gate state

**Severity: P1 documentation clarity.**

Several reports correctly preserve pre-repair evidence, but their current
verdicts remain easy to misread:

- [`M6_PREFLIGHT.md:157-218`](../M6_PREFLIGHT.md#L157-L218) says the API and
  persistence integration did not exist, while its post-preflight note at
  [`M6_PREFLIGHT.md:227-236`](../M6_PREFLIGHT.md#L227-L236) says those seams were
  subsequently integrated. The same note still says the 20-contribution gate
  is a remaining blocker, which conflicts with the current ledger summary.
- [`M6_API_REVIEW.md:10-18`](M6_API_REVIEW.md#L10-L18) and
  [`M6_API_REVIEW.md:233-239`](M6_API_REVIEW.md#L233-L239) retain a FAIL verdict,
  while its post-review resolution at [`M6_API_REVIEW.md:241-249`](M6_API_REVIEW.md#L241-L249)
  says the disclaimer handlers, typed projections, and persisted-result
  validation were added. The current `api.py` contains those repairs.
- [`M6_FRONTEND_REVIEW.md:202-216`](M6_FRONTEND_REVIEW.md#L202-L216) similarly
  retains conditional pre-repair findings while its resolution records the
  stale-result and invalid-pair repairs.

Recommendation: add a prominent “historical pre-repair snapshot” label to
those verdict sections, or add a current post-repair verdict beside them. Do
not leave a report that says FAIL without making its superseded status obvious.

### F-05 — Performance documentation still specifies the obsolete pair-ID form

**Severity: P2 contract/documentation drift.**

[`M6_PERFORMANCE.md:149-151`](../M6_PERFORMANCE.md#L149-L151) calls
`scenario-{baseline_sample_id}` the expected current convention. The active
engine uses `scenario_sample_id(trial_id, sample.id)` at
[`shadow_trial_engine.py:226-229`](../../../python/hearttwin/shadow_trial_engine.py#L226-L229),
and [`M6_DECISIONS.md:6-10`](../M6_DECISIONS.md#L6-L10) explicitly specifies
the trial-namespaced form `<trial_id>-scenario-<baseline_sample_id>`.

Recommendation: update the benchmark/reproducibility document to the namespaced
form and identify the compact helper form as historical or test-only.

### F-06 — Provenance design is partially implemented, not a full closure claim

**Severity: P2 scope/credibility wording.**

The historical framing in [`M6_PROVENANCE.md:1-8`](../M6_PROVENANCE.md#L1-L8)
and its current implementation note are directionally correct, but the
acceptance table still identifies fields such as an origin-state digest and
explicit baseline schema reference as missing at
[`M6_PROVENANCE.md:40-63`](../M6_PROVENANCE.md#L40-L63). The implemented
`ShadowTrialProvenance` does carry a schema version, engine version, pairing
policy, and scenario hash, but its fields at
[`shadow_trial_contracts.py:112-134`](../../../python/hearttwin/shadow_trial_contracts.py#L112-L134)
do not establish every stronger provenance objective in that audit, such as an
explicit origin-state digest.

This does not exceed M6 scope, and the completion record already lists trusted
demo persistence and synthetic-only limitations. Recommendation: describe
provenance as “implemented with bounded lineage limitations,” not as complete
provenance closure, unless the missing fields are intentionally waived and
recorded as such.

## M7/M8 boundary assessment

The boundary is substantively respected:

- M6 documents explicitly exclude Split Heart, Missing Piece, sensitivity and
  information-gain ranking, treatment ranking, clinical calibration, and
  redesign in [`M6_COMPLETION.md:65-69`](../M6_COMPLETION.md#L65-L69) and
  [`M6_ARCHITECTURE.md:44-50`](../M6_ARCHITECTURE.md#L44-L50).
- The active frontend adds only `ShadowTrialPanel` below the existing scenario
  and plausible-twin panels. It has scalar effect summaries, pair inspection,
  and an explicit unavailable PV boundary; it does not add a second heart,
  split viewport, anatomical inference, or a Missing Piece workflow.
- The backend has no M7/M8 routes, evaluators, or ranking code. References to
  those milestones found by search are documentation, future-boundary text, or
  unrelated general language such as imaging sensitivity metrics.

The scope conclusion is therefore **PASS for no M7/M8 leakage**. This is
separate from the documentation consistency findings above and does not promote
M6 to complete or authorize M7.

## Required documentation actions

1. Reconcile current test totals in `M6_COMPLETION.md` and `Progress.md`.
2. Define cumulative versus campaign-only contribution counts and update the
   completion record.
3. Bring the M6 workstream status table into agreement with its gate checklist.
4. Label pre-repair reviews as historical and state their superseding current
   verdicts.
5. Correct the obsolete pair-ID convention in `M6_PERFORMANCE.md`.
6. Keep provenance and browser/accessibility limitations explicit; do not
   infer full closure from passing automated tests.

No implementation change is required by this scope review.
