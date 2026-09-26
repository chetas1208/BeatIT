# MIMIC-IV-ECG — BeatIT Field Map

**Source:** [MIMIC-IV-ECG 1.0](https://physionet.org/content/mimic-iv-ecg/1.0/) · [MIMIC ECG module docs](https://mimic.mit.edu/docs/iv/modules/ecg/)

## Identity & linkage

| Field | Role |
|---|---|
| `subject_id` | **Must match** MIMIC-IV clinical `subject_id` for multimodal hero case |
| `study_id` | Unique ECG study |
| `ecg_time` | Study timestamp (temporal matching) |

## Key files (release layout)

| File | Contents |
|---|---|
| `record-list.csv` | Paths to WFDB records, study metadata |
| `machine_measurements.csv` | Device-reported intervals/axes (use as **observed** machine outputs, not BeatIT-derived QTc unless re-computed deterministically) |
| `waveform_note_links.csv` | Links to clinical notes where applicable |

## Waveform

- **12-lead**, **10 s**, **500 Hz** diagnostic ECGs (real clinical acquisitions).
- Local path pattern depends on download layout (PhysioNet credentialed bundle or [AWS Open Data](https://registry.opendata.aws/mimic-iv-ecg/) shard).
- BeatIT ingestion must preserve: lead count, sample rate, file path, study id, provenance label **OBSERVED** from MIMIC-IV-ECG.

## BeatIT pipeline notes

- Do **not** download the full ~90 GB corpus blindly; cohort-query **subject_id** list first (Wave 3), then fetch only required studies.
- Open AWS mirror does **not** replace credentialed clinical tables; waveform-only paths still require metadata CSVs from the release.

## Local status

**No MIMIC-IV-ECG files** under `BeatIT/data/` on this host (Wave 2 discovery).
