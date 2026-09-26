# M6 Frontend Experiment-Surface Review

Date: 2026-09-26  
Scope: read-only review of the M6 Shadow Trial frontend surface, its wire
types/API client, ScenarioPanel integration, accessibility semantics, and the
backend numerical-authority boundary. No implementation files were changed by
this review.

## Verdict

**CONDITIONAL PASS for a local/demo experiment surface; not a complete frontend
gate.** The panel is correctly mounted in the existing scenario workflow and
does not calculate cardiac physiology, paired deltas, quantiles, tolerances, or
direction categories in TypeScript. The backend response remains the numerical
authority. However, the panel has state-lifecycle and persistence gaps that can
make a previously returned trial look current after the user changes the
scenario, and the frontend does not yet rehydrate a persisted trial through the
GET APIs.

The remaining issues are frontend contract/lifecycle issues. They do not
authorize M7 Split Heart, M8 Missing Piece, a second heart, or a new numerical
model.

## Evidence reviewed

| Surface | Evidence | Assessment |
| --- | --- | --- |
| Experiment panel | [`ShadowTrialPanel.tsx`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L79-L145) | Client state is limited to request status, loading, and the returned trial; the visible values are response data. |
| Scenario integration | [`ScenarioPanel.tsx`](../../../web/components/twin/scenario/ScenarioPanel.tsx#L20-L55) | The panel is mounted after the plausible-twin panel inside the existing M4 scenario branch. It is not rendered as a separate heart or M7/M8 surface. |
| API client | [`api.ts`](../../../web/lib/api.ts#L100-L132), [`api.ts`](../../../web/lib/api.ts#L201-L225) | Requests use the shared error-preserving client, encode path IDs, and expose create/get-trial/get-pair methods. |
| Wire types | [`shadow-trial.ts`](../../../web/types/shadow-trial.ts#L3-L84) | Main pair/distribution fields are represented, but the result type omits the backend `definition` object and weakens provenance to `Record<string, unknown>`. |
| Backend route | [`api.py`](../../../python/hearttwin/api.py#L207-L272) | POST loads one persisted ensemble, runs the backend engine, persists the result, and GET routes read the stored result. |
| Backend engine | [`shadow_trial_engine.py`](../../../python/hearttwin/shadow_trial_engine.py#L114-L145), [`shadow_trial_engine.py`](../../../python/hearttwin/shadow_trial_engine.py#L163-L229) | Scenario application uses persisted `projection_base`/sample parameters and canonical Python evaluation; pair deltas are computed server-side. |

## Backend-authority boundary

### Passing controls

1. The panel requests an explicit scalar allowlist: EF, SV, CO, HR, and MAP
   ([`ShadowTrialPanel.tsx:10-16`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L10-L16)). It does not request the unavailable PV-loop-area metric.
2. The request carries the existing M4 scenario definition as declarative
   input ([`ShadowTrialPanel.tsx:92-110`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L92-L110)). The browser does not use its own propagation result to produce the
   Shadow Trial values.
3. The panel formats returned medians, quantiles, category counts, and pair
   values. Its only numeric calculation is a visual percentile-bar width
   ([`ShadowTrialPanel.tsx:31-48`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L31-L48)); this does not feed back into physiology or effect data.
4. The backend validates the scenario origin against the persisted ensemble,
   applies the change to each corresponding sample, and derives deltas from
   backend outputs ([`shadow_trial_engine.py:163-229`](../../../python/hearttwin/shadow_trial_engine.py#L163-L229)). This is the correct authority boundary.
5. The PV notice explicitly says pointwise PV samples are unavailable and that
   the UI does not fabricate an uncertainty envelope
   ([`ShadowTrialPanel.tsx:137`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L137)).

### Boundary risks to preserve

- `ShadowTrialMetricId` still includes `pv_loop_area_index`
  ([`shadow-trial.ts:3-11`](../../../web/types/shadow-trial.ts#L3-L11)). The active
  panel correctly excludes it, but any future generic metric picker must use a
  backend capability response or an explicit supported-metric allowlist rather
  than treating the union as proof that PV comparison is available.
- The frontend constructs a request from the local M4 result. That is safe only
  because the backend revalidates origin, bounds, units, sample availability,
  and canonical execution. The M4 result must remain request metadata, never a
  second numerical authority.

## Findings

### P1 — A completed trial can become stale without being marked stale

`ShadowTrialPanel` stores the last response locally and has no dependency on the
current ensemble ID, scenario definition ID, or scenario fingerprint beyond the
request moment ([`ShadowTrialPanel.tsx:79-119`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L79-L119)). Meanwhile, `useScenario` clears/replaces the ensemble when the user changes parameters, experiments, resets, undoes, or redoes ([`useScenario.tsx:73-105`](../../../web/lib/twin/scenario/useScenario.tsx#L73-L105), [`useScenario.tsx:147-157`](../../../web/lib/twin/scenario/useScenario.tsx#L147-L157)). Those transitions do not clear or invalidate the panel's `trial` state.

Result: after changing the scenario, the old effect distributions and pair
inspection remain visible until the next request succeeds. If a request is
in-flight while the user changes the scenario, its response can also populate
the panel after the inputs have changed. The status text does not identify the
result as stale.

Recommended closure: bind displayed results to the submitted ensemble ID and
scenario definition/fingerprint; clear or visibly mark the result stale on
dependency changes; and guard late responses (or cancel them) when a newer
scenario supersedes the request.

### P1 — Persistence exists in the API but is not reachable from the experiment surface

The client exposes `getShadowTrial` and `getShadowTrialPair`
([`api.ts:219-225`](../../../web/lib/api.ts#L219-L225)), and the backend stores
the POST result before returning it ([`api.py:207-225`](../../../python/hearttwin/api.py#L207-L225)). The panel only calls `createShadowTrial` and never uses either GET method ([`ShadowTrialPanel.tsx:90-111`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L90-L111)).

Therefore a refresh, route remount, or handoff containing only a trial ID cannot
restore the experiment in the current UI. This weakens the user-visible claim
of durable M6 persistence, even though the backend storage/API gate exists.

Recommended closure: provide a narrow persisted-trial load path (for example,
when a trial ID is supplied by the surrounding workflow) and render the loaded
result with the same provenance/safety treatment. Do not reconstruct it from
browser state.

### P1 — Pair selection is not reconciled when a new trial replaces the old one

`PairInspector` initializes `selectedId` only once from the first response
([`ShadowTrialPanel.tsx:53-56`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L53-L56)). The parent can replace `trial` after another run, but the select's controlled value can still reference a sample ID from the previous trial. The rendered pair falls back to the first new pair while the select can show no matching option, creating an identity mismatch for keyboard and screen-reader users.

Recommended closure: reconcile selection whenever the trial ID or pair IDs
change, defaulting deterministically to the first returned pair; add a runtime
case for replacement with disjoint sample IDs.

### P2 — Empty-distribution copy is inaccurate for a completed response

The result branch shows a failure message when `status === "failed"`, which is
good, but the fallback at
[`ShadowTrialPanel.tsx:134-135`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L134-L135) says distributions are unavailable “until at least one pair passes validation.” That message is also used when `valid_pairs > 0` but the server returns an empty distribution list. In that case a pair has already passed, so the text misstates the response contract.

Recommended closure: distinguish `status === "failed"`/zero valid pairs from a
completed response with no returned metrics, and say explicitly that the
backend returned no effect distributions for the selected metrics. Never imply
that an empty result means zero effect.

### P2 — Invalid pairs retain scalar-looking state cards

The panel correctly retains invalid pairs and announces their rejection reason
([`ShadowTrialPanel.tsx:67-75`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L67-L75)). It nevertheless renders baseline and scenario EF/SV/CO cards before the invalid alert. Because an invalid pair can contain copied/partial state for diagnostic inspection, those cards can be mistaken for a valid comparison.

Recommended closure: label the cards as retained diagnostic payload, or show
the metric values as unavailable for invalid pairs while keeping the rejection
reasons visible. Do not infer a delta from the retained state.

### P2 — Frontend response types under-specify persisted lineage

`ShadowTrialResponse` declares `provenance` as `Record<string, unknown>` and
does not declare the backend's optional `definition` field
([`shadow-trial.ts:64-78`](../../../web/types/shadow-trial.ts#L64-L78),
[`shadow_trial_contracts.py:301-319`](../../../python/hearttwin/shadow_trial_contracts.py#L301-L319)). This is structurally permissive but loses compile-time protection for
origin quality, seed, physiology/ensemble/prior versions, pairing policy, and
scenario identity—the exact fields needed to explain a persisted trial.

Recommended closure: type the returned provenance and definition explicitly,
or generate/validate the DTO from the backend contract. Keep unknown warning
strings display-only and never use them as authority.

## Accessibility review

### Passing semantics

- The run control is a native `button` with a visible loading label and disabled
  state ([`ShadowTrialPanel.tsx:121-130`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L121-L130)).
- Request status is a live region, and request failures use `role="alert"`
  ([`ShadowTrialPanel.tsx:130`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L130)).
- The pair selector is a native `select` inside a native `label`
  ([`ShadowTrialPanel.tsx:60-66`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L60-L66)).
- The pair section has an accessible heading, the distribution list has an
  accessible label, and the decorative percentile bar is `aria-hidden`
  ([`ShadowTrialPanel.tsx:37-48`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L37-L48), [`ShadowTrialPanel.tsx:59-60`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L59-L60)).
- Invalid-pair rejection reasons are placed in an alert, and provenance is
  available in a native `details`/`summary` disclosure
  ([`ShadowTrialPanel.tsx:73-74`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L73-L74), [`ShadowTrialPanel.tsx:138`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L138-L139)).

### Accessibility follow-ups

- The hard-coded `id="shadow-pair-title"` can duplicate if the panel is ever
  mounted more than once. A generated ID would keep `aria-labelledby` valid in
  multi-surface layouts.
- The panel has no `aria-busy` state around the full result region, so a screen
  reader receives the status update but not an explicit busy relationship for
  the result it is replacing.
- Static review cannot validate focus behavior after results arrive, the
  visibility/contrast of the tiny text, or the stale-selection problem in a
  real assistive technology session. A browser/axe pass remains outstanding.

## M7/M8 and single-heart boundary

The reviewed integration adds one panel below the existing scenario and
plausible-twin panels. It does not add a split viewport, second canvas, missing-
piece workflow, anatomical inference, or a new PV visualization. The visible
boundary is explicit: “PAIRED HYPOTHETICAL EXPERIMENT,” “no new draw,” synthetic
origin labeling, and “not clinical advice or treatment guidance” are present in
the active panel ([`ShadowTrialPanel.tsx:125-139`](../../../web/components/twin/shadow-trial/ShadowTrialPanel.tsx#L125-L139)).

## Verification evidence

Commands run from `web/` on 2026-09-26:

```text
npx tsc --noEmit
PASS (exit 0)

npm run test:runtime
PASS — 5 tests, 5 passed, 0 failed

npm run lint
PASS — 0 errors, 2 existing warnings in components/careguard/cases/CaseDetail.tsx

npm run build
PASS — Next.js 16.2.7 production build; routes generated successfully
```

No implementation file was edited. No browser or axe audit was run because the
repository's available `test:runtime` script is a Node runtime suite and there
is no configured browser accessibility command in the reviewed frontend scripts.

## Gate recommendation

Keep the current surface for controlled local/demo review because its numerical
authority and safety boundary are sound. Before declaring the M6 frontend gate
complete, close the stale-result/request-race issue, reconcile pair selection,
correct the empty-distribution state, and type/use persisted trial lineage. A
browser accessibility pass should then verify focus and live-region behavior.

## Post-review resolution

The lead now binds displayed results to the submitted ensemble/scenario IDs,
reconciles pair selection through the active pair fallback, and suppresses
scalar comparison cards for invalid pairs. Persisted GET endpoints remain
available for a future explicit rehydration entry point; the current panel does
not pretend to restore a trial from stale browser state. Browser/axe validation
is still open.
