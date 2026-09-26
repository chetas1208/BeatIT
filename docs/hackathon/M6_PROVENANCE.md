# M6 Shadow Trial Provenance Contract

Last updated: 2026-09-26

## Status

This document is the M6 provenance design and schema audit only. It does not
implement the Shadow Trial Engine and does not claim that M6 is complete.

The M6 engine must compare each baseline ensemble member with the
counterfactual result derived from that same member. A trial must never create
an independently sampled scenario population.

## Provenance objectives

Every persisted Shadow Trial must answer these questions without consulting
process memory or UI state:

1. Which immutable patient/twin snapshot was the origin?
2. Which exact persisted baseline ensemble was used?
3. Which exact scenario definition was applied?
4. Which deterministic engines, distributions, priors, and metrics produced
   the result?
5. Which seed produced the baseline members, and was any additional sampling
   performed for the scenario branch?
6. Which evidence and synthetic-lineage declarations support the input?
7. When was the origin observed, the ensemble created, and the trial run?
8. Which baseline member was paired with which scenario member?

The Python backend remains the numerical and provenance authority. Frontend
state may display these fields but must not reconstruct them or infer missing
lineage.

## Required M6 provenance envelope

The future Shadow Trial response and its persisted record must contain one
immutable provenance envelope with the following fields. Names below use the
existing backend `snake_case` wire convention.

