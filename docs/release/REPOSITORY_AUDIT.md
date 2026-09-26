# M10.5 Repository Audit

Date: 2026-09-26  
Scope: frozen M10 product — verification only, no new capabilities.

## Layout (authoritative paths)

| Area | Location | Role |
|---|---|---|
| Backend API | `python/hearttwin/api.py`, `api/index.py` | FastAPI, health live/ready, twin/ensemble/shadow/missing-piece |
| Deterministic engine | `python/hearttwin/tools/cardiac_state.py`, `hemodynamics.py`, `recovery_sim.py` | Sacred math — not modified in M10.5 |
| Frontend product | `web/app/[mode]/`, `web/components/product/`, `web/lib/product/` | Five modes TWIN→REPORT |
| Persistence | `BEATIT_ENSEMBLE_DB_PATH`, missing-piece SQLite, local `data/` | File/SQLite stores |
| Demo | `fixtures/`, `scripts/seed-demo.sh`, `data/demo/`, `data/manifest.json` | Synthetic canonical demo |
| Deploy | `deploy/beatit`, `deploy/nginx.conf.example`, `docker-compose.prod.yml` | Loopback launcher + proxy template |
| Verification | `scripts/verify-release.sh`, `scripts/verify_api_e2e.py`, `docs/release/*` | Release campaign |

## Duplicate / legacy surfaces (accepted, not removed in M10.5)

- **DualBeat** naming remains in engine modules and older docs; **BeatIT** is product branding.
- **Three-column console** (intake + agent trace) coexists with five-mode product shell — judge demo should use product routes.
- **CareGuard** subtree under `web/components/careguard/` — optional; not on primary demo spine.
- **Assistant / Copilot** campaign — separate from deterministic twin demo; Python tests include assistant isolation.

## Stale-route / localhost risks

- Product API client uses `NEXT_PUBLIC_API_BASE` (not hardcoded production hosts in `web/lib/api.ts`).
- `.env.example` documents localhost defaults for local-dev only.

## Mocks in production paths

- No mock FastAPI responses in `web/lib/api.ts`; errors surface as `ApiRequestError`.
- Optional providers (Weave, Redis, language model) degrade to local fallbacks when unset — not silent success.

## Open TODO/FIXME density

War-room spot-check: no critical `FIXME` in `web/lib/product` or `python/hearttwin/missing_piece`. Residual TODOs live in assistant/campaign docs and non-demo workstreams.

## Verification implication

Executable truth lives in:

```bash
./scripts/validate-env.sh
./scripts/verify-release.sh --deep
```

Documentation records intent; passing commands record integration.
