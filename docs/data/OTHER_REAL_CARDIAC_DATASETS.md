# Other Real Cardiac Datasets — BeatIT Roles

Use as **separate demo cases** or benchmarks — never stitched to MIMIC `subject_id` unless the dataset itself links modalities.

## PTB-XL (open ECG)

- **URL:** https://physionet.org/content/ptb-xl/1.0.3/
- **Access:** Open on PhysioNet (license + attribution).
- **Provides:** 21k+ real 12-lead ECGs (500 Hz WFDB + 100 Hz); age, sex, height, weight; SCP diagnostic statements.
- **Does not provide:** Echo, hospital meds, linked ICU course.
- **BeatIT role:** `REAL ECG-FOCUSED CASE`; Missing Piece naturally surfaces absent echo.
- **Repo:** `data/scripts/05_select_ptbxl.py` builds a **non-identifying feature index** for CareGuard matching — explicitly **not** one-patient linkage with eICU.

## EchoNet-Dynamic (echo video)

- **URL:** https://echonet.github.io/dynamic/ · https://aimi.stanford.edu/datasets/echonet-dynamic-cardiac-ultrasound
- **Provides:** 10k+ echo videos; EF, EDV, ESV; LV tracings.
- **Does not provide:** Linked 12-lead ECG from same subject in this dataset.
- **BeatIT role:** `REAL ECHO-FOCUSED CASE`; structural / EF verification.

## MIMIC-IV Demo (open clinical subset)

- **URL:** https://physionet.org/content/mimic-iv-demo/
- **Provides:** Small real de-identified clinical tables (100 patients in prior local analysis artifact).
- **Limitation:** Not a substitute for full MIMIC-IV + ECG + ECHO multimodal hero.

## eICU (repo historical)

- Referenced in `data/scripts/` for CareGuard cohort work — **separate** from BeatIT cardiac twin demo spine; do not merge identities with MIMIC hero.

## Selection principle

| Need | Dataset |
|---|---|
| Multimodal hero (same person) | MIMIC-IV + MIMIC-IV-ECG + MIMIC-IV-ECHO (all credentialed) |
| Public real ECG demo | PTB-XL |
| Public real echo demo | EchoNet-Dynamic |
| Clinical context without echo/ECG | MIMIC-IV Demo (limited) |
