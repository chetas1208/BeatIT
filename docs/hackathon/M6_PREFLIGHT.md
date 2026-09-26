# M6 Preflight Audit — Shadow Trial Engine

Date: 2026-09-26  
Scope: read-only audit of the existing M4/M5/M5.5 implementation and
documentation. This audit did not modify implementation files, shared/root
documentation, or the M6 plan.

## Historical verdict

**At audit time, M6 was not ready for execution or integration.** The M5.5 baseline ensemble is
usable as a persisted input, and its active frontend path is backend-authoritative,
but the required cross-layer canonical scenario seam does not exist. A partial
M6 scaffold appeared in the shared workspace during this audit; it now includes
an isolated paired engine, contracts, identity helpers, metrics, and a store,
but no API or persistence integration. The M4 `ScenarioDefinition` is still evaluated by a
separate frontend engine, while the M5.5 backend has a different projection
formula and accepts only sample distributions. Starting paired shadow trials
before resolving that split would make the paired deltas non-reproducible across
the product layers.

At that time M6 should remain in preflight until blockers B1–B4 below are repaired or
explicitly bounded by a reviewed architecture decision.

## Prerequisite matrix

| Prerequisite | Finding | Exact evidence | M6 impact |
|---|---|---|---|
| Canonical probabilistic engine | **Partial / blocker** | Active Python ensemble sampling and projection are in `python/hearttwin/ensemble.py:343-390,410-458`. The concurrent isolated trial engine applies a separate M4-style formula at `python/hearttwin/shadow_trial_engine.py:358-407`. The M5.5 audit records the retained frontend runner as another divergent implementation in `docs/hackathon/M5_5_NUMERICAL_AUDIT.md:22-28,74-102`. | M6 must use one evaluator for baseline and scenario twins. The current M5.5 projection, M4 propagation, and new trial engine are not yet one canonical numerical contract. |
| Cross-layer numerical parity | **Fail** | M5.5 documents separate versioning and non-equivalence in `docs/hackathon/M5_ARCHITECTURE.md:22-29` and `docs/hackathon/M5_5_COMPLETION.md:52-57`. The concrete formula differences are recorded in `docs/hackathon/M5_5_NUMERICAL_AUDIT.md:84-95`. | A paired delta is not credible if baseline and counterfactual can be evaluated by different formulas depending on the caller. |
| Durable baseline persistence | **Pass with limitation** | `python/hearttwin/storage/ensemble_store.py:52-86` creates file-backed SQLite; `:88-138` performs parameterized atomic persistence/retrieval. Restart/process coverage is in `python/hearttwin/tests/test_ensemble_store.py:55-110`. A concurrent M6 store scaffold exists at `python/hearttwin/storage/shadow_trial_store.py:32-114`. | A baseline response can be retrieved, but both stores are replaceable/upsert-based (`ensemble_store.py:22-23,88-113`; `shadow_trial_store.py:68-84`), not immutable trial-input stores. M6 needs immutability or content-addressed validation, plus API integration. |
| RNG and seeded reproducibility | **Pass for M5 baseline; incomplete for M6 contract** | Python uses one local `random.Random(request.seed)` at `python/hearttwin/ensemble.py:410-417`; seed is carried into samples and provenance at `:425,435`. Same-seed coverage is in `python/hearttwin/tests/test_ensemble.py:338-356`. | M6 should not resample. It must reuse each persisted sample's parameter vector. If any new sampling is introduced, record the RNG algorithm/runtime version; the current provenance records only the seed. |
| Sample lineage | **Partial / blocker for paired trials** | `EnsembleSample` carries ID, index, seed, origin snapshot, and quality at `python/hearttwin/ensemble.py:188-214`; `EnsembleProvenance` carries origin and optional `parent_scenario_id` at `:217-234`. The concurrent scaffold adds trial-level lineage at `python/hearttwin/shadow_trial_contracts.py:91-145` and pair identities at `python/hearttwin/shadow_trial_identity.py:33-110`. | The new fields are not yet connected to execution or API persistence. `parent_scenario_id` in M5.5 is metadata only, and the new identity tests currently fail. |
| Active frontend authority | **Pass for active M5 ensemble path; containment risk remains** | `web/lib/twin/scenario/useScenario.tsx:111-129` calls `generateBackendEnsemble`; `web/lib/twin/ensemble/backend.ts:53-68` calls the API and maps the response; `web/lib/twin/ensemble/adapter.ts:5-64` maps fields without recomputation. | The active plausible-twin UI is backend-authoritative. However, `web/lib/twin/ensemble/runner.ts` remains executable and is imported by historical tests (`web/lib/twin/ensemble/__tests__/runner.test.ts:5`, `provenance.test.ts:5`). M6 must not reuse it. |
| Synthetic/observed lineage | **Partial** | The request requires `origin_quality` and rejects supplied replay provenance labeled observed at `python/hearttwin/ensemble.py:77-109`. M5.5 records the remaining caller-trust limitation in `Progress.md:50` and `docs/hackathon/OBSERVED_SYNTHETIC_POLICY.md:40-50`. | M6 fixtures can proceed only if synthetic quality is preserved through baseline, scenario, pair, and effect outputs; caller-supplied lineage is not a complete trust boundary. |
| ScenarioDefinition | **Partial / blocker** | M4 defines `ScenarioDefinition` in TypeScript at `web/lib/twin/scenario/types.ts:35-52`; `propagateScenario` constructs/evaluates it at `web/lib/twin/scenario/propagation.ts:236-317`; persistence is local-storage-safe at `web/lib/twin/scenario/persistence.ts:264-298`. Concurrent Python contracts exist in both `python/hearttwin/shadow_trial_contracts.py:71-145` and `python/hearttwin/shadow_trial_engine.py:108-133`. | The duplicate Python contract definitions are not wired to the frontend or API, and neither establishes a shared numerical evaluator or canonical hash. |
| Scenario state isolation | **Pass locally; not available at backend trial boundary** | M4 clones/freezes origins in `web/lib/twin/scenario/propagation.ts:194-203,271-279`, and `web/lib/twin/scenario/fork.ts:61-75` provides immutable snapshot forks. | The guarantee is confined to the frontend M4 path. M6 needs equivalent backend isolation so one pair cannot mutate the baseline or another pair. |

