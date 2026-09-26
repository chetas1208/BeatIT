# Agent 08 — ECG generation, parsing, and model audit

**Date:** 2026-09-26 UTC

**Scope:** read-only audit of ECG waveform generation, CSV parsing, synthetic
fixtures, NeuroKit2 availability, and the learned-model boundary.

**Safety boundary:** no downloads, network calls, model training, production
edits, fixture regeneration, or secret-value output. The only repository file
written by this contribution is this report. Existing worktree changes were
preserved.

## Executive result

The core ECG path does **not** require NeuroKit2 or a learned ECG model. The
main Electrophysiology Agent calls the local deterministic
`python/hearttwin/tools/ecg_features.py` implementation for R-peak/RR/rhythm
descriptors and explicitly keeps language-model use out of numeric feature
estimation (`python/hearttwin/agents/electrophysiology_agent.py:1-12`). The
focused EP suite passed **11 tests** offline.

NeuroKit2 is not installed in the audited Python environment and is not declared
in `requirements.txt` or `pyproject.toml`. The phrase “NeuroKit2-compatible” in
the synthetic cohort provenance is therefore not evidence that NeuroKit2 was
used: the generator is local `math`/`random` code.

A separate, optional research ECG-superclass endpoint is different. It calls
`EcgDxClassifier.load()` and cannot operate without `model.joblib`; the API
returns HTTP 503 when that artifact is absent (`python/hearttwin/api.py:1109-1137`).
The repository has a 3.5 MB tracked artifact, but the dependency manifests omit
both `scikit-learn` and `joblib`, and local loading emitted a large number of
`InconsistentVersionWarning` warnings because the artifact was trained with
scikit-learn 1.5.2 while the environment has 1.8.0. This learned model is
therefore required only if that separate research endpoint is in the release
scope, and it is not currently a portable deployment contract.

## Existing implementation

### Generation

There are two independent deterministic synthetic waveform generators:

| Artifact | Generator | Shape/format | Observed contract |
|---|---|---|---|
| `fixtures/hearttwin/ecg_synthetic_normal.csv` and `ecg_synthetic_fast.csv` | `scripts/create_synthetic_fixtures.py:177-200,230-231` | 2,500 samples, one `lead_ii_mv` column plus `time_ms`, 250 Hz | Gaussian QRS spike, baseline wander, T-wave bump; explicitly “not clinically faithful” |
| `data/synthetic_cohort_500/ecg/*.csv` | `scripts/build_cohort_500.py:127-143,265-276` | 166 files, 500 samples each, `sample,lead_i,lead_ii,lead_iii` | Three lead-like columns, analytic P/QRS/T terms, seeded uniform noise; generator loop uses 250 Hz |

The legacy fixture generator is reproducible byte-for-byte from its source
function. The cohort has 500 synthetic profiles and 166 ECG files, matching
`data/synthetic_cohort_500/manifest.json:1-29`; every ECG file regenerated
byte-for-byte from its profile seed and the checked-in generator.

The unit-test waveform is a third, test-local periodic-spike signal
(`python/hearttwin/tests/test_electrophysiology_agent.py:34-45`). It is useful
for detector coverage but is not a committed production fixture.

### Core parsing and feature extraction

The deterministic feature path is intentionally lightweight:

- `detect_r_peaks()` applies a moving-average bandpass approximation, derivative,
  squaring, moving-window integration, thresholding, and a refractory period
  (`python/hearttwin/tools/ecg_features.py:33-124`).
- `analyze_waveform()` derives RR, heart rate, variability, a simulation-safe
  rhythm descriptor, optional Bazett QTc, and warnings for insufficient peaks
  (`python/hearttwin/tools/ecg_features.py:127-242`).
- The EP agent prefers lead II, honors `sampling_rate_hz` when supplied, and
  otherwise defaults to 500 Hz (`python/hearttwin/agents/electrophysiology_agent.py:151-175,508-513`).
- If no waveform is present, the agent falls back to reported values or
  labeled priors; it does not require a model to produce a safe response.

The separate API CSV parser accepts a time-prefixed single lead or numeric
matrix, places a single lead in lead-II position, and defaults to 100 Hz when
it does not recognize a time column (`python/hearttwin/api.py:1055-1106`).

## Findings

### PASS — core synthetic fixture generation and deterministic analysis

The two legacy CSVs are parseable and reproducible:

