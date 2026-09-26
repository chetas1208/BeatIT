# M6 Invalid Pair Policy

Every baseline sample creates exactly one attempted pair, including baseline
samples that were already rejected by M5.5. Invalid pairs remain in
`paired_results` with `valid=false` and explicit `rejection_reasons`.

Invalid pairs are excluded from effect distributions, but the response reports
both `requested_pairs` and `invalid_pairs`. The API never silently analyzes only
the valid subset.

Invalidity includes missing baseline state metrics, missing latent parameters,
non-finite values, unsupported requested metrics, or a scenario result that
violates the canonical physiology invariants. A zero-valid-pair run is retained
as a failed trial with empty effect summaries; it is not converted to zero
effects.