## Blockers and repair recommendations

### B1 — Establish one canonical evaluator before paired effects

The M4 evaluator and M5.5 evaluator are materially different. M4 uses the
frontend relationship `base.sv * 0.55` for the afterload contribution and clamps
SV/CO; M5.5 uses `base.edv * 0.25` and a different projection path. These
differences are documented rather than resolved.

Recommended repair:

1. Choose the canonical evaluator and version it explicitly.
2. Implement that evaluator in the Python backend, or define a genuinely shared
   executable contract before adding M6.
3. Create cross-layer golden vectors for no-op, single-parameter, and bounded
   multi-parameter scenarios.
4. Keep the frontend as a request/visualization layer only for M6.

### B2 — Complete the backend ScenarioDefinition/application seam

`parent_scenario_id` cannot substitute for a scenario definition. M6 needs a
validated, serializable scenario payload containing parameter changes, origin
identity, bounds/version, and a stable content hash. The backend must apply that
payload to each baseline sample's own parameter vector/state without drawing a
new sample population.

Recommended repair:

- Review and integrate the new Python contract as the versioned backend wire
  contract equivalent to the M4 `ScenarioDefinition`.
- Add a pure backend function such as `apply_scenario_to_sample` with explicit
  no-op and immutability behavior.
- Reject definitions whose origin snapshot, parameter set, bounds, or version do
  not match the persisted baseline contract.

### B3 — Add pair-level lineage and immutable trial persistence

The current store proves restart-safe JSON retrieval, not an immutable M6 trial
record. M6 requires a persisted relationship such as:

```text
trial_id
  baseline_ensemble_id
  scenario_definition_hash
  pair_id -> baseline_sample_id + counterfactual_sample_id
  baseline_seed / parameter fingerprint
```

Recommended repair:

- Persist the exact baseline ensemble reference and canonical scenario hash.
- Derive stable pair IDs from trial ID, baseline sample ID, and scenario hash.
- Validate on read that every counterfactual retains the source sample's latent
  parameters and that pair order is stable.
- Use create-once or content-addressed semantics for trial inputs; do not allow
  an existing baseline/trial ID to be silently replaced.

### B4 — Make the RNG/reproducibility boundary explicit

M5.5's seeded Python RNG is adequate for generating the baseline ensemble, and
M6 should reuse those stored draws. The current provenance does not record an
RNG implementation/version, so rerunning baseline generation under a changed
Python runtime is not a fully specified numerical contract.

Recommended repair:

- Treat the persisted baseline sample parameters as the M6 source of truth and
  perform no M6 sampling.
- Record `rng_algorithm` and runtime/engine version in future baseline metadata,
  or freeze the golden baseline fixture as the trial input.

## Concurrent M6 scaffold review

The following untracked files appeared after the initial M5/M5.5 scan and were
not created or modified by this audit:

- `python/hearttwin/shadow_trial_contracts.py` — Pydantic scenario, pair,
  provenance, and effect contracts.
- `python/hearttwin/shadow_trial_identity.py` — deterministic pair-ID helpers.
- `python/hearttwin/shadow_trial_metrics.py` — intended effect reducers.
- `python/hearttwin/shadow_trial_engine.py` — isolated paired execution engine.
- `python/hearttwin/storage/shadow_trial_store.py` — SQLite trial store.
- `python/hearttwin/tests/test_shadow_trial_contracts.py` and
  `test_shadow_trial_identity.py` — focused scaffold tests.

This is useful groundwork but does not clear the preflight gate:

