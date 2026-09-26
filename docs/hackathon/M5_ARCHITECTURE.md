# M5 Architecture

```text
observed TwinSnapshot
        ↓
versioned ParameterDistribution[]
        ↓ seed + local deterministic PRNG
validated parameter samples
        ↓
M4 deterministic propagation
        ↓
accepted/rejected TwinSample[]
        ↓
quantiles, ranges, and representative samples
```

The deterministic physiology engine is unchanged. The ensemble runner samples
only input parameters, rejects invalid draws, records the rejection reason, and
aggregates accepted outputs. The UI labels percentiles as simulated percentiles
and does not call them clinical confidence or credible intervals.

Frontend and backend implementations use explicit version fields. They are
not yet a single shared executable engine and are **not numerically equivalent**.
The current known divergences are: different afterload-to-ESV coefficients,
different low cardiac-output floors, different seeded PRNG/normal-draw
algorithms, frontend rounding before aggregation, and different completeness
and rejection validation. Cross-layer golden vectors are therefore a release
blocker; callers must not interchange their ensemble outputs as if they were
the same computation.
