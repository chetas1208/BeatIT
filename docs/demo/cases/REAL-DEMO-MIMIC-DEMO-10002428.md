# REAL-DEMO-MIMIC-DEMO-10002428

## CASE PURPOSE
Real de-identified research demo — `REAL de-identified MIMIC-IV Demo subject (clinical-focused demo)`.

## SOURCE
{
  "dataset": "MIMIC-IV-Demo",
  "subject_id": 10002428
}

## OBSERVED vs MISSING
- OBSERVED: fields marked in `data/real/normalized/REAL-DEMO-MIMIC-DEMO-10002428.json`
- BeatIT operate: PRIOR vitals used

## BEATIT RUN (deterministic pipeline)
{
  "case_id": "REAL-DEMO-MIMIC-DEMO-10002428",
  "extraction_fields": 6,
  "ef_pct": 58.3,
  "co_l_min": 5.04,
  "scenarios": 4,
  "prior_vitals_used_for_operate": true,
  "note": "Operate vitals marked PRIOR when source case lacked BP/echo volumes."
}

## LIMITATIONS
- Clinical tables only; no same-subject ECG/echo in open demo subset.
