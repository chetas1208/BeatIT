# M8 Architecture — Missing Piece

Status: **Tier-1 complete**  
Date: 2026-09-26

## Flow

```text
M5.5 Ensemble (persisted projection bases)
        │
        ▼
Local finite-difference sensitivity (per sample → median aggregate)
        │
        ▼
q05/q95 parameter spread (descriptive, not posterior)
        │
        ▼
Uncertainty-impact heuristic (normalized response × spread)
        │
        ├─► Shadow Trial effect branch (M6 same-sample, fixed scenario targets)
        │
        ▼
Evidence Priority Score (reviewed evidence map × impact)
        │
        ▼
MissingPieceResult → SQLite → API → web panel
```

## Authorities

| Layer | Source |
|---|---|
| Physiology | `python/hearttwin/ensemble._evaluate` / M5.5 projection base |
| Pairing | M6 `run_shadow_trial` / effect sensitivity in `effect_drivers.py` |
| Ranking math | `impact.py`, `evidence_value.py` — not LLM |
| Wire | `MissingPieceRequest` / `MissingPieceResponse` |

## Out of scope (explicit)

Sobol, Morris, Shapley, Bayesian EIG, clinical test ordering, 3D geometric uncertainty fields.

See [`M8_MATH_AUDIT.md`](./M8_MATH_AUDIT.md) and [`M8_INFORMATION_GAIN_BOUNDARY.md`](./M8_INFORMATION_GAIN_BOUNDARY.md).
