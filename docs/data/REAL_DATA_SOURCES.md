# Real Data Sources — BeatIT Demo Campaign

Official URLs and BeatIT roles. **Patient-level files stay local and gitignored** unless a license explicitly permits redistribution.

| Name | Official URL | Version (target) | Access | Modalities | Subject linkage | BeatIT role | Downloaded locally |
|---|---|---|---|---|---|---|---|
| MIMIC-IV Clinical | https://physionet.org/content/mimiciv/ | 2.x+ | **Credentialed** (CITI + DUA) | Demographics, vitals, labs, dx, meds, procedures | `subject_id` | **Primary** clinical spine for hero case | **No** (`data/raw/mimic-demo/` empty) |
| MIMIC-IV Docs | https://mimic.mit.edu/docs/iv/ | — | Public documentation | Schema reference | — | Field mapping | N/A |
| MIMIC-IV-ECG | https://physionet.org/content/mimic-iv-ecg/1.0/ | 1.0 | Credentialed + open waveform mirror | ~800k 12-lead 500 Hz ECGs | `subject_id` → MIMIC-IV | **Primary** ECG for linked hero | **No** |
| MIMIC-IV-ECG (AWS Open) | https://registry.opendata.aws/mimic-iv-ecg/ | — | Open **waveform** distribution | WFDB/sharded files | `subject_id` in metadata | Waveform path only; **not** clinical tables | **Not verified** |
| MIMIC-IV-ECHO | https://physionet.org/content/mimic-iv-echo/ | latest stable | **Credentialed** | Structured echo measurements (+ optional DICOM subset) | `subject_id` → MIMIC-IV | **Primary** echo for linked hero | **No** |
| MIMIC-IV Demo | https://physionet.org/content/mimic-iv-demo/ | 1.0 | **Open** (small subset) | Clinical tables only (no full ECG/ECHO linkage at demo scale) | `subject_id` within demo | Dev/validation only; **not** multimodal hero | **No** (placeholder dir) |
| PTB-XL | https://physionet.org/content/ptb-xl/1.0.3/ | 1.0.3 | **Open** | 12-lead ECG, age/sex/HW, SCP statements | ECG record id (not MIMIC) | Real **ECG-only** demo / ingestion test | **No** (placeholder dir) |
| EchoNet-Dynamic | https://echonet.github.io/dynamic/ | — | Registration/terms | Echo video, EF, EDV, ESV, tracings | Per-video patient id | Real **echo-only** demo | **No** |
| Stanford AIMI EchoNet | https://aimi.stanford.edu/datasets/echonet-dynamic-cardiac-ultrasound | — | Same | Same | Same | Attribution / terms | N/A |

See also: `REAL_DATA_LEGAL_MATRIX.md`, `MIMIC_*_MAP.md`, `REAL_DATA_WAVE_1_HANDOFF.md`.
