# CareGuard — Vercel Deployment

Root deployment is unchanged: `vercel.json` rewrites `/api/*` → `api/index.py`, which
re-exports the FastAPI app. CareGuard mounts into that same app when
`CAREGUARD_ENABLED=true`. No second Vercel project, no second long-running server, no
`localhost:8000` requirement in production.

Staged orchestration keeps each request bounded (one stage per `/runs/{id}/next`) so a
serverless function never runs the whole pipeline. Large datasets are **not** bundled:
Orange Book / DDInter / SIDER / DrugCentral load from configured `*_DATA_PATH` snapshots
in object storage or a managed store; RxNorm/RxClass/DailyMed/openFDA are runtime APIs
with cached snapshots. VISTA runs only as an external tunneled service — never inside a
Vercel function.

Set on Vercel: `CAREGUARD_ENABLED`, `NEXT_PUBLIC_CAREGUARD_ENABLED`, `ANTHROPIC_API_KEY`,
`REDIS_URL`, and any source paths. All CareGuard vars default to the safe/off posture.
