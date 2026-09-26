# M7 Pairing Audit — M6 Shadow Trial

Date: 2026-09-26  
Agent: M7 Agent 01, M6 Pairing Auditor  
Scope: read-only inspection of the M6 contracts, paired engine, identity
helpers, stores, fixtures, and tests. This audit added only this document; no
implementation or test files were changed.

## Result

**CONDITIONAL PASS for the generated M6 pairing path.** The active engine
preserves baseline sample identity, derives one scenario result from that same
sample, does not resample, uses the canonical M5.5 evaluator for scenario
outputs, computes raw scenario-minus-baseline deltas, and persists immutable
trial payloads across restart.

The pairing core is suitable for an M7 consumer when it uses the stored pair
records and canonical output/delta fields. This is not an unconditional M6
lineage or M7-readiness sign-off: the referenced baseline ensemble remains
replaceable under the same ID, pair records do not carry an explicit baseline
index or parameter digest, and the typed result contract permits some
schema-valid constructions that bypass the normal engine path.

## Contract and engine evidence

The reviewed authority is:

- `python/hearttwin/ensemble.py:188-220,242-323,332-375,416-468` — M5.5
  sample contract, lineage checks, canonical baseline/evaluator, persisted
  projection base, sample IDs, and outputs.
- `python/hearttwin/shadow_trial_contracts.py:72-171,192-227,349-398` —
  scenario, pair, provenance, result, unit, count, and status validation.
- `python/hearttwin/shadow_trial_identity.py:40-112` — deterministic and
  trial-namespaced scenario IDs plus identity helper checks.
- `python/hearttwin/shadow_trial_engine.py:114-162,169-315` — scenario
  application, trial identity, ordered pairing, canonical deltas, provenance,
  and result construction.
- `python/hearttwin/storage/shadow_trial_store.py:51-138` — file-backed
  create-once trial persistence and canonical JSON comparison.
- `python/hearttwin/storage/ensemble_store.py:52-139` — baseline persistence
  behavior relevant to the immutability limitation below.

### Baseline sample ID and scenario correspondence — PASS on active path

`EnsembleSample` requires a non-empty `id` and non-negative `index`; the M5.5
response validates unique IDs and complete index coverage. The M6 engine sorts
the validated samples by `(sample.id, sample.index)`, copies the baseline
sample ID into `sample_id` and `baseline_twin_id`, and constructs the scenario
ID as `<trial_id>-scenario-<sample_id>`. The result also rejects duplicate
pair sample IDs.

Independent execution of
`fixtures/golden/probabilistic/fixed-only.json` with
`fixtures/golden/shadow_trials/fixed-baseline-afterload.json` produced:

| baseline sample ID | baseline twin ID | scenario twin ID | parameter correspondence |
|---|---|---|---|
| `ensemble-1701e87cd10c-sample-0` | identical | `shadow-trial-b7c89ab1a9ee-scenario-ensemble-1701e87cd10c-sample-0` | baseline parameters equal persisted sample; only `afterload_index` targeted to `1.15` |
| `ensemble-1701e87cd10c-sample-1` | identical | `shadow-trial-b7c89ab1a9ee-scenario-ensemble-1701e87cd10c-sample-1` | baseline parameters equal persisted sample; only `afterload_index` targeted to `1.15` |

The run returned `requested_pairs=2`, `valid_pairs=2`, and
`invalid_pairs=0`. The trial ID was `shadow-trial-b7c89ab1a9ee`.

### No resampling — PASS, with fail-closed legacy behavior

The engine does not call `run_ensemble` and does not import or invoke a random
sampler. For each accepted sample it copies the persisted parameter vector,
changes only declared scenario keys, and calls `_evaluate` through the
canonical import from `ensemble.py`. It uses the sample's persisted
`projection_base`; a missing projection base raises
`baseline ensemble sample lacks the persisted projection base` instead of
reconstructing a second population from an already projected state.

The engine explicitly records the policy
`same baseline sample identity; no scenario resampling` in provenance. The
mixed-sample test independently recomputes each scenario from
`sample.projection_base` and the copied-plus-targeted parameters.

### Canonical deltas — PASS for returned scalar/output fields

Baseline values come from persisted `sample.outputs`; scenario values come
from the canonical evaluator output. The engine stores the raw subtraction
`scenario_value - baseline_value` and applies near-zero tolerances only for
descriptive category counts, not for delta rounding.

For the fixed golden run, an independent `_evaluate(sample.projection_base,
expected_parameters)` comparison matched both returned pairs exactly:

```text
ejection_fraction_pct: -1.249999999999993 percentage_points
stroke_volume_ml:     -1.625 mL
cardiac_output_l_min: -0.11375000000000046 L/min
```