- The engine is isolated and has no FastAPI integration; no API route invokes
  `run_shadow_trial`.
- `python/hearttwin/api.py` has no Shadow Trial create/retrieve/effects routes.
- `shadow_trial_store.py:68-84` silently upserts an existing trial ID, so it is
  not yet immutable persistence.
- `shadow_trial_engine.py:64-260` defines a second set of scenario, pair, and
  result contracts distinct from `shadow_trial_contracts.py:51-288`; this is a
  contract-authority split.
- `shadow_trial_engine.py:358-407` applies the M4-style evaluator rather than
  the M5.5 Python ensemble projection, so the canonical-engine blocker remains.
- The isolated scaffold test run is green at the latest snapshot (**17 passed,
  8 warnings**), but it does not test API integration, persistence, or a
  cross-layer golden vector. An earlier snapshot of the concurrent scaffold had
  **11 passed, 1 failed**; the workspace changed while this audit was running.

The scaffold was therefore **unintegrated and incomplete** at audit time. It
has since been consolidated into the active M6 path; current status is
maintained in `M6_COMPLETION.md`.

## What is already usable

- The Python backend validates accepted/rejected samples, summaries, IDs,
  provenance, and safety disclaimer (`python/hearttwin/ensemble.py:255-317`).
- The baseline ensemble is persisted in file-backed SQLite and survives a
  separate process (`python/hearttwin/tests/test_ensemble_store.py:64-110`).
- The active frontend maps backend output without running a second ensemble
  calculation (`web/lib/twin/ensemble/backend.ts:53-68`,
  `web/lib/twin/ensemble/adapter.ts:5-64`).
- M4 scenario definitions and immutable origin semantics exist as a frontend
  contract (`web/lib/twin/scenario/types.ts:44-60`), but they are not yet a
  backend M6 contract.

## M6 implementation gate — historical checklist

The following were the pre-implementation gates; the current completion record
links the evidence collected after this audit:

- one canonical evaluator selected and golden-tested across the backend seam;
- a backend `ScenarioDefinition` and pure per-sample application function;
- persisted baseline ensemble retrieval by stable ID;
- immutable baseline/trial input records;
- pair IDs linking each baseline sample to exactly one counterfactual;
- scenario hash, baseline ensemble ID, sample parameter fingerprint, and origin
  quality carried through trial provenance;
- no-op, identity, order, immutability, mismatch, and same-input reproducibility
  tests;
- explicit confirmation that the frontend does not execute paired-trial math.

The existing `docs/hackathon/M6_AGENT_PLAN.md` has an empty dispatch ledger at
the time of this audit (`:66-73`). This preflight does not count or certify the
future M6 multi-agent contribution gate.

## Verification evidence

Commands run from `/home/923873155/BeatIT`:

```text
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev pytest -q \
  python/hearttwin/tests/test_ensemble.py \
  python/hearttwin/tests/test_ensemble_api.py \
  python/hearttwin/tests/test_ensemble_store.py \
  python/hearttwin/tests/test_probabilistic_golden.py
83 passed in 2.18s

cd web && npm run test:runtime
2 passed, 0 failed

cd web && npx tsc --noEmit
passed with no output

rg --files python web | rg 'shadow_trial|shadowTrial'
python/hearttwin/shadow_trial_contracts.py
python/hearttwin/shadow_trial_identity.py
python/hearttwin/shadow_trial_metrics.py
python/hearttwin/shadow_trial_engine.py
python/hearttwin/storage/shadow_trial_store.py
python/hearttwin/tests/test_shadow_trial_contracts.py
python/hearttwin/tests/test_shadow_trial_identity.py
python/hearttwin/tests/test_shadow_trial_engine.py

PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev pytest -q \
  python/hearttwin/tests/test_shadow_trial_contracts.py \
  python/hearttwin/tests/test_shadow_trial_identity.py \
  python/hearttwin/tests/test_shadow_trial_engine.py
17 passed, 8 warnings

PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev \
  python -c 'import python.hearttwin.shadow_trial_metrics'
passed
```

These are M5/M5.5 regression and seam checks plus the observed isolated M6
scaffold tests. No M6 API/persistence integration test was possible because
those routes and integrations do not exist.

## Files changed by this audit

- `docs/hackathon/M6_PREFLIGHT.md` — added this read-only preflight record.

No implementation files, shared/root documentation, or existing M6 planning
files were modified by this preflight snapshot.

## Post-preflight implementation note

This file is retained as the historical preflight record. The lead
subsequently repaired the identified seams: `shadow_trial_engine.py` now
delegates to the canonical Python M5.5 evaluator without resampling,
`shadow_trial_store.py` is immutable file-backed SQLite, the four Shadow Trial
API routes are integrated, and focused API/store/golden coverage is present.
The remaining M6 blockers are environmental browser/accessibility validation
and the separately evidenced 20-contribution campaign gate; see
`M6_COMPLETION.md` for current status.