| Field | Required meaning | Current schema status |
|---|---|---|
| `trial_id` | Stable identifier for this Shadow Trial result. | Missing; new M6 field. |
| `provenance_schema_version` | Version of this envelope, independent of engine versions. | Missing; new M6 field. |
| `status` | Lifecycle state such as pending, completed, or failed. | Missing; new M6 field. |
| `origin_snapshot_id` | Immutable snapshot identity used to create the baseline ensemble. | Present as `EnsembleRequest.origin_snapshot_id` and `EnsembleResponse.origin_snapshot_id`. |
| `origin_case_id` | Canonical `CardiacTwinState.case_id` for the origin snapshot. | Present inside `state`; not promoted into the M5.5 provenance object. M6 must expose it explicitly or provide an unambiguous state reference. |
| `origin_timestamp` | Timestamp of the origin snapshot, normalized to UTC ISO-8601. | Present in `EnsembleProvenance`; currently derived from `state.created_at`. |
| `origin_quality` | One of `observed`, `derived`, `interpolated`, or `synthetic`. | Present in request, samples, and provenance. |
| `origin_provenance` | Full source records for the origin snapshot. | Present as an untyped `list[dict]`; M6 must preserve it losslessly. |
| `origin_evidence_ids` | Evidence IDs attached to the origin snapshot. | Present as request `evidence_ids` and merged response `provenance.evidence_ids`; the snapshot-level name is not explicit in Python. |
| `origin_state_digest` | Stable digest of the canonical origin state used by the trial. | Missing; required to detect state substitution while retaining the existing snapshot ID. |
| `baseline_ensemble_id` | ID of the exact persisted M5.5 ensemble consumed by M6. | M5.5 `EnsembleResponse.id` exists; a first-class M6 reference is missing. |
| `baseline_ensemble_schema_version` | Contract version of the baseline ensemble payload. | The wire contract is documented as `m5.5-backend-ensemble-v1`, but it is not carried as a response field. |
| `baseline_requested_sample_count` | Number of baseline members requested. | Present as `requested_sample_count`. |
| `baseline_accepted_sample_count` | Number of baseline members eligible for pairing. | Present as `accepted_sample_count`. |
| `baseline_rejected_sample_count` | Number of rejected baseline members and their reasons. | Count and per-sample reasons are present. |
| `baseline_seed` | Seed used to produce the persisted baseline members. | Present as `seed`; M6 should rename or nest it to make its role unambiguous. |
| `baseline_parameter_distributions` | Exact serialized input distributions, bounds, source, rationale, version, and evidence IDs. | Present as `parameter_distributions`; must be copied or referenced immutably. |
| `distribution_config_version` | Version of the distribution construction/configuration. | Present in `EnsembleProvenance`. |
| `prior_version` | Version of priors used to configure uncertain inputs. | Present in `EnsembleProvenance`; current value is `m5-priors-v1`. |
| `baseline_physiology_version` | Version of the deterministic evaluator used for baseline outputs. | Present as `physiology_version`; M6 must retain it under an explicit baseline role. |
| `baseline_assumptions` | Assumptions that affect interpretation, including independent input sampling. | Present as `assumptions`; must be retained. |
| `scenario_id` | Stable scenario definition identity. | M4 `ScenarioDefinition.id` exists; not part of the M5.5 ensemble provenance envelope. |
| `scenario_definition_version` | Version of the scenario-definition contract or persistence format. | M4 persistence has `SCENARIO_PERSISTENCE_VERSION = 1`; it is not included in the definition itself. |
| `scenario_definition_digest` | Stable digest of the exact scenario label, origin, parameters, units, and timestamps used. | Missing; required for replay and tamper/substitution detection. |
| `scenario_label` | Human-readable scenario label. | Present in M4 `ScenarioDefinition.label`; must be copied into the M6 record. |
| `scenario_parameters` | Ordered bounded changes with parameter, baseline, value, delta, and unit. | Present in M4 `ScenarioDefinition.parameters`; M6 must preserve order and numeric values exactly. |
| `scenario_origin_snapshot_id` | Snapshot from which the scenario was forked. | Present indirectly in M4 `ScenarioDefinition.origin.snapshotId`; M6 must require equality with `origin_snapshot_id`. |
| `scenario_created_at` | Timestamp at which the immutable scenario definition was created. | Present as M4 `ScenarioDefinition.createdAt`. |
| `scenario_engine_version` | Version/identity of the deterministic M4 scenario application seam. | Missing as a machine-readable version; current provenance only uses the note `M4 deterministic scenario engine`. |
| `shadow_trial_engine_version` | Version of paired execution, validity, and pairing behavior. | Missing; new M6 field. |
| `effect_metrics_version` | Version of delta/statistical definitions and category thresholds. | Missing; new M6 field. |
| `pairing_policy` | Explicit policy stating baseline sample `i` maps only to scenario sample `i`; no resampling. | Missing; required M6 assertion. |
| `pair_count` | Number of attempted baseline/scenario pairs. | Missing; new M6 result field. |
| `pair_rejection_count` | Number of invalid pairs retained with reasons. | Missing; new M6 result field. |
| `pairing_digest` | Digest of ordered `(baseline_sample_id, scenario_sample_id, baseline_parameter_digest)` records. | Missing; required for pair identity verification. |
| `trial_created_at` | Wall-clock time the trial record was created. | Missing; M5.5 `created_at` currently aliases the origin state timestamp. |
| `trial_completed_at` | Wall-clock time the trial reached a terminal state. | Missing; new M6 field. |
| `engine_started_at` / `engine_completed_at` | Optional execution timing for performance and failure diagnosis. | Missing; recommended M6 fields. |
| `evidence_ids` | Union of origin, distribution, scenario, and explicitly supplied trial evidence IDs. | M5.5 has merged ensemble evidence IDs; scenario/trial-level aggregation is missing. |
| `lineage` | Explicit observed/derived/interpolated/synthetic declarations for origin, baseline, scenario, and result. | M5.5 has one `origin_quality`; M6 needs stage-specific lineage. |
| `safety_disclaimer` | Canonical educational-use disclaimer carried through the response. | Present and validated in `EnsembleResponse`; M6 must preserve it. |

### Pair-level required record

In addition to the envelope, each pair must carry enough identity to prove that
the comparison is paired:

```json
{
  "pair_id": "pair-<stable-id>",
  "baseline_sample_id": "<persisted-baseline-sample-id>",
  "scenario_sample_id": "<derived-scenario-sample-id>",
  "baseline_sample_index": 0,
  "baseline_parameter_digest": "sha256:<digest>",
  "scenario_application": "same-baseline-parameters-no-resampling",
  "valid": true,
  "rejection_reasons": [],
  "effects": {
    "ejection_fraction_pct": {"baseline": 55.0, "scenario": 57.0, "delta": 2.0, "unit": "%"}
  }
}
```

The example is illustrative only. Numeric values and IDs are not a fixture and
must not be copied into implementation tests as if they were canonical.
`scenario_sample_id` identifies the derived result; it must not imply that a
second random sample was drawn.