```text
ecg_synthetic_normal.csv: rows=2500 fs=250.0Hz peaks=12 hr=72.0 rr_ms=833.5 source_reproducible=True
ecg_synthetic_fast.csv: rows=2500 fs=250.0Hz peaks=20 hr=120.0 rr_ms=500.0 source_reproducible=True
legacy fixture probe: PASS
```

The cohort inventory and generator replay also agree:

```text
manifest_profiles=500 manifest_ecg=166 files=166 headers=[('sample', 'lead_i', 'lead_ii', 'lead_iii')] rows=[500] reproducible=True
cohort fixture probe: PASS
```

These results prove software-path reproducibility and parser exercise only.
They do not establish physiologic or clinical validity; the legacy generator
itself says it is not clinically faithful, and all cohort provenance is
synthetic.

### OPEN — cohort CSV and API parser disagree on sample rate and lead mapping

The cohort generator uses `fs = 250` but writes a column named `sample`, not a
time column (`scripts/build_cohort_500.py:127-143`). The API parser only treats
the first column as time when its header contains `time`
(`python/hearttwin/api.py:1086-1095`). Reproduction against
`BEATIT-SYN-0003.csv`:

```text
header: sample,lead_i,lead_ii,lead_iii
parser_fs_hz=100.0 (generator contract is 250.0)
source_row0 lead_i=-0.001173 lead_ii=0.002310
parser_row0 mapped_lead0=0.000000 mapped_lead2=0.002310 classifier_lead_ii_index1=-0.001173
cohort parser mismatch: REPRODUCED
```

Because the numeric sample counter is retained as signal column 0, the parser’s
12-column output puts source `lead_i` at index 1, where the research feature
extractor assumes standard lead II (`python/hearttwin/research/ecg_dx/features.py:13,59-61`).
The legacy `time_ms,lead_ii_mv` fixtures do not have this mismatch: their time
column is removed and the single remaining signal is placed at lead-II index 1.

**Disposition:** do not use the cohort CSVs as research-endpoint inputs until
the generator/parser contract is deliberately aligned. A future fix should
choose one explicit contract (for example, `time_ms` plus named leads, or a
documented sample-index column and explicit sampling-rate/lead handling) and
add a regression test. No such fix was made in this audit.

### PASS — NeuroKit2 is absent and not needed by the core path

The environment-safe package probe did not print any secret values:

```text
neurokit2: importable=False version=not-installed
scikit-learn: importable=True version=1.8.0
joblib: importable=True version=1.5.3
numpy: importable=True version=2.5.2
scipy: importable=True version=1.17.1
```

The repository search found no `neurokit2` import or dependency declaration.
`scripts/build_cohort_500.py` uses only standard-library `math` and `random` for
waveform generation. “NeuroKit2-compatible” should be treated as an unverified
description, not as package provenance.

### PARTIAL — learned research classifier exists but is not deployment-ready

The artifact and classifier are real repository components:

```text
python/hearttwin/research/ecg_dx/model.joblib: exists=True size=3475594
bundle_keys: ['feature_dim', 'model', 'threshold']
feature_dim: 103
threshold: 0.5
model_type: OneVsRestClassifier
estimators: 5
classes: [0 1 2 3 4]
model_load=PASS type=OneVsRestClassifier feature_dim=103 classes=5 warnings=3021
model_compatibility_warning=InconsistentVersionWarning
research classifier probe: PASS (local artifact only; no network)
```

The classifier has five superclass outputs (`NORM`, `MI`, `STTC`, `CD`, `HYP`)
and is reachable only through the separate `/api/v1/ecg/diagnose` route. Its
training code expects `benchmark/datasets/ptbxl/dx_dataset.npz`
(`python/hearttwin/research/ecg_dx/train.py:21-24,37-42`), which is absent from
this checkout; `test_split.npz` is also absent. The committed model can be
loaded locally, but the exact training/evaluation replay is not available from
the current repository state.

`requirements.txt` and `pyproject.toml` declare NumPy/SciPy but not
scikit-learn or joblib. A clean deployment therefore cannot safely claim that
the research endpoint is runnable merely because `model.joblib` is tracked.
The version mismatch warning further means the loaded artifact needs a pinned
runtime or a deliberate compatibility validation before promotion.

## Executable checks

All checks were run from the repository root with the local Python environment.
They were offline and did not download or contact external services.

