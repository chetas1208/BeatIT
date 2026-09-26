## BeatIT Web

Next.js App Router frontend workspace for the BeatIT cardiac twin demo.
The root Vercel project should use `web` as its root directory.

### Commands

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

```bash
pnpm build
pnpm lint
```

### Running locally against the BeatIT backend

This Next.js app is the CopilotKit frontend; the FastAPI app under
`python/hearttwin` is the backend. The CopilotKit server route uses the same
provider-neutral model runtime configuration and proxies to the backend's
`/copilotkit` AG-UI actions, while REST + the live SSE trace stream go straight
to `/api/v1/*`.

Run two processes from the repo root:

```powershell
# 1. Backend (FastAPI) on :8000  — Windows
py -m uvicorn python.hearttwin.api:app --reload --port 8000
#    POSIX: python -m uvicorn python.hearttwin.api:app --reload --port 8000

# 2. Frontend (Next.js) on :3000
cd web; pnpm install --ignore-workspace; pnpm dev
```

Then open http://localhost:3000.

### Environment

Copy `web/.env.example` to `web/.env.local` (gitignored). For local dev it
points `NEXT_PUBLIC_API_BASE` at `http://localhost:8000/api/v1`. Configure the
server-only `MODEL_*` variables in the private environment. If using the
optional first-party adapter, set `INTELLIGENCE_PROVIDER=openai`,
`OPENAI_ENABLED=true`, `OPENAI_API_KEY`, and `OPENAI_MODEL`. CopilotKit runtime
credentials stay server-side in the App Router route.

### Safety Boundary

BeatIT is an educational simulation. It is not for diagnosis or
treatment decisions and does not provide medical advice. Keep that disclaimer
visible on every shipped screen.

### Pinned Demo Dependencies

The sponsor/demo packages are pinned from `docs/INTEGRATION_NOTES.md`:

- CopilotKit React/runtime packages: `1.59.5`
- `@react-three/fiber`: `9.6.1`
- `@react-three/drei`: `10.7.7`
- `react-plotly.js`: `2.6.0`

Later workers should keep API contracts under `web/lib`, `web/hooks`, and
`web/types` aligned with `python/hearttwin/schemas.py`.
