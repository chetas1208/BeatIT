# M10 Reproducibility Review

**Contribution:** A07 — deterministic reproducibility and demo fixture lifecycle
**Date:** 2026-09-26
**Scope:** `scripts/create_synthetic_fixtures.py`, `scripts/seed-demo.sh`, `scripts/reset-demo.sh`, and `scripts/demo-preflight.sh`

## Result

**PASS for the local synthetic demo lifecycle.** The canonical fixtures, generated
demo state, and deterministic pipeline outputs were stable across repeated seeds
and a reset/reseed cycle. The preflight passed all local checks.

This is not evidence of deployed HTTP reproducibility: the preflight HTTP branch
was not exercised because `E2E_BASE_URL` was not set.

## Commands and observed evidence

All commands were run from the repository root on 2026-09-26.

### Seed, repeat, reset, reseed

```text
./scripts/seed-demo.sh                         PASS
./scripts/seed-demo.sh                         PASS
./scripts/reset-demo.sh                        PASS
test that data/demo/state.json is absent       PASS
./scripts/reset-demo.sh                        PASS (already reset)
./scripts/seed-demo.sh                         PASS
./scripts/demo-preflight.sh                    PASS
```

Each seed run reported:

```text
All fixtures already up to date.
validated_fields=6
EF=58.3
CO=5.04
has_pv_loop=True
scenarios=4
overall_score=0.9
RESULT: OK
DEMO READY
```

The generated case UUID changed on each run, as expected for a newly created
in-process case. No deterministic result changed.

### SHA-256 evidence

The following hashes were identical after the first seed, second seed, and the
reset/reseed cycle:

| Artifact | SHA-256 |
| --- | --- |
| `fixtures/hearttwin/manual_baseline.json` | `1e448677700a64058df5038dd60f8f5a6516dc2df9bff5eb5e71f6fbd335b5ca` |
| `fixtures/golden/probabilistic/fixed-only.json` | `ac3d4334162541b0c4aec6d1cca61210826737f1d82f9295f7ff02c20178fb84` |
| `fixtures/golden/shadow_trials/synthetic-demo-case.json` | `6ab9a8c62f80e1a373ee01ce8d6b8eca8b87041abe694331f5a913b081406530` |
| `data/demo/state.json` | `ca710f80a1e270dee2094b5003d792286814941a5c578655e69f29ffc1d47d2c` |

`data/demo/state.json` records the first three fixture hashes, the
`m10-demo-v1` state version, `synthetic_demo` status, and the explicit
precomputed-fallback label. The recorded values matched the independently
computed `sha256sum` output.

## Preflight result

With no `E2E_BASE_URL`, local preflight reported:

```text
READY    python
READY    node
READY    curl
READY    demo fixture
READY    ensemble golden
READY    Shadow Trial golden
READY    model manifest
SKIP     HTTP checks (set E2E_BASE_URL)
DEMO READY
```

## Idempotence and reset assessment

- `create_synthetic_fixtures.py` is content-idempotent: it reported that all
  fixtures were already current on every seed and uses write-if-changed logic.
- `seed-demo.sh` is state-reproducible: it rewrites the same canonical JSON
  state and hashes on every run.
- `reset-demo.sh` has a narrow deletion target: only
  `data/demo/state.json` is removed. A second reset is a successful no-op.
- The smoke path is deterministic in its measured outputs, but case identifiers
  are intentionally generated per run and must not be used as golden values.

## Boundaries and follow-up

- No real patient data, network download, provider key, or optional model was
  required for this evidence.
- HTTP health/system-check reproducibility remains unverified in this run; set
  `E2E_BASE_URL` and rerun `scripts/demo-preflight.sh` against the deployed or
  locally running API before release.
- The seed script runs the real in-process extraction, operation, recovery, and
  evaluator paths. It does not prove browser rendering, reverse-proxy behavior,
  persistence across a service restart, or remote model availability.
