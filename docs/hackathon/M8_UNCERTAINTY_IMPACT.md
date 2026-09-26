# M8 Uncertainty Impact

Implementation: `python/hearttwin/missing_piece/impact.py`, `uncertainty.py`.

## Parameter uncertainty

Descriptive accepted-sample spread: **q95 − q05** over each parameter, normalized by declared deterministic range width. Not a probability, posterior, or measurement error.

## Impact heuristic (`uncertainty-impact-heuristic-v1`)

For target metric *m*:

```text
impactScore(θ, m) = uncertaintyMagnitude(θ) × |normalizedSensitivity(θ, m)|
```

- Requires finite normalized sensitivity; raw mixed-unit derivatives are **unavailable** for cross-parameter ranking.
- Normalized impact divides by the sum of impact scores on the same target (transparent shares, not probabilities).

## Critical distinction

High sensitivity + low uncertainty → **low impact**.  
Moderate sensitivity + high uncertainty → can **dominate**.

Golden fixtures under `fixtures/golden/missing_piece/` lock this behavior.
