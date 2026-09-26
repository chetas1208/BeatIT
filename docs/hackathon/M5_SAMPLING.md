# M5 Sampling

- Seed: recorded with every ensemble and sample.
- Randomness: one local deterministic PRNG; no global `Math.random()` calls.
- Reproducibility: same snapshot, distributions, seed, and count produce the
  same serialized samples.
- Bounds: samples outside declared support are rejected, never silently
  clamped.
- Validity: EDV must exceed ESV; volumes, EF, stroke volume, and cardiac output
  must remain finite and physiologically bounded.
- Correlation: parameters are sampled independently because BeatIT does not yet
  have a validated joint correlation model for these proxies.
- Quantiles use sorted empirical samples with linear interpolation at
  `(n - 1) × probability`; they are descriptive simulation percentiles.
