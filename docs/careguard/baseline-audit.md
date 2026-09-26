# CareGuard — Baseline Audit

**Date:** 2026-07-18
**Purpose:** Required first deliverable (spec §2). Establishes the immutable DualBeat
baseline *before* any CareGuard code is written, so every later change can be measured
against a known-good starting point and rolled back cleanly.

> CareGuard is an **additive** module. Nothing in this audit is modified by CareGuard
> except the small, explicitly-listed integration seams in §6.

---

## 1. Actual repository stack (vs. the spec's assumptions)

The spec was written against a **Nuxt/Vue** app. This repository is **Next.js/React**.
The preservation contract (spec §1) forbids "rewrite the existing frontend into a
different application," so introducing Nuxt would *violate* the contract. CareGuard is
therefore adapted to the real stack. Reconciliation table:

| Spec assumes (Nuxt) | This repo actually uses (Next.js) | CareGuard uses |
|---|---|---|
| `nuxt.config.ts` | `web/next.config.ts` | Next config (untouched) |
| `app/pages/careguard/*.vue` | `web/app/**/page.tsx` (App Router) | `web/app/careguard/**/page.tsx` |
| `app/components/careguard/*.vue` | `web/components/**/*.tsx` | `web/components/careguard/*.tsx` |
| `app/stores/careguard.ts` (Pinia) | `web/lib/store.ts` (Zustand) | `web/lib/careguardStore.ts` (Zustand) |
| `app/composables/useCareGuardApi.ts` | `web/lib/api.ts` (plain fns/hooks) | `web/lib/careguardApi.ts` + `web/hooks/useCareGuardRun.ts` |
| `NUXT_PUBLIC_CAREGUARD_ENABLED` | `NEXT_PUBLIC_*` convention | `NEXT_PUBLIC_CAREGUARD_ENABLED` |
| `pnpm typecheck` / `pnpm check` | not defined | `tsc --noEmit` via `pnpm -C web exec tsc` |
| `pnpm test:api` / `pnpm test:e2e` | not defined | `pnpm test:careguard` (pytest) added additively |

**Backend matches the spec as-is:** Python at `python/hearttwin/`, FastAPI app at
`python/hearttwin/api.py`, Vercel entry `api/index.py`, root `vercel.json`. CareGuard's
Python namespace (`python/hearttwin/careguard/`) is used verbatim.

---

## 2. Current architecture (immutable)

```
python/hearttwin/
  api.py               FastAPI app, all routes under /api/v1  (+ CopilotKit at /copilotkit)
  orchestrator.py      8-agent deterministic pipeline (extract → operate → recovery)
  safety.py            request+output safety gates, disclaimer, PII redaction
  schemas.py           Pydantic contracts (CardiacTwinState, CaseRecord, AgentResponse…)
  copilot.py           CopilotKit SDK actions
  agents/              8 DualBeat agents (intake, extraction, validator, state_builder,
                       electrophysiology, hemodynamics, recovery, evaluator)
  tools/               deterministic math + infra:
                         cardiac_state, hemodynamics, ecg_features, recovery_sim,
                         cardiac_findings, scoring, ct_volumetry
                         redis_client, storage, weave_trace, model_config, env_config,
                         vista3d_client, pdf_extract, image_extract, nifti_write, case_memory
  research/ecg_dx/     sklearn ECG classifier (model.joblib)
  tests/               ~40 pytest modules
web/                   Next.js 16 App Router, React 19, Tailwind 4, Plotly, three.js
api/index.py           Vercel serverless entry → re-exports FastAPI app
vercel.json            root deploy: rewrites /api/* → api/index.py
```

**Design law (must be preserved):** LLMs never compute numbers. All numeric outputs
come from pure, tested Python. CareGuard inherits this law — Anthropic writes prose and
structures evidence; all cardiac numbers still come from DualBeat's existing functions
via a read-only adapter.

---

## 3. DualBeat functions that remain untouched

- **Agents (8):** `intake_agent`, `extraction_agent`, `validator_agent`,
  `state_builder_agent`, `electrophysiology_agent`, `hemodynamics_agent`,
  `recovery_agent`, `evaluator_agent`. Agent IDs unchanged.
- **Orchestrator:** `run_extraction_pipeline`, `run_operation_pipeline`,
  `run_recovery_pipeline`, `run_self_improvement_pipeline`.
- **Deterministic formulas:** everything in `tools/cardiac_state.py`,
  `tools/hemodynamics.py`, `tools/ecg_features.py`, `tools/recovery_sim.py`,
  `tools/cardiac_findings.py`, `tools/scoring.py`, `tools/ct_volumetry.py`.
