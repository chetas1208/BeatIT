# Open Real Data Execution

Generated: 2026-09-26  
Reproduce: `python scripts/execute_open_real_data.py`

Each case is one source subject. Missing modalities remain missing. Computational
defaults are `MODEL_PRIOR`, never observations.

## Execution results

| Dataset | Download and verification | BeatIT path | Public gate |
|---|---|---|---|
| PTB-XL 1.0.3 | Metadata plus four 100 Hz WFDB records; 11/11 selected upstream checksums pass; 4/4 finite `1000 × 12` arrays | Parser → Electrophysiology Agent, 4/4 success | GO with CC BY 4.0 attribution |
| UCI HF | Complete 12,239-byte CSV; 299 rows, 13 columns, 0 nulls, 0 duplicates | Five profiles preserve source age and EF through State Builder | GO with CC BY 4.0 attribution |
| CAMUS | Anonymous access; one 6,155,713-byte subject ZIP; archive/NIfTI checks pass | Supplied EF only; pixels and contours not wired | NO-GO pending NC/research terms clarification |
| TED | Anonymous access; one 17,826,785-byte full-cycle sequence; MetaImage/ED/ES checks pass | Supplied EF only; temporal pixels not wired | NO-GO pending NC/research terms clarification |
| Clinical Ultrasound | Metadata/access probe only | Not incorporated | NO-GO under conservative CC BY-NC review |

PTB selected records: `1`, `8`, `22`, `32`. UCI selected rows: `1`, `2`,
`5`, `15`, `46`. The UCI SHA-256 is
`54349729933cffdde5c92068572a89761bb53df50cc28250b0915fd18066976c`.

## Storage and integrity

- `data/real/`: 70 local files, 41,638,151 bytes; ignored by Git.
- Normalized outputs: 11 JSON cases, 28,042 bytes.
- Receipts: 17/17 byte counts and local SHA-256 values reproduce.
- Synthetic measurements: **0**
- Cross-patient stitching: **0**
- Missing values preserved: **YES**
- Priors explicitly labeled: **YES**

Known epistemic limitation: waveform-derived RR is attached after state building,
but the original canonical `source_map` entry remains a default prior. The
normalized report does not call that derived value observed.

## BeatIT E2E

- ECG: local parser and Electrophysiology Agent path verified.
- Clinical: local normalization and State Builder path verified.
- Echo: file integrity verified; image pipeline not wired.
- Missing Piece: generic regression tests pass; no open-real runner.
- Copilot/UI: no allowlisted real-case catalog or loader.
- Reports: normalized cases and machine-readable receipts generated locally.

## Final

| Gate | Status |
|---|---|
| ECG real demo ready | **YES — local only** |
| Clinical real demo ready | **YES — local only** |
| Echo real demo ready | **NO** |
| Open real data suite ready | **NO** |
| Public hackathon path ready | **NO** |

The synthetic demo spine remains the public fallback. PTB-XL and UCI can
supplement it after a typed, allowlisted, privacy-minimized API/UI loader is built.
