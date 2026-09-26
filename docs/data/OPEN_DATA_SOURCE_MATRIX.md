# Open real-data source matrix

Verified 2026-09-26 from authoritative source pages and anonymous access tests.
“Open access” means downloadable without an account; it does not waive license
restrictions.

| Dataset | Open access | Account required | License | Real subjects | ECG | Echo | Vitals | EF | Clinical context | Medications | Longitudinal | BeatIT role |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| PTB-XL 1.0.3 | Yes (HTTPS and anonymous S3) | No | CC BY 4.0 | Yes | Yes | No | No | No | Partial ECG metadata | No | No | Electrical hero |
| CAMUS public | Yes (public collection) | No | CC BY-NC-SA 4.0 plus research-only terms | 500 | No | Yes | No | Yes | Limited demographics | No | Cardiac-cycle sequences | Structural hero; local/derived demo only pending terms clarification |
| TED | Yes (public collection) | No | CC BY-NC-SA 4.0 plus research-only terms | 98 CAMUS subjects | No | Yes | No | Yes | Limited demographics | No | Full cardiac cycle | Temporal hero; local/derived demo only pending terms clarification |
| UCI Heart Failure Clinical Records | Yes (direct CSV) | No | CC BY 4.0 | 299 | No | No raw echo | Limited binary context only | Yes | Yes | No | Follow-up endpoint, not repeated measurements | Clinical HF hero |
| Clinical Ultrasound Image Repository | Yes (anonymous S3) | No | CC BY-NC 4.0 | 2,000 (667 cardiac) | No | Yes | No | Not established | Limited DICOM metadata | No | No | Imaging/VISTA evaluation; bounded adult TTE subset |

## Integrity policy

- Every demo case represents one source subject from one dataset.
- No source identifier is treated as linkable across datasets.
- Unavailable modalities remain `MISSING`.
- Computational assumptions remain `MODEL_PRIOR`; computed measurements remain
  `DERIVED`.
- Raw CAMUS, TED, and Clinical Ultrasound artifacts must not be mirrored through
  the public demo without explicit license/terms clearance.

