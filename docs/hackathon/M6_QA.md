# M6 QA and Adversarial Review

## Completed checks

- Pairing: stable identity, order-independent execution, no resampling, and
  baseline immutability are covered by focused engine tests.
- Statistics: mean, median, quantiles, explicit units, and category counts are
  validated by the response contracts and golden vector.
- Cardiac modeling: M6 delegates to the versioned Python M5.5 evaluator;
  duplicate M4-style formulas were removed from the active engine.
- Persistence: restart-safe SQLite round trip, immutable IDs, and API retrieval
  are covered by focused tests.
- API safety: typed effects/pair projections, persisted-result revalidation, and
  disclaimer-bearing M6 errors are covered by focused tests.
- Medical language: UI and warnings use hypothetical/simulated language and
  retain the canonical safety disclaimer. No treatment ranking or efficacy
  claim is emitted.
- Security: persistence remains trusted-demo-only because authentication,
  restricted CORS, and hosted ownership controls are not part of M6.

## Environment-limited checks

Browser interaction, keyboard traversal, screen-reader behavior, and visual
responsive QA remain blocked by the missing browser executable/harness recorded
in the M5.5 gate. TypeScript, lint, and production build remain executable
checks.

The frontend review also identified persisted-trial rehydration as a future
surface improvement. The current panel now invalidates stale local results when
the ensemble or scenario changes; it does not silently reconstruct a trial from
browser state.
