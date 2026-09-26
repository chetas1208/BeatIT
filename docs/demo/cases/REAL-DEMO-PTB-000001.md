# REAL-DEMO-PTB-000001

## CASE PURPOSE
Real de-identified research demo — `REAL de-identified PTB-XL subject (ECG-focused demo)`.

## SOURCE
{
  "dataset": "PTB-XL",
  "subject_key": "ptb-xl:ecg_id:1",
  "ecg_id": 1
}

## OBSERVED vs MISSING
- OBSERVED: fields marked in `data/real/normalized/REAL-DEMO-PTB-000001.json`
- BeatIT operate: PRIOR vitals used

## BEATIT RUN (deterministic pipeline)
{
  "case_id": "REAL-DEMO-PTB-000001",
  "extraction_fields": 6,
  "ef_pct": 58.3,
  "co_l_min": 5.04,
  "scenarios": 4,
  "prior_vitals_used_for_operate": true,
  "note": "Operate vitals marked PRIOR when source case lacked BP/echo volumes."
}

## LIMITATIONS
- PTB-XL provides real 12-lead ECG and demographics; BP and echo are not in this dataset.
- Educational simulation only — not a clinical case report.
