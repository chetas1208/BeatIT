# M6 Explanation Grounding Review

Date: 2026-09-26  
Scope: M6 Shadow Trial warnings, provenance copy, pair explanations, and
effect-category language. This is a read-only review; no implementation files
were changed.

## Verdict

**Pass for the reviewed M6 explanation boundary.** The Shadow Trial surface
describes an already-computed deterministic paired result. Its visible
explanations are fixed UI copy, backend warnings, pair identifiers, provenance,
and status text. The reviewed path does not call a model provider and does not
ask a model to calculate physiology, deltas, quantiles, categories, or units.

The result remains a bounded educational simulation. Direction labels such as
positive, near-zero, and negative describe the sign of a simulation delta only;
they are not claims of benefit, harm, diagnosis, treatment response, efficacy,
or clinical evidence.

## Evidence reviewed

| Boundary | Evidence | Finding |
|---|---|---|
| Scenario and trial copy | `web/components/twin/shadow-trial/ShadowTrialPanel.tsx:125-139` | Fixed copy identifies a paired hypothetical experiment, same-sample pairing, no resampling, PV limitations, provenance, and the non-clinical boundary. |
| Pair explanation | `ShadowTrialPanel.tsx:59-74` | The inspector displays stored baseline/scenario state, pair IDs, the stored-parameter/no-new-draw statement, and backend rejection reasons. It does not derive a new clinical interpretation. |
| Effect explanation | `ShadowTrialPanel.tsx:31-49` | The UI formats backend median/quantile values and counts. Category text explicitly says “descriptive simulation categories only.” |
| Failure/status text | `ShadowTrialPanel.tsx:82-87,112-115,130,134-135` | Empty prerequisites, request failure, invalid-pair retention, zero-valid-pair failure, and unavailable distributions are presented as status or alert text. No fallback explanation invents a result. |
| Numerical authority | `python/hearttwin/shadow_trial_engine.py:114-144` | Scenario application reuses the Python canonical evaluator and persisted sample projection base. The engine emits deterministic derived values and a bounded hypothetical-simulation warning. |
| Effect authority | `python/hearttwin/shadow_trial_metrics.py` and `python/hearttwin/shadow_trial_contracts.py:243-298` | Deltas, quantiles, units, tolerances, and sign counts are backend-owned and contract-validated. |
| Model boundary | `python/hearttwin/shadow_trial_engine.py:1-33` and the reviewed M6 frontend path | No model-provider or LLM call is present in the trial engine, metrics path, contracts, API response mapping, or Shadow Trial panel. |

## Deterministic explanation rules

The reviewed M6 surface must preserve these rules:

1. Render labels and warnings from fixed copy or returned metadata; do not
   synthesize a clinical narrative from a delta.
2. Treat scenario labels, descriptions, pair IDs, provenance, warnings, and
   status as metadata about the computation, not as additional physiology.
3. Treat `scenario - baseline` values, units, quantiles, tolerances, and
   positive/near-zero/negative counts as backend-owned results. The frontend may
   format them but must not recalculate or reinterpret them.
4. Keep invalid-pair reasons visible and keep zero-valid-pair output as a
   failure/empty result. Never replace missing or invalid values with a
   plausible-sounding explanation.
5. Preserve the visible `HYPOTHETICAL SIMULATION` and
   `not clinical advice or treatment guidance` boundary on completed results.

## Prohibited explanation drift

The following would fail this boundary and require a new review:

- A model-generated number, formula, percentile, category, unit, or canonical
  state value.
- Copy such as “improves,” “worsens,” “safe,” “effective,” “recommended,” or
  “beneficial” when it is inferred from a direction category rather than
  returned as neutral simulation metadata.
- Treating a positive delta as treatment benefit, a negative delta as harm, or
  a near-zero delta as clinical stability.
- Filling an unavailable PV comparison, invalid pair, or empty distribution
  with estimated or model-generated content.
- Hiding the synthetic-origin, provenance, warning, or safety disclaimer.
- Introducing M7 Split Heart or M8 Missing Piece explanation flows.

## Review conclusion

M6 explanation grounding is **PASS**, subject to preserving the reviewed
backend-authority and copy-only presentation boundary. This review does not
claim clinical validation, treatment utility, or model-provider safety for
unrelated Copilot surfaces. M7 and M8 remain out of scope.

