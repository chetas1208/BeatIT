# M8 Missing Piece Completion

Status: **COMPLETE — Tier-1 scope**  
Date: 2026-09-26

## Delivered

- Bounded, deterministic local finite-difference sensitivity over persisted M5.5
  projection bases.
- Distribution-aware q05/q95 parameter spread and an explicitly named
  uncertainty-impact heuristic.
- Same-sample M6 Shadow Trial-effect sensitivity with fixed absolute scenario
  targets.
- Versioned evidence taxonomy, freshness metadata, completeness reporting, and
  target-specific Evidence Priority Score ranking.
- Strict contracts that reject unsupported Sobol/Shapley labels, preserve
  unavailable reasons, retain units/configuration/provenance, and require the
  canonical safety disclaimer.
- Restart-safe SQLite persistence and `/api/v1/missing-piece` plus retrieval
  route. Shadow-effect requests reference an immutable persisted Shadow Trial.
- Accessible target selector, loading/empty/error/success states, sensitivity
  table, evidence rationale map, and scalar split-heart overlay boundary.

## Verification

```text
python -m pytest -q python/hearttwin/tests/test_missing_piece_*.py  77 passed
web vitest lib/twin/missing-piece/__tests__/inspectorModel.test.ts  2 passed
GET /api/v1/missing-piece/{id}/drivers + /evidence-ranking          route test passed
fixtures/golden/missing_piece/                                      9 cases (m8-golden-v1)
agent ledger                                 24 complete, reviewed, meaningful (IDs 04–19, 29–41)
```

## Explicit boundaries

M8 does not calculate Sobol, Morris, Shapley, posterior uncertainty, entropy
reduction, expected information gain, probabilities, confidence intervals,
diagnoses, treatments, or clinical measurement recommendations. Evidence
ranking is an Evidence Priority Score over reviewed model-proxy mappings.

Browser/WebGL, assistive-technology, and machine-specific visual performance
signoff remains blocked by the inherited environment limitation documented in
`M8_PREFLIGHT.md` and `M8_PERFORMANCE.md` (Chromium lacks `libasound.so.2` and
Firefox is unavailable). A successful build is not browser/accessibility
signoff.

M9, M10, and M10.5 were not started.