- **Infra:** `redis_client`, `storage`, `weave_trace`, `model_config`, `env_config`,
  `vista3d_client`. Reused read-only; existing Redis keys and response shapes unchanged.
- **Existing routes (14):** snapshot in §5. None removed, renamed, or reshaped.
- **Frontend:** every existing page/component under `web/` unchanged.
- **Safety:** `safety.py` messages unchanged. CareGuard adds its own boundary layer.
- **OpenAI / Weave / CopilotKit integrations:** unchanged. CareGuard adds Anthropic
  *alongside* them; it does not remove or reroute any existing provider.

---

## 4. Baseline test results (measured, not claimed)

Command: `python -m pytest python/hearttwin/tests -q` (Python 3.14.6, venv).

```
10 failed, 563 passed, 1 skipped, 394 warnings in 5.29s
```

**The 10 failures are pre-existing and environment-driven — not caused by CareGuard
(CareGuard did not exist when this ran).** Every one fails identically with:

```
RuntimeError: There is no current event loop in thread 'MainThread'.
```

Root cause: these tests call `asyncio.get_event_loop().run_until_complete(...)`, an API
**removed in Python 3.14**. The repo declares `requires-python = ">=3.12"`; the dev
machine has 3.14.6. Affected files: `test_evaluator_agent.py` (9), `test_validator_agent.py` (1).

**Preservation metric:** CareGuard's guarantee is *no new failures against this exact
baseline* — the count must stay `10 failed / 563 passed` (or better) after integration.
CareGuard's own tests use the modern async pattern (`asyncio.run` / `pytest.mark.asyncio`)
so they pass on 3.14.

Fixing the 10 pre-existing failures is **out of scope** (would edit existing test files
the spec marks immutable); they are documented here as a known baseline condition.

---

## 5. Route snapshot (immutable — regression-tested)

```
POST   /api/v1/cases
GET    /api/v1/cases/{case_id}
POST   /api/v1/cases/{case_id}/extract
POST   /api/v1/cases/{case_id}/files
GET    /api/v1/cases/{case_id}/harness
POST   /api/v1/cases/{case_id}/operate
POST   /api/v1/cases/{case_id}/self-improve
POST   /api/v1/cases/{case_id}/simulate-recovery
GET    /api/v1/cases/{case_id}/trace
GET    /api/v1/cases/{case_id}/trace/stream
GET    /api/v1/config
POST   /api/v1/ecg/diagnose
GET    /api/v1/health
GET    /api/v1/system-check
(+ CopilotKit: GET/PUT/POST/DELETE/OPTIONS /copilotkit/{path})
```

A regression test asserts every one of these paths still exists after CareGuard mounts.

---

## 6. Integration seams (the ONLY existing files CareGuard edits)

Each edit is minimal, additive, and flag-guarded. Full list kept current in the final report.

| File | Minimal change | Guard |
|---|---|---|
| `python/hearttwin/api.py` | `include_router(careguard_router)` — one guarded block | only mounts when `CAREGUARD_ENABLED=true` |
| `.env.example` | append CareGuard variables | flags default such that off = baseline |
| `web/components/layout/AppShell.tsx` | one flag-guarded nav link to `/careguard` | hidden unless `NEXT_PUBLIC_CAREGUARD_ENABLED=true` |
| `package.json` | add `test:careguard`, `verify:careguard` scripts | additive only |
| `pyproject.toml` | add `anthropic`, `pyyaml` to deps (additive) | optional at runtime |
| `README.md` | append "Built at the Abridge Hackathon" section | docs only |

**Nothing else existing is modified.** No existing file is renamed or moved.

---

## 7. Feature-flag isolation contract

When `CAREGUARD_ENABLED=false` **and** `NEXT_PUBLIC_CAREGUARD_ENABLED=false`:

- CareGuard router is **not mounted** → zero new API routes exist.
- No CareGuard navigation renders.
- No Anthropic client is constructed → no Anthropic calls.
- No `careguard:*` Redis keys are created.
- Existing DualBeat behavior is byte-for-byte the current baseline.

This is proven by `test_careguard_isolation.py` (flag-off asserts route table == baseline).

---

## 8. Rollback boundaries

CareGuard is fully contained in **new paths**:
`python/hearttwin/careguard/`, `web/app/careguard/`, `web/components/careguard/`,
`web/lib/careguard*.ts`, `fixtures/careguard/`, `docs/careguard/`,
`python/hearttwin/tests/careguard/`.

**To remove CareGuard entirely:** delete those directories and revert the ~6 seam edits
in §6. DualBeat returns to this exact baseline. No data migration, no key rename, no
schema change is required to roll back.
