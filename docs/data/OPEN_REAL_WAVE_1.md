# Open real-data campaign — Wave 1 handoff

Date: 2026-09-26

Five independent auditors tested authoritative endpoints without credentials.
No bulk dataset was downloaded.

| Source | Anonymous access evidence | License gate | Decision |
|---|---|---|---|
| PTB-XL 1.0.3 | PhysioNet file index and `s3://physionet-open/ptb-xl/1.0.3/` list successfully; sampled WFDB objects returned HTTP 200 | CC BY 4.0; attribution required; source `SHA256SUMS.txt` available | Continue |
| CAMUS public | Collection API reports `public: true`; anonymous ZIP endpoint returned HTTP 200 | CC BY-NC-SA 4.0 plus non-commercial scientific-research wording; no checksum manifest found | Continue locally; do not publicly redistribute raw data pending clarification |
| TED | Collection API reports public; anonymous `TED.zip` endpoint returned HTTP 200 | CC BY-NC-SA 4.0 plus research-only wording; no checksum found | Continue locally; do not publicly redistribute raw data pending clarification |
| UCI Heart Failure | Direct `data.csv` returned HTTP 200; 299 rows, 13 columns, no empty fields | CC BY 4.0; attribution required | Continue |
| Clinical Ultrasound Image Repository | Anonymous S3 ListBucket succeeded; aggregate metadata returned HTTP 200 | CC BY-NC 4.0; hackathon/public-use interpretation needs care; no checksums found | Continue with a bounded adult-TTE subset; no raw public mirror |

## Verified source details

### PTB-XL

- Source: <https://physionet.org/content/ptb-xl/1.0.3/>
- Direct files: <https://physionet.org/files/ptb-xl/1.0.3/>
- Format: 10-second, 12-lead WFDB at 100 Hz and 500 Hz.
- Metadata includes source `patient_id`, age, sex, ECG report/codes, signal
  quality fields, and waveform paths.
- Candidate downloads must come from `filename_lr`/`filename_hr` and be verified
  against the source checksum manifest.

### CAMUS

- Source: <https://www.creatis.insa-lyon.fr/Challenge/camus/>
- Public collection:
  <https://humanheart-project.creatis.insa-lyon.fr/database/#collection/6373703d73e9f0047faa1bc8>
- Format: current package uses compressed NIfTI plus configuration metadata;
  legacy documentation also describes MHD/raw.
- ED/ES, EF, age, sex, frame rate, image quality, and segmentation references are
  available. EDV/ESV are `DERIVED` unless an inspected source file explicitly
  supplies scalar values.

### TED

- Source: <https://humanheart-project.creatis.insa-lyon.fr/ted.html>
- Public collection:
  <https://humanheart-project.creatis.insa-lyon.fr/database/#collection/62840fcd73e9f00479084885>
- Format: MetaImage headers and raw image/mask arrays for full-cycle 4CH
  sequences. TED contains 98 CAMUS subjects with full-cycle annotations.

### UCI Heart Failure Clinical Records

- Source:
  <https://archive.ics.uci.edu/dataset/519/heart+failure+clinical+records>
- Direct CSV: <https://archive.ics.uci.edu/static/public/519/data.csv>
- Verified SHA-256:
  `54349729933cffdde5c92068572a89761bb53df50cc28250b0915fd18066976c`.
- EF is an observed scalar. ECG, raw echo, medications, and detailed diagnoses
  are absent. `time` is follow-up duration, not a repeated measurement series.

### Clinical Ultrasound Image Repository

- Source: <https://registry.opendata.aws/clinical-ultrasound-image-data/>
- Bucket: `s3://clinical-ultrasound-image-repository/`
- Format: DICOM plus per-study JSON/CSV metadata.
- Cardiac studies use `C` prefixes but span TTE, TEE, stress, pediatric, and
  fetal studies. Wave 2 must select adult TTE explicitly using metadata before
  downloading any large DICOM object.

## Wave 2 gate

All five sources may proceed to bounded indexing. PTB-XL and UCI may produce
redistributable attributed case assets under CC BY 4.0. CAMUS, TED, and Clinical
Ultrasound raw artifacts remain local-only/restricted until public-demo use is
cleared. No source may be joined to another source at subject level.

