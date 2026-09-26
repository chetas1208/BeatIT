# Real Data Legal & Usage Matrix

Not legal advice — engineering checklist for BeatIT demo planning.

| Dataset | License / agreement | Credentialing | Redistribution in Git | Public web demo | Local private research demo |
|---|---|---|---|---|---|
| MIMIC-IV | PhysioNet credentialed + [DUA](https://physionet.org/content/mimiciv/view-dua/) | CITI + approved access | **No** raw patient rows | **No** raw PHI/identifiers; derived aggregates only if DUA permits | **Yes** if access approved and data stay on controlled machine |
| MIMIC-IV-ECG | Same family / module DUA | Credentialed (metadata); AWS open **waveforms** separate terms | **No** | Waveforms/IDs generally **not** for public re-hosting without review | Local only with compliance |
| MIMIC-IV-ECHO | Credentialed + DUA | Same as MIMIC-IV | **No** | **No** raw measurements/DICOM publicly | Local with compliance |
| MIMIC-IV Demo | Open with attribution | None | **No** (still patient-level) | Aggregate only | Small local demo clinical tables OK |
| PTB-XL | Open PhysioNet license | None | **No** raw WFDB in public repo | Attribution; check license for clip hosting | Open download OK locally |
| EchoNet-Dynamic | Dataset-specific terms | Registration | **No** videos in Git | Check Stanford/AIMI terms | Local OK under terms |

## Hard rules (campaign)

1. **No bypass** of PhysioNet authentication or sharing credentials.
2. **No re-identification** attempts.
3. **No cross-dataset subject stitching** (forbidden composite “one patient”).
4. **No silent imputation** of missing real fields as OBSERVED.
5. **Public Cloudflare/judge demo:** prefer **synthetic** or **aggregated** displays unless counsel/DUA explicitly allows the exposure mode.

## BeatIT labeling

All real-ingested values: **OBSERVED** (with dataset + table + time). Model-filled gaps: **PRIOR** or **MISSING**, never OBSERVED.
