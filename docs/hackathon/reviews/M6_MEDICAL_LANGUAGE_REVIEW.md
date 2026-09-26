# M6 Medical-Language Review

Date: 2026-09-26  
Agent: M6 agent #29  
Scope: M6 Shadow Trial backend warnings and contracts, API response safety
fields, the Shadow Trial panel, the shared frontend disclaimer, and M6 design
documentation. No implementation files were changed.

## Verdict

**PASS for the reviewed M6 surface.** No diagnosis, treatment, efficacy,
benefit, harm, recommendation, or clinical-validation claim is introduced as a
result of a Shadow Trial. The medical terms present in the reviewed path occur
in explicit safety boundaries such as “not diagnosis,” “not treatment advice,”
and “not clinical efficacy evidence.”

This is a language-boundary review only. It does not claim clinical validation,
medical-device status, patient-specific utility, or clearance, and it does not
clear unrelated M6 numerical, persistence, browser, or security gates.

## Evidence reviewed

| Surface | Evidence | Finding |
|---|---|---|
| Canonical safety contract | `python/hearttwin/safety.py:12-18,94-98` | The required educational-simulation disclaimer explicitly rejects diagnosis, treatment decisions, medical-device status, and medical advice. |
| M6 result warnings | `python/hearttwin/shadow_trial_engine.py:271-280` | Warnings call the result hypothetical, reject diagnosis/treatment/clinical-efficacy interpretation, identify synthetic replay data as non-patient evidence, and state that sign does not imply clinical value. |
| M6 contracts | `python/hearttwin/shadow_trial_contracts.py:1-7,301-339` | Contracts describe deterministic virtual simulation metadata, retain the canonical disclaimer on effect and pair projections, and do not encode clinical outcomes or recommendations. |
| M6 API | `python/hearttwin/api.py:234-280` and `python/hearttwin/tests/test_shadow_trial_api.py:50-79,105-116` | Create, retrieval, effects, pair, and tested error responses preserve the safety disclaimer. The API exposes computed records and warnings, not medical advice. |
| Effect panel | `web/components/twin/shadow-trial/ShadowTrialPanel.tsx:31-49,125-139` | The panel formats backend values and units, labels the experiment hypothetical, states that sign categories are descriptive simulation categories only, and shows the non-clinical boundary. |
| Pair inspector | `ShadowTrialPanel.tsx:53-74` | Baseline/scenario values, pair identity, stored-parameter reuse, and invalid reasons are shown without an inferred clinical interpretation. |
| Shared disclaimer | `web/components/safety/DisclaimerModal.tsx:61-67` | The frontend boundary says the application is educational, not a medical device, does not diagnose, and does not recommend treatment. |
| M6 documentation | `docs/hackathon/M6_EFFECT_METRICS.md:15-25`, `M6_QA.md:13-17`, and `M6_PROVENANCE.md` | Documentation defines descriptive statistics, rejects efficacy/probability interpretations, and prohibits treating positive/negative deltas as clinical evidence or treatment benefit/harm. |

## Sign-category review

The backend computes `scenario - baseline` and classifies each finite delta as
`positive`, `near-zero`, or `negative` using an explicit metric tolerance. The
frontend displays the returned counts and the phrase **“descriptive simulation
categories only.”** The categories therefore describe numeric direction in the
simulation; they do not mean:

- clinical improvement or worsening;
- treatment benefit, harm, or efficacy;
- safety, risk, prognosis, or eligibility; or
- a diagnosis, patient finding, or recommendation.

The M6 effect-metrics documentation also explicitly states that a positive
cardiac-output delta is not automatically medically better and a negative delta
is not automatically medically harmful. This is the correct interpretation
boundary and must remain attached to any future category visualization.

## Prohibited language drift

The following changes would fail this review and require a new audit:

- replacing “positive,” “near-zero,” or “negative” with “better,” “worse,”
  “benefit,” “harm,” “effective,” or “safe”;
- turning a scenario label into a treatment recommendation;
- describing a percentile range as efficacy, probability, confidence, or a
  patient-specific likelihood;
- presenting a valid pair as clinical evidence or a rejected pair as a
  diagnosis;
- removing the canonical disclaimer from a result, effect projection, pair
  projection, or error response; or
- adding model-generated medical interpretation to the deterministic effect
  values.

## Validation

- `python/hearttwin/tests/test_safety_language.py`: the repository safety tests
  cover the canonical disclaimer, blocked diagnosis/treatment requests, and
  required frontend safety wording.
- `python/hearttwin/tests/test_shadow_trial_api.py`: focused API tests verify
  the canonical disclaimer on create, full retrieval, effect retrieval, pair
  retrieval, and tested error responses.
- `git diff --check`: passed after adding this review.

## Conclusion

M6 medical-language and sign-category handling is **PASS** for the reviewed
backend, API, frontend, and documentation surfaces. Keep all sign labels
descriptive and preserve the explicit educational-simulation boundary. M7
Split Heart and M8 Missing Piece are out of scope.
