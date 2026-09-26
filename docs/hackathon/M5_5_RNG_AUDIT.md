# M5.5 RNG Reproducibility Audit

Date: 2026-09-26  
Scope: Python plausible-twin ensemble, active frontend ensemble flow, adjacent
frontend synthetic-input path, and reproducibility tests. Read-only production
audit; no M6, M7, or M8 work.

## Verdict

The canonical ensemble sampler has no hidden or unseeded RNG:

- Python creates one local `random.Random(request.seed)` per ensemble run.
- Every stochastic distribution draw receives that local generator explicitly.
- The active frontend does not sample or evaluate physiology; it forwards the
  caller-provided seed to the Python endpoint and maps the response.
- Sample IDs and ensemble IDs are deterministic hashes/string compositions, not
  random identifiers.

M5.5 RNG closure is therefore **PASS for the canonical ensemble path**, but
**PARTIAL for full demo-input replay**. The active intake UI has a separate
synthetic-vitals convenience action that calls `Math.random()` without a seed.
Using that action changes the origin inputs before the seeded ensemble request,
so the ensemble seed alone cannot replay the complete user flow.

## Active path evidence

### Python sampler

- `python/hearttwin/ensemble.py:13` imports the standard `random` module; no
  module-level random draw or global RNG seeding is used.
- `python/hearttwin/ensemble.py:300-313` accepts an explicit `random.Random`
  instance. Fixed distributions consume no random values; normal, lognormal,
  uniform, and empirical families use only `rng.gauss`,
  `rng.lognormvariate`, `rng.uniform`, and `rng.choice`.
- `python/hearttwin/ensemble.py:91-95` restricts seeds to safe integers.
- `python/hearttwin/ensemble.py:367-373` creates exactly one local generator
  from the request seed and samples each requested member in a fixed loop.
- `python/hearttwin/ensemble.py:373-379` evaluates and rejects after all
  parameter draws; there is no rejection resampling or second RNG source.
- `python/hearttwin/ensemble.py:391-393` derives the ensemble ID with sorted
  JSON plus SHA-256. `python/hearttwin/ensemble.py:380` derives sample IDs from
  the origin snapshot ID and sample index.

The draw assignment is deterministic for an identical request, including the
order of `request.distributions`. The active request builder supplies a stable
five-parameter order at `web/lib/twin/ensemble/backend.ts:16-22`.

### Active frontend flow

- `web/lib/twin/scenario/useScenario.tsx:111-129` obtains the seed from the
  caller, defaulting to `1208`, and calls `generateBackendEnsemble`.
- `web/lib/twin/ensemble/backend.ts:13` documents that the frontend builds only
  distribution inputs; the backend samples and evaluates them.
- `web/lib/twin/ensemble/backend.ts:52-66` sends `seed` unchanged in the
  request to `/twin/ensemble` along with the snapshot and distributions.
- `python/hearttwin/api.py:156-164` validates the request and runs the seeded
  backend operation in the API thread.
- `web/lib/twin/ensemble/adapter.ts:5-6` and `:14-64` map the backend response
  without recalculating samples, metrics, or representatives.
- `web/lib/twin/ensemble/index.ts:4-6` explicitly identifies the local
  `runner.ts` as historical and exports the backend adapter as the active seam.

No `Math.random`, browser crypto RNG, or unseeded random call appears in the
active ensemble request/response path.

## Findings

### F1 — Upstream synthetic vitals are unseeded

Severity: medium reproducibility risk; active but separate from the canonical
ensemble sampler.

- `web/components/intake/CaseIntakePanel.tsx:138-145` implements Box-Muller
  normal sampling with `Math.random()` for both uniforms.
- `web/components/intake/CaseIntakePanel.tsx:152-164` uses those draws to fill
  synthetic vitals.
- The action is reachable from the UI at `:651-659`, confirmed at `:367-374`,
  and explicitly described as random synthetic data at `:780-813`.

This helper is not imported by `web/lib/twin/ensemble/backend.ts`, so it does
not alter the canonical ensemble RNG. However, when a user uses **Generate**
before creating the case, the generated vitals become upstream input. Replaying
the same ensemble seed then does not reproduce the same origin snapshot unless
the generated form values are also persisted or a separate seed is recorded.
The UI warning makes the behavior visible, but it is not reproducible.