The checked-in vector also matches the expected trial ID, fingerprint, pair
deltas, and effect medians in
`fixtures/golden/shadow_trials/fixed-baseline-afterload.json`.

Invalid pairs are retained with rejection reasons, have their partial deltas
cleared atomically, and are excluded from effect distributions. The zero-valid
case is represented as `status="failed"`, not as a successful empty effect
population.

### Persistence and trial immutability — PASS for Shadow Trial records

`SQLiteShadowTrialStore` requires a file-backed database, writes canonical JSON,
uses `trial_id` as a primary key, performs `ON CONFLICT DO NOTHING`, and
compares the stored payload after the write. Exact replays are accepted;
different payloads raise `ShadowTrialStoreError: shadow trial IDs are
immutable` and leave the original record unchanged.

The focused store/API tests cover round trip, new-store retrieval, canonical
key ordering, conflicting writes, invalid/non-finite payloads, API retrieval,
idempotent POST behavior, and persistence error mapping. The independent
probe saved the generated result, retrieved it from a new store instance with
`restart_round_trip_equal: True`, rejected a conflicting write, and reported
`after_conflict_equal: True`.

### Provenance — PASS for normal generated results; conditional at contract boundary

The generated result retains:

```text
origin_snapshot_id       = golden-fixed-only
baseline_ensemble_id     = ensemble-1701e87cd10c
scenario_definition_id   = afterload-plus-15
origin_quality            = observed
evidence_ids              = [golden-fixed-only, golden-probabilistic-fixture]
seed                      = 101
physiology_version        = m5.5-ensemble-projection-v1
ensemble_version          = m5.5-backend-ensemble-v1
prior_version             = m5-priors-v1
engine_version            = m6-shadow-trial-v1
effect_metrics_version    = m6-effect-metrics-v1
pairing_policy            = same baseline sample identity; no scenario resampling
scenario_hash == fingerprint = True
definition present        = True
```

The scenario origin snapshot is bound to the baseline origin snapshot, and the
definition binds the scenario parameters and provenance parameters. The
canonical safety disclaimer and hypothetical/simulation warnings are retained.

## Exact verification commands and evidence

All commands below were run from `/home/923873155/BeatIT` on Python 3.13.12.

Focused M6 contract/identity/engine/golden/reproducibility/store/API suite:

```bash
python -m pytest -q \
  python/hearttwin/tests/test_shadow_trial_identity.py \
  python/hearttwin/tests/test_shadow_trial_contracts.py \
  python/hearttwin/tests/test_shadow_trial_engine.py \
  python/hearttwin/tests/test_shadow_trial_golden.py \
  python/hearttwin/tests/test_shadow_trial_reproducibility.py \
  python/hearttwin/tests/test_shadow_trial_store.py \
  python/hearttwin/tests/test_shadow_trial_api.py
```

Result: `40 passed, 8 warnings in 3.87s`.

Repository Python regression suite:

```bash
pnpm test:py
```

Result: `988 passed, 1 skipped, 494 warnings in 12.21s`.

The independent read-only fixture probe used this exact command:

```bash
python - <<'PY'
import hashlib, json, tempfile
from pathlib import Path
from python.hearttwin.ensemble import EnsembleRequest, _evaluate, run_ensemble
from python.hearttwin.shadow_trial_contracts import ScenarioDefinition
from python.hearttwin.shadow_trial_engine import run_shadow_trial
from python.hearttwin.storage.shadow_trial_store import SQLiteShadowTrialStore, ShadowTrialStoreError

root = Path.cwd()
b = json.loads((root / 'fixtures/golden/probabilistic/fixed-only.json').read_text())
s = json.loads((root / 'fixtures/golden/shadow_trials/fixed-baseline-afterload.json').read_text())
baseline = run_ensemble(EnsembleRequest.model_validate(b['input']))
scenario = ScenarioDefinition.model_validate(s['scenario'])
before = hashlib.sha256(json.dumps(baseline, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
result = run_shadow_trial(baseline, scenario, metrics=s['metrics'])
after = hashlib.sha256(json.dumps(baseline, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
print('baseline_id:', baseline['id'])
print('baseline_sample_ids:', [sample['id'] for sample in baseline['samples']])
print('trial_id:', result.id)
print('pair_count:', len(result.paired_results), 'valid:', result.valid_pairs, 'invalid:', result.invalid_pairs)
for pair in result.paired_results:
    sample = next(sample for sample in baseline['samples'] if sample['id'] == pair.sample_id)
    expected_parameters = {**sample['parameters'], 'afterload_index': 1.15}
    expected_outputs = _evaluate(sample['projection_base'], expected_parameters)
    assert pair.baseline_parameters == sample['parameters']
    assert pair.scenario_parameters == expected_parameters
    assert all(pair.deltas[m] == expected_outputs[m] - sample['outputs'][m] for m in s['metrics'])
    print('canonical_deltas_equal_returned: True', pair.sample_id)
print('baseline_unchanged_sha256:', before == after)
with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / 'shadow.sqlite3'
    payload = result.model_dump(mode='json')
    SQLiteShadowTrialStore(db).save(result.id, payload)
    print('restart_round_trip_equal:', SQLiteShadowTrialStore(db).get(result.id) == payload)
    try:
        SQLiteShadowTrialStore(db).save(result.id, {**payload, 'warnings': ['conflict']})
    except ShadowTrialStoreError as exc:
        print('conflicting_write:', type(exc).__name__, str(exc))
    print('after_conflict_equal:', SQLiteShadowTrialStore(db).get(result.id) == payload)
PY
```

