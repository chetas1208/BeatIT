# M6 Provenance and Lineage Review

Date: 2026-09-26  
Scope: read-only review of the M6 contracts, paired engine provenance
construction, Shadow Trial golden fixtures, and computational credibility
documentation. No implementation or test files were edited by this review.

## Verdict

**CONDITIONAL PASS for generated-result provenance, with bounded lineage and
fixture-gate findings.** A result produced by the active engine carries the
baseline origin snapshot, baseline ensemble ID, scenario ID and parameters,
baseline RNG seed, physiology/ensemble/prior versions, engine and metric
contract versions, an explicit no-resampling policy, a scenario fingerprint,
the canonical safety disclaimer, and synthetic-origin warnings when the
referenced ensemble is synthetic.

The review does not support an unconditional provenance sign-off because the
typed result contract is permissive when used outside the engine, the upstream
ensemble contract does not check every sample's origin quality, and the golden
fixture/document versioning is inconsistent.

## Reviewed sources

- `python/hearttwin/shadow_trial_contracts.py`
  - `ShadowTrialProvenance`
  - `ShadowTrialDefinition.validate_lineage`
  - `ShadowTrialResult.validate_result`
- `python/hearttwin/shadow_trial_engine.py`
  - `_trial_id`
  - `run_shadow_trial`
  - provenance and definition construction
- `python/hearttwin/ensemble.py`
  - `EnsembleResponse.validate_counts_and_lineage`
  - `EnsembleProvenance`
- `fixtures/golden/shadow_trials/*.json`
- `python/hearttwin/tests/test_shadow_trial_contracts.py`
- `python/hearttwin/tests/test_shadow_trial_engine.py`
- `python/hearttwin/tests/test_shadow_trial_reproducibility.py`
- `python/hearttwin/tests/test_shadow_trial_golden.py`
- `docs/credibility/COMPUTATIONAL_CREDIBILITY.md`
- `docs/credibility/beatit-model-manifest.json`

## Evidence summary

Focused verification was run from the repository root:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  pytest -q \
  python/hearttwin/tests/test_shadow_trial_contracts.py \
  python/hearttwin/tests/test_shadow_trial_engine.py \
  python/hearttwin/tests/test_shadow_trial_reproducibility.py \
  python/hearttwin/tests/test_shadow_trial_golden.py