### F2 — Historical frontend runner uses a different seeded PRNG

Severity: low current-runtime risk; medium future drift risk.

- `web/lib/twin/ensemble/distributions.ts:9-20` contains a deterministic custom
  PRNG, not `Math.random()`.
- `web/lib/twin/ensemble/runner.ts:115-150` creates and consumes that PRNG for
  a complete local ensemble implementation.
- Production import search finds `runner.ts` only in
  `web/lib/twin/ensemble/__tests__/runner.test.ts:5` and
  `web/lib/twin/ensemble/__tests__/provenance.test.ts:5`; the active UI imports
  `generateBackendEnsemble` at
  `web/lib/twin/scenario/useScenario.tsx:25`.

The historical PRNG is therefore not an active hidden source. It is not
cross-language equivalent to Python's `random.Random`, and its 32-bit seed
initialization at `distributions.ts:12` maps safe-integer seeds `0` and
`4294967296` to the same internal state. It must not be promoted as a second
production sampler without a separately versioned RNG contract.

### F3 — Metadata defaults can be nondeterministic, but are not sampler RNG

Severity: low boundary risk; not counted as a sampling failure.

- `python/hearttwin/schemas.py:248-250` defaults a missing cardiac state ID to
  `uuid4()` and its timestamp to `datetime.utcnow()`.
- The ensemble request requires a state at
  `python/hearttwin/ensemble.py:77-89`, and the active frontend sends the
  existing snapshot state at `backend.ts:54-65`.

These defaults do not feed `random.Random` or physiology sampling. They can make
metadata/provenance nondeterministic when upstream Python code constructs a
state without explicit identity/timestamp fields, so exact replay evidence must
use a fully materialized snapshot. They are outside the canonical ensemble
sampler and no production change is made in this audit.

## Test evidence

### Python

- `python/hearttwin/tests/test_ensemble.py:152-169` proves same-seed equality
  and changed-seed divergence.
- `python/hearttwin/tests/test_ensemble.py:205-230` proves seed propagation in
  response provenance and every sample.
- `python/hearttwin/tests/test_probabilistic_golden.py:51-62` validates all six
  canonical fixture requests and calls `run_ensemble(request)` twice for exact
  replay.
- The focused command below also exercises API routing and persistence without
  introducing a new RNG source.

### Frontend

- `web/tests/m5-runtime.test.ts:25-46` proves a seeded distribution draw
  replays exactly and validates distribution failures.
- `web/lib/twin/ensemble/__tests__/distributions.test.ts:112-122` checks replay
  for fixed, normal, uniform, and empirical families.
- `web/lib/twin/ensemble/__tests__/runner.test.ts:71-88` checks replay and
  changed-seed behavior for the retained historical runner.
- `web/tests/m5-runtime.test.ts:48-71` proves the active adapter preserves the
  backend response instead of recomputing physiology.

The runtime harness does not make a live HTTP request through
`generateBackendEnsemble`; the active network seam is verified by source-path
inspection and backend API tests. It also does not test reproducibility of the
intake synthetic-vitals button.

## Verification

Commands run from `/home/923873155/BeatIT`:

```text
PYTHONPATH=. uv run --project . --extra dev pytest -q \
  python/hearttwin/tests/test_ensemble.py \
  python/hearttwin/tests/test_ensemble_api.py \
  python/hearttwin/tests/test_probabilistic_golden.py \
  python/hearttwin/tests/test_ensemble_store.py
72 passed in 1.32s

cd web && npm run test:runtime
2 passed

cd web && npx tsc --noEmit
passed with no output
```

## Recommendations within the M5.5 boundary

- Treat Python `run_ensemble` plus the active backend adapter as the only
  canonical ensemble RNG path.
- If full demo replay is required, record or seed the intake synthetic-vitals
  generator in a future scoped change; do not silently reuse the ensemble seed
  for a different random stream.
- Keep `runner.ts` quarantined as historical test coverage. Any removal or
  migration is outside this read-only audit and is not M6 work.

No M6, M7, or M8 work was performed.