```bash
# Package availability; prints names and versions only, never environment values.
/opt/miniconda/bin/python - <<'PY'
from importlib import metadata
import importlib.util
for dist, module in [('neurokit2','neurokit2'), ('scikit-learn','sklearn'),
                     ('joblib','joblib'), ('numpy','numpy'), ('scipy','scipy')]:
    try:
        version = metadata.version(dist)
    except metadata.PackageNotFoundError:
        version = 'not-installed'
    print(f'{dist}: importable={importlib.util.find_spec(module) is not None} version={version}')
PY

# Core EP regression suite, with provider/credential variables removed.
env -u OPENAI_API_KEY -u WANDB_API_KEY -u UPSTASH_REDIS_REST_URL \
    -u UPSTASH_REDIS_REST_TOKEN -u MODEL_API_KEY \
    /opt/miniconda/bin/python -m pytest -q \
    python/hearttwin/tests/test_electrophysiology_agent.py
```

Observed test result:

```text
11 passed, 11 warnings in 0.14s
```

The warnings were existing Pydantic/deprecated-UTC warnings. The focused API
test selection had no ECG-specific tests: `16 deselected in 3.01s`.

The fixture replay and parser-contract probes were also run without writing
files:

```bash
env -u OPENAI_API_KEY -u WANDB_API_KEY -u UPSTASH_REDIS_REST_TOKEN \
    -u MODEL_API_KEY /opt/miniconda/bin/python - <<'PY'
import csv, json, runpy
from pathlib import Path
from python.hearttwin.api import _parse_ecg_csv
from python.hearttwin.tools.ecg_features import analyze_waveform

legacy = runpy.run_path('scripts/create_synthetic_fixtures.py', run_name='audit')
for name, hr in [('ecg_synthetic_normal.csv', 72.0),
                 ('ecg_synthetic_fast.csv', 120.0)]:
    path = Path('fixtures/hearttwin') / name
    rows = list(csv.DictReader(path.open(newline='')))
    time_ms = [float(row['time_ms']) for row in rows]
    signal = [float(row['lead_ii_mv']) for row in rows]
    fs = 1000.0 / (time_ms[1] - time_ms[0])
    result = analyze_waveform(signal, fs)
    assert legacy['_synthetic_ecg'](hr) == path.read_text()
    print(name, len(rows), fs, result.heart_rate_bpm)

manifest = json.loads(Path('data/synthetic_cohort_500/manifest.json').read_text())
files = sorted(Path('data/synthetic_cohort_500/ecg').glob('*.csv'))
assert manifest['synthetic_ecg_count'] == len(files) == 166
cohort = files[0]
sig, fs = _parse_ecg_csv(cohort.read_bytes())
print('cohort', len(files), sig.shape, fs)
assert fs == 100.0  # current parser behavior; generator uses 250 Hz
PY
```

The model seam was checked locally, without an inference request or network
access:

```bash
/opt/miniconda/bin/python - <<'PY'
import warnings
from pathlib import Path
import joblib

path = Path('python/hearttwin/research/ecg_dx/model.joblib')
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always')
    bundle = joblib.load(path)
model = bundle['model']
print(path.stat().st_size, bundle['feature_dim'], type(model).__name__, len(caught))
PY
```

For the audited checkout, the first command reported the values shown above and
the second reported `3475594 103 OneVsRestClassifier 3021` plus
`InconsistentVersionWarning` instances.

## Recommendation

1. Keep the core EP generator/parser path deterministic and model-free for the
   demo and simulation pipeline. NeuroKit2 is not a prerequisite.
2. Treat `model.joblib` and `/api/v1/ecg/diagnose` as an explicitly optional
   research capability. If it is released, add pinned `scikit-learn` and
   `joblib` dependencies, pin or revalidate the artifact’s scikit-learn version,
   and preserve the absent-model failure as a safe, explicit state.
3. Before using cohort ECGs through the API, resolve the `sample`/250 Hz/lead
   mapping mismatch and add a fixture-level parser regression test. Do not
   silently reinterpret the sample counter as a waveform channel.
4. Correct the provenance wording in a separately authorized change so the
   cohort identifies its actual local analytic generator rather than implying
   NeuroKit2 use or compatibility that was not tested.

## Final disposition

**PASS — deterministic core ECG generation, parsing of legacy fixtures, and EP
feature extraction.**

**OPEN — cohort CSV parser contract mismatch.**

**PARTIAL — optional learned research classifier: artifact present and locally
loadable, but dependency/runtime compatibility and reproducible training data
are not established.**

No production source, committed fixture, model artifact, or external resource
was modified or downloaded by this audit.
