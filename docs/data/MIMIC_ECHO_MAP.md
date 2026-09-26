# MIMIC-IV-ECHO — BeatIT Field Map

**Source:** [MIMIC-IV-ECHO](https://physionet.org/content/mimic-iv-echo/) (credentialed; linked to MIMIC-IV via `subject_id`)

## Scale (public release summary)

- Structured measurements from **200k+** echo studies / **90k+** patients (release documentation).
- Optional DICOM subset for a fraction of studies — use only if licensed and stored locally.

## Linkage

| Field | Role |
|---|---|
| `subject_id` | **Must match** MIMIC-IV clinical and MIMIC-IV-ECG for hero case |
| Echo study / report identifiers | Per-release column names (map in Wave 2 loader from `measurements`/`labels` tables) |

## BeatIT targets → typical measurement families

Map **only fields present** in the release for that study:

| BeatIT | Echo concepts (examples) |
|---|---|
| EF | LV ejection fraction (%), biplane/simpson where available |
| EDV / ESV | LV end-diastolic / end-systolic volume (mL) |
| LV size / wall | LVEDD, septal/posterior wall thickness |
| Diastolic function | E/e′, deceleration time, tissue Doppler where coded |
| Valves | Peak gradients, regurgitation grade |
| RV / LA | Chamber sizes, TAPSE, etc. |

Do **not** invent EDV/ESV from EF alone. If a volume is missing, store **MISSING**.

## Provenance

Each measurement → dataset table, row id, study id, time, original unit, **OBSERVED**.

## Local status

**No MIMIC-IV-ECHO** files under `BeatIT/data/` on this host.
