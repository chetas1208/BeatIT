# M6 Shadow Trial Architecture

## Data flow

```text
persisted M5.5 EnsembleResponse
          ↓
validated ScenarioDefinition
          ↓
same-sample pairing by baseline sample ID
          ↓
canonical Python M5.5 evaluator
          ↓
paired states and scenario-minus-baseline deltas
          ↓
descriptive effect distributions
          ↓
immutable SQLite ShadowTrialResult
```

M6 does not generate a second ensemble. The stored baseline sample parameters
are copied, only explicitly selected scenario parameter values are changed, and
all other latent values remain identical. Pair output is ordered by stable
baseline sample identity, so array order cannot alter the result.

## Execution and failure semantics

The current implementation is synchronous and runs in `asyncio.to_thread` from
FastAPI. This is truthful progress: the API does not expose a fake progress
bar. A completed request returns `status=complete`; a run with zero valid pairs
returns `status=failed` with every invalid pair and reason persisted.

Missing baseline ensembles return 404. Invalid scenario contracts or origin
mismatches return 422. Persistence failures return 503. Baseline records are
never mutated, and Shadow Trial IDs are immutable: identical deterministic
replays are idempotent, while a same-ID/different-payload write is rejected.

## Numerical authority

`python/hearttwin/ensemble.py` remains the numerical authority. M6 delegates
to its existing `_baseline`, `_evaluate`, and `_derived_state` seam. The
frontend M4 evaluator is not called for M6 results; the frontend submits
scenario metadata and renders the backend response.

## Scope boundaries

M6 exposes compact paired inspection, scalar effect distributions, and an
explicitly unavailable pointwise PV boundary. It does not split the 3D heart
(M7), perform sensitivity/information-gain analysis (M8), rank scenarios, or
make clinical value judgments from metric direction.
