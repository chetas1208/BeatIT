# M8 Evidence Map

Version: **`m8-evidence-map-v1`**  
Implementation: `python/hearttwin/missing_piece/evidence_map.py`, `evidence.py`.

## Reviewed mappings (model-proxy)

| Evidence type | Parameters | Typical strength |
|---|---|---|
| `echocardiographic_measurement` | preload_index, contractility_index | strong |
| `blood_pressure_series` | afterload_index, systemic_vascular_resistance_index | moderate |
| `repeat_ecg` | heart_rate_bpm | moderate |

Unknown evidence types or undeclared parameters **fail closed** at scoring time.

## Rationale boundary

Mappings describe which **deterministic model parameters** an evidence class could constrain in this educational twin — not unique identifiability, not clinical necessity.

Strength weights: direct=1.0, strong=0.75, moderate=0.5, weak=0.25 (documented in code).