Its material output was:

```text
baseline_id: ensemble-1701e87cd10c
baseline_sample_ids: [ensemble-1701e87cd10c-sample-0, ensemble-1701e87cd10c-sample-1]
trial_id: shadow-trial-b7c89ab1a9ee
pair_count: 2 valid: 2 invalid: 0
baseline_unchanged_sha256: True
canonical_deltas_equal_returned: True  (both pairs)
restart_round_trip_equal: True
conflicting_write: ShadowTrialStoreError shadow trial IDs are immutable
after_conflict_equal: True
```

The source-level no-resampling scan was:

```bash
rg -n "projection_base|scenario_sample_id|sorted\\(ensemble.samples|baseline_outputs|canonical_evaluate|no scenario resampling|scenario_definition_hash|ON CONFLICT|immutable|definition: ShadowTrialDefinition|pairing_policy" \
  python/hearttwin/ensemble.py \
  python/hearttwin/shadow_trial_engine.py \
  python/hearttwin/shadow_trial_identity.py \
  python/hearttwin/storage/shadow_trial_store.py \
  python/hearttwin/storage/ensemble_store.py \
  python/hearttwin/shadow_trial_contracts.py
```

The scan showed the expected persisted projection base, canonical evaluator,
trial-namespaced scenario ID, sorted pairing loop, no-resampling policy,
create-once Shadow Trial write, and replaceable baseline write.

## Limitations and M7 consumption rules

1. **Baseline storage is replaceable.** `SQLiteEnsembleStore` uses
   `ON CONFLICT (ensemble_id) DO UPDATE`. A direct probe saved `afterload_index`
   `1.0` and then `1.2` under the same `ensemble-fixed` ID; retrieval returned
   `1.2`. The Shadow Trial payload is immutable, but the ID it references is
   not a content-addressed immutable input. M7 must treat the stored pair/result
   as authoritative and must not silently recompute from a later baseline
   lookup. An unconditional lineage sign-off requires a baseline digest or
   create-once baseline store.

2. **Pair correspondence is not cryptographically closed.** The active engine
   proves correspondence through sample IDs, copied parameters, sorted
   execution, and tests, but `PairedTwinResult` does not persist the baseline
   sample `index` or a baseline-parameter digest. A future pair consumer should
   use `trial_id + sample_id` and the stored pair, not infer correspondence
   from array position or scenario ID alone.

3. **Result validation is weaker outside the engine.**
   `ShadowTrialResult.definition` is optional, and result validation does not
   bind every definition field, the actual baseline object, or a baseline
   content digest. Trusted API-generated results include the definition; direct
   or tampered schema-valid payloads can have weaker lineage guarantees.

4. **Scenario `baseline` metadata is not per-sample measured baseline.** The
   engine treats `value` as an absolute bounded target for every sample. It
   does not assert that the optional scenario `baseline` equals each sample's
   latent parameter. M7 must present these fields as scenario metadata, not as
   a measured per-sample change.

5. **MAP state projection has a known boundary.** M6 numerical review found
   that returned MAP deltas use canonical evaluator outputs, while the typed
   scenario state's systolic/diastolic fields remain baseline values. M7 should
   consume `pair.deltas`/canonical output fields for MAP and must not reconstruct
   scenario MAP from those unchanged BP fields.

6. **Persistence evidence is local and sequential.** Restart, replay, and
   conflict behavior are covered, but there is no concurrent-writer stress
   test, hosted-database evidence, or complete persisted-baseline/subprocess
   benchmark. The M6 completion record also correctly keeps browser and
   accessibility gates separate from this backend pairing audit.

## Audit disposition

**Pairing core: PASS.**  
**Trial persistence/record immutability: PASS.**  
**Baseline-input immutability and complete provenance closure: CONDITIONAL.**  
**M7 handoff: permitted for read-only pair visualization under the rules above;
do not claim unconditional M6/M7 lineage readiness until the baseline digest or
create-once baseline decision is resolved.**
