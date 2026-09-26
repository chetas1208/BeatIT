# M10 War Room

Status: **ACTIVE — release hardening**  
Started: 2026-09-26

## Commander's boundary

The five-space M9 product is frozen:

```text
TWIN → EXPERIMENT → COMPARE → EVIDENCE → REPORT
```

M10 may repair release blockers, deployment, persistence, health, fallbacks,
security, performance, accessibility, reproducibility, documentation, and the
demo runbook. It may not add a new scientific method, formula, product space,
agent, or major visualization.

## Priority queue

1. P0: crashes, blank heart, lost state, fake numerical output, unsafe labels,
   broken core demo path.
2. P1: restart/persistence/deployment/model fallback, avoidable red tests,
   security exposure, and broken deterministic demo reset.
3. P2: release polish after P0/P1 closure.
4. WONTFIX: documented inherited limitations that do not undermine the demo
   claim.

## Evidence ledger

The following evidence index is the current handoff. No failure is hidden; an
environment blocker is recorded as a blocker rather than converted into a
passing claim.

| Evidence | Result |
|---|---|
| Python final suite | `1233 passed, 5 skipped, 6 xfailed` |
| Direct frontend gates | TypeScript, scoped ESLint, product runtime (3), Next build: pass |
| API contracts | liveness/readiness/system-status TestClient probes: pass |
| Demo | preflight, seed, reset/idempotence and fixture hash review: pass locally |
| Self-host launcher | alternate-port `up` → HTTP preflight → frontend HTTP → `down`: pass |
| Host/deployment audits | reviewed; public proxy/TLS and external persistence remain open |
| Browser/AT/WebGL | blocked by missing Chromium audio dependency and Firefox executable |
| Security/privacy | synthetic/demo-only; no patient-data release |
| Regression | nine inherited frontend runtime failures remain documented |
| Agent ledger | 22 distinct reviewed contributions in `M10_AGENT_PLAN.md` |
| Final decision | **INCOMPLETE — DO NOT SHIP** |

Supporting records: [`M10_COMPLETION.md`](M10_COMPLETION.md),
[`M10_TEST_MATRIX.md`](M10_TEST_MATRIX.md),
[`M10_BLOCKERS.md`](M10_BLOCKERS.md), and the `M10_*` reviews under
`docs/hackathon/reviews/`, `docs/deploy/`, and `docs/models/`.
