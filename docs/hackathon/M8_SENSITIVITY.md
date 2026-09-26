# M8 Sensitivity

Implementation: `python/hearttwin/missing_piece/sensitivity.py`, `perturbations.py`, `engine.py`.

## Method (Tier-1)

- **finite_difference** on the canonical M5.5 evaluator at each accepted sample's **persisted projection base**.
- Perturbation policy: 5% fractional step capped at 5% of declared parameter range; central differences when in bounds, else one-sided.
- **Raw sensitivity**: ΔY/Δθ in native units.
- **Normalized sensitivity**: |(ΔY/Y_floor)/(Δθ/θ)| with per-metric output floors documented in `engine.py`.

## Targets

- Baseline outputs: EF, SV, CO, HR, EDV, ESV, MAP.
- Shadow Trial effects: same metrics as scenario−baseline deltas with **fixed absolute scenario parameters** (M6 pairing preserved).

## Global aggregate (optional descriptive)

`global_sensitivity.py` exposes a median absolute normalized response aggregate only; it **rejects** Sobol/Morris/Shapley labels at the contract boundary.
