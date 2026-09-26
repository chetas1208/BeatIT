# M8 Evidence Priority

Implementation: `python/hearttwin/missing_piece/evidence_value.py`.

## Method: Evidence Priority Score (`evidence-priority-score-v1`)

For evidence type *E* and target metric *m*:

```text
Score(E, m) = Σ  impactScore(θ, m) × strengthWeight(E, θ)
```

over reviewed parameters θ constrained by *E* that also appear in the target's impact list.

## Not information gain

- `estimated_reduction` remains unset unless a valid Tier-2 Bayesian reduction is implemented.
- Rankings are **target-specific** (impacts filtered by `metric_id` before scoring).

## Freshness and completeness

Freshness (`freshness.py`) and domain completeness (`completeness.py`) inform presentation and limitations; they do not silently rescale priority scores without documented rules.
