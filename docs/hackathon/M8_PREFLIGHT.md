# M8 Preflight — M5 through M7

Last updated: 2026-09-26

## M5 uncertainty authority

M5.5 persists each accepted sample's parameter vector, projection base,
deterministic outputs, distribution definitions, seed, source/evidence IDs,
prior/version metadata, and descriptive output distributions. Parameter
independence remains an explicit assumption; M8 must not call independent
distributions a learned joint model.

## M6 paired Shadow Trial authority

M6 consumes one persisted ensemble, applies a bounded scenario to each sample's
own stored parameters, retains sample identity, and persists canonical raw
scenario-minus-baseline deltas. M8 can analyze those parameter vectors and
paired deltas, but must not resample or recompute an unrelated frontend result.

## M7 readiness boundary

M7 now has two independently mounted heart renderers, a pure comparison clock,
semantic selection, canonical delta presentation, PV cursor context, and
provenance labels. Automated TypeScript and focused comparison tests pass.
Browser/WebGL, assistive technology, and machine-specific performance evidence
remain open because the local Chromium environment lacks `libasound.so.2` and
Firefox is unavailable. This is recorded as an inherited validation blocker;
M8 does not claim M7 completion or silently expand M7 to resolve it.

## M8 binding rules

1. Tier 1 is deterministic finite perturbation/sensitivity plus explicit
   uncertainty-impact scoring. Any `sensitivity × uncertainty` score is named
   an uncertainty-impact heuristic, not expected information gain.
2. Evidence ranking is target-specific and uses explicit mapping rationale,
   completeness, freshness, and parameter relevance.
3. A local/external model may explain results only. M8 mathematics works with
   model use disabled.
4. M8 outputs are educational research projections, not diagnosis, treatment,
   medical necessity, or guaranteed measurement value.
