# M5 Priors

Every prior carries a source category, rationale, bounds, evidence IDs, and a
version. The initial version is `m5-priors-v1`.

No prior is presented as patient evidence. Only field-relevant evidence IDs
are retained alongside a distribution; unrelated snapshot evidence is not
copied into every parameter. If an explicit measurement is unavailable, the
parameter is labeled `population_prior` and the missing evidence remains a
known limitation.
