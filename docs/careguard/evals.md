# CareGuard — Evals & Success Metrics

## Regression (existing DualBeat)
Route-table snapshot, baseline formulas, agent IDs, and pages are asserted unchanged;
flag-off behavior equals baseline (`test_careguard_isolation.py`, `verify:careguard`).

## CareGuard tests (`python/hearttwin/tests/careguard/`)
Isolation, config/secret, deidentification, FHIR parse/provenance, full staged
pipeline, and the medication-safety golden + unit suite (normalization, label-backed
conflicts, report-mention NLP, alternatives, critic, source policy, DrugBank license,
no-Kaggle).

## Instrumented workflow metrics
medications normalized · ambiguities · active conditions reviewed · report mentions
(detected/confirmed/rejected) · drug–drug / drug–disease / allergy conflicts ·
duplications · monitoring gaps · label & guideline evidence coverage · alternatives
considered/excluded · unsupported alternatives blocked · clinician accept/reject/
override · pharmacist-review requests · review time · source & model latency.

We do not claim clinical-outcome improvement.
