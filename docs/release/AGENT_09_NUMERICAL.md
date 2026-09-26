# M10.5 Agent 09 — Numerical Integrity Verification

**Status:** PASS for the exercised deterministic paths; QTc fixture coverage is
explicitly limited as noted below.

**Scope:** read-only verification of the canonical cardiac formulas against the
checked-in synthetic fixtures. No production code or fixture data was changed.

## Verification commands

The direct probe was run from the repository root with `PYTHONPATH=.`. It loaded
the checked-in JSON and CSV fixtures and called the production functions directly:

```text
python.hearttwin.tools.cardiac_state
python.hearttwin.tools.ecg_features
python.hearttwin.tools.hemodynamics
python.hearttwin.tools.cardiac_findings
```

The focused regression command also passed:

```text
python -m pytest -q \
  python/hearttwin/tests/test_cardiac_formulas_golden.py \
  python/hearttwin/tests/test_cardiac_formulas.py \
  python/hearttwin/tests/test_hemodynamics.py \
  python/hearttwin/tests/test_cardiac_findings.py
```

Result: **102 passed in 0.12s**.

## Canonical fixture results

Values below are the unrounded production-function results. The checked-in
fixture expectations are rounded to two decimal places and were matched within
`0.01` in the direct probe.

| Fixture | SV | EF | CO | MAP | RR | Result |
|---|---:|---:|---:|---:|---:|---|
| `fixtures/hearttwin/manual_baseline.json` | 70.00000 mL | 58.33333 % | 5.04000 L/min | 93.33333 mmHg | 833.33333 ms | PASS |
| `fixtures/hearttwin/manual_reduced_function.json` | 55.00000 mL | 36.66667 % | 4.84000 L/min | 101.66667 mmHg | 681.81818 ms | PASS |

The exercised formulas were:

- `SV = EDV - ESV`
- `EF = SV / EDV * 100`
- `CO = HR * SV / 1000`
- `MAP = DBP + (SBP - DBP) / 3`
- `RR = 60000 / HR`

The invalid-state tests also pass: non-positive EDV/HR, non-positive stroke
volume, and `ESV >= EDV` are rejected by the deterministic core rather than
silently converted into measurements.

## QTc verification

The checked-in waveform fixtures are intentionally minimal ECG-like CSV files.
They contain `time_ms,lead_ii_mv`, but no explicit QT interval annotation. The
waveform path therefore correctly reports `qtc_ms=None`; it must not invent a
QT interval from the synthetic signal.

| Fixture | Samples | Detected R peaks | Mean RR | HR | QTc |
|---|---:|---:|---:|---:|---|
| `ecg_synthetic_normal.csv` | 2500 | 12 | 833.5 ms | 72.0 bpm | unavailable: no QT annotation |
| `ecg_synthetic_fast.csv` | 2500 | 20 | 500.0 ms | 120.0 bpm | unavailable: no QT annotation |

The Bazett implementation was nevertheless exercised with the baseline
fixture-derived RR and an explicit controlled synthetic QT input:

```text
QT = 400.0 ms, RR = 833.33333 ms
QTc = QT / sqrt(RR_seconds) = 438.17805 ms
```

This is a formula probe, not a measured ECG result. A future fixture that is
intended to assert QTc must provide `qt_interval_ms` (or an equivalent
annotated measurement) and its provenance.

## Pressure-volume verification

`generate_pressure_volume_loop` was exercised using the baseline fixture's
`EDV=120 mL`, `ESV=50 mL`, `HR=72 bpm`, and `BP=120/80 mmHg`:

| Output | Result |
|---|---:|
| volume/pressure points | 200 / 200 |
| PV-loop area | 6449.06 mmHg·mL |
| stroke work | 0.859801 J |
| loop EF | 58.3 % |
| peak pressure | 144.7 mmHg |
| warnings | none |

The area is positive and the returned arrays are the same length, so the
deterministic chart payload is usable for the baseline synthetic case. PV area
is an `mmHg·mL` quantity; stroke work is reported in joules.

## AHA localization and units

The findings probe used the reduced-function EF and a synthetic anterior-wall
state. It returned:

- `segment_model`: `AHA 17-segment`.
- Global reduced-function finding: AHA segments `1..17`.
- Anterior regional finding: AHA segments `[1, 7, 13]`, LAD territory.
- Findings remained labeled as educational simulation observations.

AHA segment numbers are anatomical identifiers, not physical units. The
canonical physical-unit mapping exercised/reviewed here is:

| Metric | Unit |
|---|---|
| heart rate | bpm |
| EDV, ESV, SV | mL |
| EF, oxygen saturation | % |
| CO | L/min |
| SBP, DBP, MAP | mmHg |
| QT, QTc, QRS, RR | ms |
| PV-loop area | mmHg·mL |
| stroke work | J |
| AHA segment | dimensionless segment identifier |

## Disposition

The canonical deterministic numerical paths exercised in this task are
**verified for the checked-in synthetic baseline and reduced-function data**.
The result does not establish clinical validity, real-patient accuracy, or QTc
availability when the input lacks an explicit QT measurement.
