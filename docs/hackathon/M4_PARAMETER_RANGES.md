# M4 parameter ranges

The first explorer intentionally exposes five inputs only:

| Key | Unit | Bounds | Meaning |
|---|---|---:|---|
| `heart_rate_bpm` | bpm | 30–200 | Scenario beat rate; RR is derived as `60000 / HR` |
| `preload_index` | index | 0–1.5 | Relative filling input carried by the existing twin |
| `afterload_index` | index | 0–2 | Relative ejection-resistance input |
| `contractility_index` | index | 0–1.5 | Relative contractile input |
| `systemic_vascular_resistance_index` | index | 0–2 | Relative vascular-resistance input |

Values are validated as finite numbers before computation. The propagation
engine normalizes each index to the selected snapshot's baseline so controls
can work with the existing state units. Inputs outside bounds are rejected;
they are never silently coerced by the UI.