## Timestamp rules

M6 must distinguish these timestamps:

- `origin_timestamp`: when the source snapshot represents the patient/twin
  state. This is not the trial execution time.
- `baseline_ensemble_created_at`: when the persisted baseline ensemble was
  generated. This is not currently represented accurately by M5.5 because
  `EnsembleProvenance.created_at` is populated from `state.created_at`.
- `scenario_created_at`: when the immutable M4 scenario definition was created.
- `trial_created_at`: when M6 accepted the trial request and created its record.
- `engine_started_at` and `engine_completed_at`: execution interval, if
  recorded.
- `trial_completed_at`: when the persisted result became terminal.

All timestamps must be normalized UTC ISO-8601 strings with millisecond
precision, following `normalizeTwinTimestamp` on the frontend boundary. The
backend should use timezone-aware values for new M6 fields. A timestamp copied
from the origin is acceptable only when it is explicitly named
`origin_timestamp`.

## Seed and no-resampling rules

The baseline ensemble's `seed` is the only required random seed for the paired
trial. M6 must:

- persist it as `baseline_seed`;
- retain the exact baseline sample order and IDs;
- apply the scenario deterministically to each accepted baseline sample's
  parameters;
- record `pairing_policy = "same-baseline-member-no-resampling"`;
- record `scenario_resampling = false` (or an equivalent machine-readable
  boolean);
- reject or fail closed if a scenario branch attempts to create an unrelated
  sample population.

If a future implementation needs randomness for a non-physiological operation,
it must use a separately named seed and document its role. It must not be
silently substituted for `baseline_seed` or used to redraw latent physiology.

## Priors, distributions, and engine versions

The provenance record must retain the exact values, not only labels, for:

- `physiology_version` / `baseline_physiology_version`;
- `distribution_config_version`;
- `prior_version`;
- every parameter distribution's family, parameters, bounds, source,
  rationale, version, and evidence IDs;
- `scenario_engine_version`;
- `shadow_trial_engine_version`;
- `effect_metrics_version`;
- `provenance_schema_version`.

The current M5.5 values audited in the repository are:

```text
physiology_version           = m5.5-ensemble-projection-v1
distribution_config_version = m5.5-backend-ensemble-v1
prior_version                = m5-priors-v1
```

These are baseline ensemble versions, not an M6 engine version. M6 must not
reuse `parent_scenario_id` as a substitute for a complete scenario definition;
that field is optional in the current M5.5 request and is insufficient to
reconstruct the applied changes.

## Evidence and synthetic lineage

Evidence aggregation must be deterministic and lossless:

```text
evidence_ids = unique_sorted(
    origin_snapshot.evidence_ids
    + origin_provenance[*].evidenceIds
    + baseline_parameter_distributions[*].evidence_ids
    + scenario_provenance[*].evidenceIds
    + explicitly supplied trial evidence_ids
)
```

The record must also retain the unflattened provenance entries. IDs alone are
not enough to explain whether a value came from a measurement, derivation,
prior, scenario, replay, or user annotation.

Required lineage rules:

- `origin_quality` is copied from the snapshot and is immutable for the trial.
- Any `synthetic_replay` source or replay note makes the relevant lineage
  synthetic; it must never be represented as observed.
- A synthetic demo fixture must carry an explicit fixture/evidence ID and a
  visible synthetic label in the API/UI.
- Derived scenario outputs must be marked derived/hypothetical and retain the
  baseline origin, rather than becoming observed evidence.
- M6 must not infer clinical evidence from a simulated effect or classify a
  positive/negative delta as treatment benefit/harm.
- Missing evidence is represented as missing; it is not replaced by a newly
  invented source record.

The current M5.5 validator rejects `origin_quality="observed"` when supplied
origin provenance contains `source="synthetic_replay"` or a replay note. That
is a useful guard but is not a complete M6 lineage policy: it does not require
all synthetic sources to be declared, and `origin_provenance` remains an
untyped dictionary list.

## Audit against current contracts

### Python backend

`python/hearttwin/ensemble.py` currently provides:

