# M7 Difference Engine

M7 difference rows are presentation models over the backend `scenario -
baseline` delta. Metric-specific units and near-zero display tolerances are
copied from the M6 contract. EF is displayed in percentage points; a relative
percent change is a separate value when available and is never substituted for
the percentage-point delta.

No-op or below-threshold differences produce no emphasized row and the UI
reports `NO MODELED DIFFERENCE`. The current integrated difference-only control
filters the deterministic metric table and exposes an explicit no-op state.
Per-component opacity/emphasis in the 3D material layer is not yet wired to
returned deltas, so the UI does not claim that unchanged anatomy has been
selectively subdued. Direction is neutral simulation semantics, not benefit/harm
or clinical advice.