16 passed, 8 warnings
```

An independent generated-result probe verified:

```text
origin_snapshot_match: true
baseline_ensemble_match: true
scenario_id_match: true
scenario_parameter_match: true
seed_match: true
scenario_hash_equals_fingerprint: true
canonical_disclaimer: true
pairing_policy: "same baseline sample identity; no scenario resampling"
```

The synthetic replay fixture was executed independently. It produced
`origin_quality = "synthetic"`, preserved the replay provenance object and
seed `404`, carried the M5.5 physiology/ensemble/prior versions plus
`m6-shadow-trial-v1`, preserved the exact canonical disclaimer, and emitted:

```text
Baseline ensemble origin is synthetic replay data; it is not patient evidence.
```

## Passed invariants

### Origin quality and source propagation — PASS for engine-generated results

`run_shadow_trial` copies `origin_quality`, `origin_provenance`, and
`evidence_ids` from the persisted M5.5 ensemble into
`ShadowTrialProvenance`. The source origin snapshot is copied into both the
trial provenance and the generated `ShadowTrialDefinition`. If the incoming
scenario omits `origin_snapshot_id`, the engine fills it with the baseline
ensemble snapshot; if it supplies one, the engine rejects a mismatch.

The definition validator then requires:

- scenario origin snapshot == trial origin snapshot;
- provenance origin snapshot == trial origin snapshot;
- provenance baseline ensemble == trial baseline ensemble;
- provenance scenario ID == the serialized scenario ID; and
- provenance parameter changes == the serialized scenario parameters.

These checks establish a coherent lineage graph for the normal engine path.

### Versions and seed — PASS with a bounded scope

The generated provenance records:

- physiology version from the baseline ensemble;
- ensemble distribution-config version;
- prior version;
- `m6-shadow-trial-v1` engine version; and
- `m6-effect-metrics-v1` effect contract version.

The trial seed is copied from the baseline ensemble seed. This is appropriate
for M6 because the scenario does not draw a second population. The engine
applies bounded target values to each already persisted sample and explicitly
records the no-resampling policy.

This is a baseline RNG seed, not a separate scenario RNG seed. That distinction
is correctly represented by the current deterministic design and should remain
explicit in any future API documentation.

### Scenario lineage and deterministic identity — PASS

The trial fingerprint hashes the baseline ensemble ID, canonicalized scenario,
selected metrics, neutral tolerances, engine version, and physiology version.
The provenance `scenario_definition_hash` is set to that fingerprint. Scenario
parameter declaration order is normalized before identity construction, and
the reproducibility tests verify same-input and reversed-sample-order replay.

The scenario's `baseline` and `delta` fields are retained as descriptive
metadata. The engine documents that `value` is the absolute bounded target
applied to every paired sample; it does not interpret `delta` as a new
per-sample random or additive draw.

### Safety disclaimer and synthetic labeling — PASS on successful output

`ShadowTrialResult`, effects projections, and pair projections require the
canonical `DISCLAIMER`. The API's Shadow Trial HTTP and validation exception
handlers also attach the disclaimer to error responses. The synthetic replay
probe verified that synthetic origin produces an explicit non-patient-evidence
warning, while the result remains labeled as a hypothetical simulation.

The credibility document and manifest also state that Shadow Trial effects do
not establish efficacy, benefit, harm, treatment value, or patient-specific
claims.

## Findings and bounded limitations

### F-1 — Result-level lineage is not fully closed outside the engine

**Severity: P1 provenance-contract gap.**

`ShadowTrialResult.definition` is optional, and `ShadowTrialResult` validates
only that its provenance baseline ensemble ID matches the result's baseline
ensemble ID. It does not require a definition or, when one is supplied, repeat
all definition-to-result checks. It also cannot validate that the provenance
origin snapshot and seed match the actual persisted baseline ensemble because
the result contract contains no baseline ensemble snapshot digest and does not
receive the baseline object during validation.

The active engine always emits a populated, internally consistent definition,
so this is not a failure of the normal generated path. It is a boundary gap for
direct construction, tampered persisted payloads that remain schema-valid, or
future producers that bypass `run_shadow_trial`. The current local SQLite
design is trusted storage rather than content-addressed baseline storage, so an
ensemble replacement under the same ID is not ruled out by the M6 result
payload alone.

### F-2 — Per-sample origin quality is not checked upstream

**Severity: P1 inherited lineage-validation gap.**

`EnsembleResponse` checks that the ensemble provenance origin quality equals the
first sample's origin quality, and checks every sample's origin snapshot and
seed. It does not check that every sample's `origin_quality` equals the
ensemble-level value. Consequently, a malformed ensemble with a later sample
carrying a different quality could still validate, while M6 would copy the
ensemble-level quality into trial provenance and potentially mask that
sample-level inconsistency.

Normal `run_ensemble` output and the reviewed fixtures are coherent, so this is
a defensive/tamper boundary rather than evidence of a current fixture failure.

### F-3 — Provenance metadata is structurally permissive

**Severity: P2 auditability limitation.**

`origin_provenance` and `evidence_ids` are allowed to be empty, and provenance
entries are untyped dictionaries. The engine copies the upstream values
faithfully, but the contract does not require an evidence identifier or define
the minimum fields needed to identify a source snapshot/replay. This is
acceptable for the current synthetic/demo scope, but it means that presence of
the provenance object alone is not proof that an external source can be
reconstructed.

### F-4 — Golden fixture versioning and execution coverage drift

**Severity: P1 verification/documentation gap.**

The manifest advertises `shadow_trial_fixture_version` as
`m6-shadow-trial-golden-v1`, while the executable Shadow Trial matrix fixtures
use `m6-golden-v1`. In addition, `fixed-baseline-afterload.json` is the one
fixture used for exact vector execution but has no `version` field, and it is
not included in the matrix set asserted by
`test_m6_golden_fixture_matrix_is_present_and_synthetic`.

That matrix test checks file presence, version, scenario ID, and a non-empty
`expected` object; it does not execute all listed baseline/scenario pairs. In
particular, `synthetic-demo-case.json` declares expected synthetic origin,
non-patient evidence, and a required disclaimer, but the test does not run that
case and assert those output values. The independent synthetic probe passed,
but the repository's golden gate does not currently enforce it.

### F-5 — Scenario baseline metadata is not sample-level provenance

**Severity: P2 contract-clarity limitation.**

`ScenarioParameterChange.baseline` is checked only for finite values and for
internal consistency with `value - delta` when `delta` is supplied. The engine
does not compare it with each baseline sample's actual parameter. This is
consistent with the documented absolute-target semantics, but a scenario
labelled “+15%” can be misread unless the API/UI continue to display the
baseline/value fields as descriptive metadata rather than claiming a measured
per-sample change.

## Gate assessment

| Gate | Result | Basis |
| --- | --- | --- |
| Generated origin quality and snapshot propagation | PASS | Engine probe and definition lineage checks |
| Version and baseline seed propagation | PASS | Engine probe and focused tests |
| Scenario ID/parameter lineage | PASS | Contract checks and reproducibility tests |
| Safety disclaimer | PASS | Contract, API tests, and synthetic probe |
| Synthetic labeling | PASS for executed synthetic replay; fixture gate incomplete | Independent probe passed; matrix test is presence-only |
| Schema-valid result cannot lose baseline lineage | CONDITIONAL | Optional definition and no baseline digest in result contract |
| Golden fixture provenance gate | CONDITIONAL | Version drift and incomplete execution coverage |

## Recommended closure actions

1. Require or fully validate `ShadowTrialResult.definition` on persisted/read
   paths, and bind the trial to an immutable baseline ensemble fingerprint or
   equivalent content identity.
2. Validate origin quality for every `EnsembleSample`, not only the first one.
3. Align the manifest and fixture version names, add a version to the exact
   vector fixture, and execute the synthetic-demo fixture in the golden test.
4. If evidence IDs remain optional for demo fixtures, state that explicitly as
   a synthetic/demo limitation; otherwise require a typed minimum provenance
   record.

No M7 Split Heart or M8 Missing Piece behavior was reviewed or introduced.
