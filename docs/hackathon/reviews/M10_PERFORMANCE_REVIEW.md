# M10 Performance and Resource Review

**Contribution:** A26 — bounded local performance/resource audit  
**Review date:** 2026-09-26  
**Scope:** synthetic demo seed, deterministic system-check, representative API
routes, and the frontend production build  
**Production-code changes:** none  
**Model policy:** no large or optional model was loaded

## Result

**PASS for bounded local smoke performance; OPEN for production capacity.**

The deterministic local seed and system-check are fast and repeatable on this
host. The frontend build completes successfully, but the cold build reaches
approximately 2.45 GiB peak RSS. The API probe reaches approximately 471 MiB
peak RSS when importing and exercising the full FastAPI application. These are
useful local sizing observations, not deployment SLOs, concurrency capacity, or
browser-runtime measurements.

## Environment and method

All commands ran from the current worktree on 2026-09-26:

| Item | Observed value |
|---|---|
| Host | Linux 6.8.0-139-generic, x86_64 |
| CPU/RAM | 20 CPUs; 125 GiB RAM; 104 GiB available at probe start |
| Swap | 8.0 GiB configured, 7.7 GiB used at probe start |
| Python/Node/pnpm | Python 3.13.12 / Node v22.22.2 / pnpm 11.23.0 |
| Build mode | Next.js 16.2.7 with Turbopack; 10 page-data workers |
| Optional providers | Seed output reported OpenAI, Weave, Redis, and VISTA disabled |

Each workload was bounded and local. `/usr/bin/time` supplied process wall time,
CPU time, and maximum resident set size (RSS). API timings used five measured
requests per route after one warmup request through FastAPI `TestClient`; this
does not include TCP, reverse proxy, TLS, or browser overhead.

## Measurements

### Synthetic demo seed

Command:

```text
for run in 1 2 3; do
  /usr/bin/time -f "elapsed=%e user=%U sys=%S maxrss_kb=%M exit=%x" \
    ./scripts/seed-demo.sh
done
```

All three runs returned exit `0`, printed `RESULT: OK`, and reported the same
deterministic smoke values (`validated_fields=6`, `EF=58.3`, `CO=5.04`,
`has_pv_loop=True`, `scenarios=4`, `overall_score=0.9`). The measured resource
values were:

| Run | Wall | User | System | Max RSS |
|---:|---:|---:|---:|---:|
| 1 | 0.43 s | 0.37 s | 0.05 s | 47,244 KiB |
| 2 | 0.41 s | 0.36 s | 0.04 s | 47,720 KiB |
| 3 | 0.46 s | 0.39 s | 0.06 s | 47,384 KiB |
| **range** | **0.41–0.46 s** | **0.36–0.39 s** | **0.04–0.06 s** | **46.1–46.6 MiB** |

The script regenerated `data/demo/state.json`; this is the intended synthetic
demo artifact and contains no patient data.

### API route timing

The bounded probe warmed and then measured five successful `200` responses for
each route in one `TestClient` process:

| Route | Min | Median | P95/max for 5 samples |
|---|---:|---:|---:|
| `/api/health/live` | 0.56 ms | 0.57 ms | 0.75 ms |
| `/api/health/ready` | 0.62 ms | 0.67 ms | 0.71 ms |
| `/api/v1/system-status` | 0.76 ms | 0.76 ms | 0.83 ms |
| `/api/v1/models/status` | 0.71 ms | 0.73 ms | 0.97 ms |
| `/api/v1/system-check` | 27.66 ms | 28.64 ms | 50.07 ms |

The complete API probe took 4.80 seconds including application startup and all
requests, and its maximum RSS was 481,920 KiB (approximately 470.6 MiB). The
system-check timing demonstrates a responsive deterministic local path, but it
does not establish a route deadline or protect against concurrent requests,
provider stalls, upload buffering, Redis stalls, or long-lived trace growth.

### Frontend production build

Command, run from `web/`:

```text
/usr/bin/time -f "elapsed=%e user=%U sys=%S maxrss_kb=%M exit=%x" \
  ./node_modules/.bin/next build
```

Result:

| Result | Wall | User | System | Max RSS |
|---|---:|---:|---:|---:|
| exit `0`; optimized build, TypeScript, page data, and static generation passed | 24.39 s | 123.45 s | 10.42 s | 2,565,524 KiB (~2.45 GiB) |

The build reported successful compilation in 11.8 seconds, TypeScript in 9.5
seconds, and static generation of 7 pages in 951 ms. This is a cold-build
observation on the current host; it is not a request-time or client-download
measurement. The build also displayed CopilotKit's anonymous telemetry notice;
no optional model inference was started.

## Interpretation and release impact

### Verified

- The local synthetic seed completes in under half a second across three runs
  with a peak below 48 MiB RSS.
- The deterministic system-check returned `200` five out of five times, with a
  28.64 ms median in this process.
- Liveness, readiness, system status, and model status routes were all `200`
  across five samples each.
- The frontend production build completed successfully.

### Still open

- No concurrent-load, soak, rate-limit, upload, slow-client, reverse-proxy, or
  browser performance test was run. Existing reliability reviews identify
  missing global route limits, end-to-end deadlines, upload buffering limits,
  and trace-retention bounds.
- The API RSS includes full application import and test-client overhead; it is
  not a measured Uvicorn worker baseline or a container memory limit.
- The frontend build RSS is high enough to require deployment-build capacity
  planning. Vercel/build-container behavior was not tested.
- Swap was already heavily used at probe start, so host-wide memory pressure may
  influence measurements. No swap was observed for the seed command itself.
- Optional language, VISTA, Weave, Redis, and remote deployment performance
  were intentionally not tested; no claim is made for those paths.

## Gate decision

**Performance gate: PASS for the bounded synthetic local smoke path; OPEN for
public release capacity and resilience.** Before a public RC, repeat the API
probe through the deployed reverse proxy, verify the frontend build in its
actual build environment, and add bounded concurrent/soak and oversized-upload
tests with explicit memory, latency, and failure budgets.

