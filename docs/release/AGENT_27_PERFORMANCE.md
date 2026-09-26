# M10.5 Agent 27 — Performance Benchmark

**Date:** 2026-09-26 UTC  
**Scope:** deterministic seed, API E2E, ensemble scaling, Shadow Trial scaling,
Missing Piece timing, frontend production build, and process resource usage.  
**Disposition:** **PASS for bounded local synthetic execution; OPEN for capacity,
concurrency, browser, proxy, and production-load claims.**

## Safety and isolation

- All inputs were checked-in synthetic fixtures; no patient data was used.
- Optional model providers were disabled for API probes:
  `MODEL_ENABLED=false`, `INTELLIGENCE_PROVIDER=disabled`,
  `OPENAI_ENABLED=false`, and `VISTA3D_ENABLED=false`.
- API E2E stores were temporary SQLite files and were removed after each probe.
- No large model checkpoint was loaded. Both RTX 3090 devices were idle at the
  host snapshot, with 1 MiB used on each.
- The frontend build wrote only normal ignored Next.js build output.

## Host and runtime

| Item | Observed value |
|---|---:|
| Timestamp | `2026-09-26T17:35:07Z` |
| Kernel / architecture | Linux 6.8.0-139-generic, x86_64 |
| CPUs | 20 |
| RAM | 125 GiB total; 105 GiB available |
| Swap | 8.0 GiB total; 6.2 GiB used |
| Root filesystem | 3.6 T total; 743 G available; 79% used |
| `/usr/data` | 2.7 T total; 2.2 T available; 22% used |
| GPU | 2 × NVIDIA GeForce RTX 3090, 24,576 MiB each |
| Driver | 535.288.01 |
| Python | 3.13.12 |
| Node build | Next.js 16.2.7 / Turbopack |

These are host observations, not capacity guarantees. Swap utilization is a
release risk for memory-sensitive workloads.

## Summary

| Workload | Result | Wall time | Peak RSS | Notes |
|---|---|---:|---:|---|
| `scripts/seed-demo.sh` | PASS | 0.43 s | 46.4 MiB | Fixtures, local smoke, and manifest/state write |
| Real API E2E verifier | PASS | 4.06 s | 470.8 MiB | Includes Python import and TestClient startup |
| Ensemble benchmark, 50–1000 | PASS | 2.67 s | 74.8 MiB | Five measured repetitions per count |
| Shadow Trial benchmark, 50–1000 | PASS | 8.56 s | 252.5 MiB | Three core/persist repetitions per count |
| Next production build | PASS | 25.90 s | 2,591.9 MiB | TypeScript, static generation, optimization |

Peak RSS values are `/usr/bin/time -v` process maxima converted from KiB. They
are not additive: each workload ran in a separate process.

## Seed and deterministic demo

Command:

```text
/usr/bin/time -v ./scripts/seed-demo.sh
```

Result:

```text
All fixtures already up to date.
validated_fields=6
EF=58.3 CO=5.04 has_pv_loop=True
scenarios=4
overall_score=0.9
RESULT: OK
DEMO READY
Elapsed: 0.43 s
Maximum resident set size: 47,536 KiB
Exit status: 0
```

The seed path is deterministic local smoke coverage, not a benchmark of a
remote model or deployed storage service.

## Ensemble scaling

Command:

```text
/usr/bin/time -v python scripts/benchmark_ensemble.py \
  --warmups 1 --repeats 5 --json
```

The benchmark uses `fixtures/hearttwin/manual_baseline.json`, seed `20260926`,
and measures `run_ensemble` including result construction and summary
statistics, but excludes fixture loading, request construction, and process
startup.

| Requested samples | Accepted | Min ms | Median ms | Mean ms | Max ms |
|---:|---:|---:|---:|---:|---:|
| 50 | 50 | 10.145 | 13.740 | 14.297 | 23.080 |
| 100 | 100 | 19.252 | 19.580 | 19.534 | 19.806 |
| 250 | 250 | 48.613 | 48.969 | 50.893 | 59.014 |
| 500 | 500 | 101.240 | 106.001 | 105.933 | 111.919 |
| 1000 | 1000 | 214.640 | 229.228 | 228.580 | 245.048 |

The requested release points, 50/100/500, completed with all samples accepted.
The local timings scale approximately linearly with sample count in this range.

## Shadow Trial scaling

Command:

```text
PYTHONPATH=. /usr/bin/time -v python scripts/benchmark_shadow_trial.py
```

The script uses `fixtures/golden/probabilistic/fixed-only.json`, applies the
synthetic `afterload_index` scenario, and measures baseline generation, paired
trial execution, JSON encoding, SQLite save, and SQLite reload. Every measured
row reloaded equal persisted data and had zero invalid pairs.

