# BeatIT Final Local Model Inventory

This report distinguishes checkpoint presence/load from request-serving inference.

| Capability | Path/configured | Files | Load | Inference | GPU smoke | Required | Status |
|---|---|---:|---:|---:|---:|---:|---|
| medical-segmentation | configured | True | True | False | True | False | COMPLETE_BUT_INCOMPATIBLE |
| language | not configured | False | False | False | n/a | False | OPTIONAL_NOT_INSTALLED |
| embedding | not configured | n/a | n/a | n/a | n/a | False | OPTIONAL_NOT_INSTALLED |

- Learned ECG model: `NOT_REQUIRED`; the current path uses deterministic ECG parsing/formulas.
- Overall: `DETERMINISTIC_FALLBACK_READY`; live model claims remain `NOT_READY`.
- The VISTA checkpoint is not treated as usable inference without a configured compatible runner and smoke output.
