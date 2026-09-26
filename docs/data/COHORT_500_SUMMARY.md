# BeatIT Synthetic Cohort 500 Summary

Status: **READY for local deterministic testing; not a clinical cohort**

## Scorecard

| Measure | Result |
|---|---:|
| Requested/created profiles | 500 / 500 |
| Unique IDs | 500 / 500 |
| FHIR bundles structurally valid | 500 / 500 |
| BeatIT real-pipeline ingestion | 500 / 500 |
| Restart persistence readback | 500 / 500 |
| Longitudinal profiles (T0–T3) | 250 |
| Synthetic ECG profiles | 166 |
| Physiological invariant checks | PASS |
| Diverse advanced E2E sample | 120 / 120 |

## Coverage buckets

| Bucket | Count |
|---|---:|
| baseline | 200 |
| hemodynamic | 100 |
| electrical | 70 |
| structural | 60 |
| mixed | 40 |
| stress_test | 30 |

## Generated distributions

Values are deterministic generator outputs, not epidemiological claims.

| Field | Minimum | Mean | Median | Maximum |
|---|---:|---:|---:|---:|
| Age (years) | 18 | 53.11 | 52.00 | 88 |
| Heart rate (bpm) | 49.42 | 79.21 | 74.68 | 145 |
| Systolic BP (mmHg) | 92 | 128.94 | 127.38 | 180 |
| Diastolic BP (mmHg) | 54 | 79.28 | 79.44 | 107.05 |
| EDV (mL) | 80 | 133.64 | 131.76 | 209.79 |
| ESV (mL) | 28.16 | 60.15 | 57.01 | 126.08 |
| Oxygen saturation (%) | 93.61 | 97.43 | 97.47 | 100 |

Canonical metric relationships are generated from EDV, ESV, and bounded
phenotype parameters; the validator checks `SV = EDV - ESV` and
`EF = SV / EDV * 100` for every ingested state.