| Requested pairs | Valid | Baseline ms | Shadow core ms (3 runs) | Median JSON ms | Median save ms | Reload ms | Payload |
|---:|---:|---:|---|---:|---:|---:|---:|
| 50 | 50 | 9.122 | 35.247 / 48.089 / 24.016 | 7.545 | 6.204 | 3.474 | 486 KiB |
| 100 | 100 | 18.907 | 60.010 / 74.791 / 52.049 | 15.341 | 14.717 | 7.640 | 966 KiB |
| 250 | 250 | 64.767 | 131.412 / 150.186 / 131.066 | 39.952 | 30.136 | 18.020 | 2,409 KiB |
| 500 | 500 | 131.395 | 355.177 / 284.938 / 408.586 | 81.323 | 59.401 | 37.309 | 4,814 KiB |
| 1000 | 1000 | 210.050 | 706.297 / 737.093 / 709.029 | 161.607 | 114.943 | 76.672 | 9,623 KiB |

The direct script invocation without `PYTHONPATH=.` failed with
`ModuleNotFoundError: No module named 'python'`; the benchmark passed with the
repository root explicitly on `PYTHONPATH`. This is a harness portability issue,
not a measured engine failure.

## API E2E and Missing Piece

### Full verifier

Command:

```text
MODEL_ENABLED=false INTELLIGENCE_PROVIDER=disabled OPENAI_ENABLED=false \
VISTA3D_ENABLED=false PYTHONPATH=. /usr/bin/time -v \
python scripts/verify_api_e2e.py
```

Result:

```text
API E2E PASS
ENDPOINT CHECKS PASS 4
ENSEMBLE PASS
SHADOW_TRIAL PASS pairs=3
MISSING_PIECE PASS
PERSISTED READBACK PASS
Elapsed: 4.06 s
Maximum resident set size: 482,128 KiB
Exit status: 0
```

The full process-level timing includes imports and FastAPI `TestClient` setup.
It verified creation and persisted readback for the ensemble, Shadow Trial, and
Missing Piece records.

### Staged API timing

A separate temporary-store probe repeated the complete API sequence three times
through `TestClient`: readiness, ensemble POST, Shadow Trial POST, Missing Piece
POST, and three persisted GETs. Responses were checked for HTTP 200 and exact
JSON equality on readback.

| Iteration | Ready ms | Ensemble POST ms | Shadow POST ms | Missing Piece POST ms | Three GETs ms | Full sequence ms |
|---:|---:|---:|---:|---:|---:|---:|
| 1 (cold store) | 3.481 | 28.811 | 37.533 | 31.809 | 20.678 | 122.313 |
| 2 | 1.792 | 31.314 | 17.213 | 8.491 | 18.561 | 77.371 |
| 3 | 1.850 | 30.327 | 16.956 | 9.616 | 19.697 | 78.446 |

The staged Missing Piece POST measured 31.809 ms on the cold SQLite path and
8.491/9.616 ms on warm persisted replays. The staged results are local in-process
measurements and do not represent network, reverse proxy, browser, or external
database latency.

The staged probe was bounded to the deterministic Missing Piece implementation;
no language model or VISTA checkpoint was loaded.

## Frontend build

Command:

```text
(cd web && /usr/bin/time -v ./node_modules/.bin/next build)
```

Result:

```text
Compiled successfully in 12.5s
Finished TypeScript in 10.2s
Generating static pages: 7/7
Exit status: 0
Elapsed: 25.90 s
User: 127.15 s; system: 11.61 s; CPU: 535%
Maximum resident set size: 2,654,096 KiB
```

All listed application routes were generated or compiled successfully. The
build's peak RSS is material for constrained deployment hosts; it does not imply
equivalent runtime memory use.

## Resource and model observations

- No model load was attempted or needed for any benchmark.
- Host GPU utilization was 0% at the post-run snapshot, with 1 MiB used per GPU.
- The API E2E process peaked at approximately 471 MiB RSS.
- The Shadow Trial process peaked at approximately 253 MiB RSS at 1,000 pairs.
- The Next build peaked at approximately 2.53 GiB RSS.
- The host reported 6.2 GiB of 8.0 GiB swap in use; concurrent builds or model
  loading could therefore materially change latency or cause memory pressure.

## Limitations and release impact

This campaign does not establish:

- throughput or tail latency under concurrent clients;
- long-running soak behavior, rate limiting, or upload pressure;
- browser/WebGL rendering cost or accessibility runtime performance;
- reverse-proxy, TLS, public-network, or remote-database latency;
- PostgreSQL/Valkey performance or backup/restore performance;
- live language/VISTA model latency or GPU inference capacity;
- production capacity from one host-local synthetic run.

**Final result:** bounded local synthetic performance is verified for the
requested paths. The overall M10.5 release gate remains **OPEN** until
concurrency, deployment, browser, external persistence, and live-model
benchmarks are separately closed.
