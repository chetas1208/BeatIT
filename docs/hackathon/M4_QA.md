# M4 QA record

## Completed review passes

- Contract review: observed snapshot fields, provenance, and existing M3
  timeline APIs were inspected before scenario implementation.
- Physiology review: existing formulas and units are recorded in
  `M4_PHYSIOLOGY_AUDIT.md`; the known PV afterload limitation is not hidden.
- Immutability review: fork, origin metadata, and scenario history are detached
  value operations.
- Model boundary review: registry startup path has no torch/MONAI imports and
  model failure cannot block deterministic operation.

## Required validation

Run the TypeScript compiler, ESLint, focused Python model tests, and the full
Python suite before calling M4 complete. A production build and browser demo
are also required for the completion gate. Any unavailable gate remains
explicitly incomplete in `M4_COMPLETION.md`.

## Known risks

- The local VISTA checkpoint was loadable as a state dict, but its full MONAI
  inference path is not yet benchmarked against the host's version skew.
- The visual scenario projections are demo-bounded and must not be described
  as patient-specific predictions.
- The environment did not permit the requested 20 concurrent agent threads;
  the actual agent ledger records this rather than fabricating usage.
