# Real Data Case Certificate

Case: `REAL-PTB-XL-000008`  
Dataset: PTB-XL 1.0.3  
Source subject: PTB-XL `ecg_id=8`

| Check | Result |
|---|---|
| Account required | **NO** |
| Real ECG | **YES — 12 leads, 1000 samples, 100 Hz** |
| Real echo, BP, medications | **MISSING** |
| Clinical context | **PARTIAL — source ECG metadata/statements** |
| Synthetic measurements | **0** |
| Cross-dataset stitching | **NO** |
| Same subject across modalities | **N/A — ECG-only source case** |
| Derived values | Waveform-estimated electrical evidence |
| Model priors | Explicitly `MODEL_PRIOR`; never `OBSERVED` |
| Upstream checksums | **PASS** |
| License | CC BY 4.0 |
| Public use | Permitted with attribution and modification notice |
| BeatIT status | Local ECG path verified; API/UI/Copilot not wired |

Citation: Wagner, P., Strodthoff, N., Bousseljot, R., Samek, W., and
Schaeffter, T. (2022). *PTB-XL, a large publicly available
electrocardiography dataset* (version 1.0.3). PhysioNet.
https://doi.org/10.13026/kfzx-aw45
