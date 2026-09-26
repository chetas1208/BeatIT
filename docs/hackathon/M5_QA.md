# M5 QA

Required checks:

- distribution validation and invalid-parameter rejection;
- same-seed replay and different-seed divergence;
- accepted/rejected sample accounting;
- deterministic physiology invariants for every accepted sample;
- quantile and variance calculations;
- provenance and version retention;
- API validation and repeated requests;
- UI representative-sample selection and labeling;
- M1–M4 regression, TypeScript, focused lint, and production build.

Browser, visual, and assistive-technology validation remain a separate gate.

## Current evidence

- Focused Python M5/API/cardio/model/schema regression: 141 passed, 0 failed,
  0 skipped; 29 non-blocking deprecation warnings.
- Full Python suite: 718 passed, 10 failed, 1 skipped. All failures are the
  known Python 3.13 event-loop compatibility failures in evaluator/validator
  tests; no M5 test failed.
- Frontend TypeScript, focused M5 ESLint, and production build: passed.
- Frontend runtime test attempt: blocked before assertions by unresolved `@/*`
  imports because no alias-aware runner is configured.
- Full frontend lint: 6 unrelated errors and 4 warnings in CareGuard/
  Disclaimer/Redis surfaces.