- `EnsembleRequest`: origin snapshot ID, typed cardiac state, seed, sample
  count, complete parameter distributions, version strings, origin quality,
  optional parent scenario ID, provenance, and evidence IDs.
- `EnsembleResponse`: stable ensemble ID, accepted/rejected samples,
  distributions, parameter distributions, provenance, warnings, safety
  disclaimer, and representative IDs.
- `EnsembleProvenance`: origin timestamp/quality, source records, evidence,
  seed, physiology/distribution/prior versions, creation field, and
  assumptions.

These contracts are sufficient as M5.5 baseline input/output, but not as the
complete M6 trial contract. In particular, they lack a trial ID, scenario
definition digest, pair records, explicit execution timestamps, stage-specific
lineage, and a no-resampling assertion.

### Frontend time and scenario contracts

`web/lib/twin/time/contracts.ts` provides `TwinSnapshot` with ID, timestamp,
state, evidence IDs, changed fields, provenance, and quality. It also provides
`TwinProvenance` with source, source ID, method, confidence, evidence IDs, and
note.

`web/lib/twin/scenario/types.ts` provides `ScenarioDefinition` with ID, label,
origin metadata, ordered parameter changes, and `createdAt`; its origin holds
snapshot ID, patient ID, timestamp, state, provenance, evidence IDs, and
quality. `ScenarioResult` additionally provides baseline, scenario state,
component deltas, provenance, status, warnings, and `computedAt`.

These are suitable source contracts for M6, but the frontend contracts do not
provide backend-authoritative digests or a Shadow Trial envelope. The frontend
must therefore send the immutable scenario definition to a future backend M6
endpoint and consume the returned provenance, rather than calculate trial
lineage locally.

### Persistence

`python/hearttwin/storage/ensemble_store.py` persists the complete M5.5 JSON
response by ensemble ID and survives process restart. It does not persist
Shadow Trial records, scenario-definition digests, or pair-level lineage.
M6 requires a separate trial persistence record or an explicitly versioned
extension; overwriting the baseline ensemble would destroy the source needed
for audit and replay.

## M6 acceptance checks for this contract

An implementation may only claim provenance closure when tests demonstrate:

1. A trial cannot be created without every required envelope field.
2. The referenced baseline ensemble exists and its ID, seed, versions, counts,
   parameter distributions, and origin snapshot digest match the trial.
3. The scenario definition's origin snapshot equals the baseline origin.
4. Every accepted baseline sample has exactly one scenario result with the same
   sample index and baseline parameter digest.
5. No scenario-side resampling occurs; repeated runs with the same immutable
   inputs are identical.
6. Pair order changes are either rejected or produce a distinct, explicitly
   versioned result rather than silently changing pair identity.
7. Invalid pairs remain present with rejection reasons and reconciled counts.
8. Origin, baseline, scenario, and trial timestamps remain distinct and are
   normalized.
9. Synthetic fixtures remain synthetic through baseline, scenario, pair, and
   trial output lineage.
10. Restart retrieval returns the same immutable provenance and pair records.
11. API, Python, frontend runtime, lint, build, golden-vector, no-op, and
    reproducibility tests pass before M6 completion is reported.

## Historical audit conclusion

The M5.5 baseline contains most inputs needed to begin M6, including durable
ensemble IDs, seeds, distribution/prior/physiology versions, evidence, and
synthetic quality. At the time of this design audit, M6 provenance was **not
yet implemented**. The implementation that followed adds the first-class
trial envelope, pair identity, no-resampling assertion, scenario lineage, and
result fingerprint; timestamp and hosted-ownership limitations remain bounded
in the current completion record.

No implementation files were modified by this audit. The audit is retained as
historical design evidence.

## Current implementation note

The implemented M6 contracts now carry the trial definition, baseline ensemble
reference, scenario parameter changes, seed and version lineage, pair counts,
effect metrics, warnings, fingerprint, scenario-definition hash, pairing
policy, and the canonical safety disclaimer. Each generated M5.5 sample also
persists the exact projection base used by the canonical evaluator; M6 refuses
to run against a legacy sample that lacks that base rather than double-applying
sampled parameters.

The remaining limitations are the trusted-demo persistence boundary and the
lack of pointwise PV samples; they are recorded in `M6_COMPLETION.md`.
