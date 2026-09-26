# BeatIT

[![GitHub](https://img.shields.io/badge/GitHub-chetas1208%2FBeatIT-181717?logo=github)](https://github.com/chetas1208/BeatIT)

**BeatIT helps cardiologists explain and explore bounded recovery scenarios using
patient data and deterministic cardiovascular modeling—without allowing an LLM
to invent clinical calculations.** It connects supplied cardiac evidence to a
reproducible baseline, inspectable scenario assumptions, and a visual comparison.
Every displayed value should show where it came from and whether it was measured,
extracted, derived, inferred, prior-filled, or simulated.

> **Educational simulation only.** DualBeat is **not a medical device**. It does not diagnose, prescribe, triage, or recommend treatment. Every output is a simulated, educational estimate.

---

## Why this matters

Recovery planning after a cardiac event is difficult to personalize and explain
because patient evidence, physiological models, uncertainty, and care-team
reasoning remain disconnected. During a supervised follow-up conversation,
clinicians need to show what is known, what is assumed, and how a bounded
hypothetical change affects the model without presenting it as a predicted
patient outcome. Two failure modes dominate:

1. **Static calculators** give you one formula in isolation. They can't relate EF to afterload, localize a regional change to a coronary territory, or project a recovery trajectory.
2. **Black-box medical LLMs** can invent numerical results, hide assumptions, and
   drift into unsupported clinical language.

BeatIT is built around the conviction that **a simulation is only trustworthy
when every value is traceable, its math is reproducible, and its limits are
explicit.** It is a clinician-supervised education and exploration instrument,
not a clinical prediction system.

---

## How it's different — in depth

### 1. Provenance on every single value
Extracted values cite the **source file, extraction method, and a confidence score**. Derived values cite the **exact formula**. Anything filled from population data is explicitly labeled a **`default_model_prior`**. You can audit the entire state field-by-field. No other "AI cardiac" tool hands you a fully sourced state object.

### 2. LLMs never do the math
Core numeric outputs (SV, EF, CO, MAP, RR, QTc, BSA) come from **pure, tested deterministic functions** — never from a language model. LLMs are used only where they're appropriate: reading documents, classifying intent, and writing prose. Baseline results are reproducible; M5 plausible-twin mode samples explicit input distributions with a recorded seed and then runs deterministic physiology. This distinction is central to the audit trail.

### 3. Anatomically-localized, code-tagged findings (for radiologists & cardiologists)
DualBeat doesn't stop at scalars. A deterministic **findings layer** localizes the simulated state to anatomy using the standard **AHA 17-segment left-ventricle model** and **coronary artery territories (LAD / RCA / LCx)**, and renders them as **numbered callouts on the 3D twin** with a matching clinical readout: region, a brief observation, the driving metric, and **reference codes**. Reduced EF → global LV; a regional wall change + scar fraction → the right segments and territory; widened QRS / prolonged QTc → conduction and repolarization observations. Every finding is framed as an **educational simulation observation with reference terminology — never a diagnosis** — so it is legible to a clinician without crossing the safety line.

### 4. An observable processing pipeline
The staged pipeline keeps intake, extraction, validation, deterministic modeling,
explanation, and evaluation inspectable. Its architecture supports the product;
it is not the product claim.

### 5. A model you can run bounded scenarios on
Beyond a static snapshot, BeatIT produces bounded simulated trajectories,
deterministic causal scenarios, and plausible-twin ensembles with explicit input
uncertainty. These are hypothetical model outputs, not forecasts of an
individual patient's outcome.

### 6. Degrades, never bluffs
Missing data is filled from conservative population priors **and flagged**, with elevated uncertainty — never silently guessed. On valid input, no agent hard-fails: the pipeline degrades with explained warnings (covered by an adversarial no-fail test). The only blocking paths are intentional safety gates, and each states its reason.

### 7. Safe by construction
Diagnostic / treatment / emergency language is blocked at **both** the request (intake) and the model-output boundary. Every API response carries a mandatory disclaimer. The product is honest about being a simulation.

---

## Who it's for

- **Primary:** cardiologists preparing for or conducting supervised recovery and
  follow-up conversations.
- **Secondary:** cardiac rehabilitation educators, trainees, and researchers
  exploring bounded cardiovascular simulations.

It is **not** for diagnosis, treatment selection, emergency triage, autonomous
clinical decision-making, or validated outcome prediction.

## What it produces

- A sourced `CardiacTwinState` (deterministic SV, EF, CO, MAP, QTc).
- A beating **3D digital twin** with severity-coded, anatomically-anchored finding callouts (AHA 17-segment + coronary territory + reference codes) and an honest "no findings / no CT provided" state.
- A simulated cardiac cycle with a pressure–volume loop.
- 2–4 bounded recovery trajectories with uncertainty bands.
- A seeded plausible-twin ensemble with rejected-sample accounting and output percentiles when uncertainty mode is enabled.
- A full 8-agent orchestration trace + structured eval scores, every warning explained.

---

## Quick start

Frontend is a Next.js + CopilotKit app under `web/`; backend is FastAPI under `python/hearttwin`. Run them as two processes:

```bash
cp .env.example .env        # add your API keys (never commit .env)

# 1. Backend (FastAPI) on :8000
python -m uvicorn python.hearttwin.api:app --reload --port 8000

# 2. Frontend (Next.js) on :3000
cd web && pnpm install --ignore-workspace && pnpm dev   # http://localhost:3000
```

Point the frontend at the backend with `NEXT_PUBLIC_API_BASE` (copy `web/.env.example` to `web/.env.local`; defaults to `http://localhost:8000/api/v1`). The CopilotKit chat route proxies to the backend's `/copilotkit` AG-UI endpoint.

Without any API keys the app still runs: LLM-backed steps fall back to deterministic behavior, and Weave / Redis / OpenAI / VISTA-3D all degrade safely when unconfigured.

## API endpoints

```
GET  /api/v1/health                          health check
POST /api/v1/cases                           create a case
POST /api/v1/cases/{id}/files                upload PDF/image/CSV
POST /api/v1/cases/{id}/extract              stages 1-3: intake + extraction + validation
POST /api/v1/cases/{id}/operate              stages 4-5-7: state builder + EP + hemodynamics + evaluator
                                             (returns visualization.cardiac_findings)
POST /api/v1/cases/{id}/simulate-recovery    stages 6-7: bounded recovery + evaluator
POST /api/v1/cases/{id}/self-improve         bounded harness improvement rerun
POST /api/v1/twin/ensemble                   seeded plausible-twin ensemble
GET  /api/v1/twin/ensemble/{id}              retrieve a process-local ensemble
GET  /api/v1/twin/ensemble/{id}/distributions retrieve ensemble distributions
GET  /api/v1/cases/{id}                      full case state
GET  /api/v1/cases/{id}/trace                agent trace (snapshot)
GET  /api/v1/cases/{id}/trace/stream         live agent trace (SSE)
```

## Pipeline stages

| Stage | Agent | Endpoint |
|-------|-------|----------|
| 1 | Intake & Safety | `/extract` |
| 2 | Multimodal Extraction | `/extract` |
| 3 | Evidence Validator | `/extract` |
| 4 | Cardiac State Builder | `/operate` |
| 5a | Electrophysiology (parallel) | `/operate` |
| 5b | Hemodynamics Simulation (parallel) | `/operate` |
| 6 | Recovery Orchestration | `/simulate-recovery` |
| 7 | Evaluator & Critic | `/operate` + `/simulate-recovery` |

## Deterministic formulas

All numeric outputs come from pure Python in `python/hearttwin/tools/`. LLMs never perform math.

```
SV  = EDV - ESV
EF  = (SV / EDV) × 100
CO  = (HR × SV) / 1000
MAP = DBP + (SBP - DBP) / 3
RR  = 60000 / HR
QTc = QT / sqrt(RR [seconds])   [Bazett]
BSA = sqrt(H × W / 3600)         [Mosteller]
```

## Findings & anatomy

The findings layer (`python/hearttwin/tools/cardiac_findings.py`) maps the simulated state onto the **AHA 17-segment model** and **coronary territories**, attaching a 3D anchor, severity, observation, and reference codes. It reports `imaging_source` honestly (`none` / `image_extraction` / `vista3d_segmentation`). VISTA-3D segmentation is **optional** and, in its current contract, returns segmentation label IDs + a job handle (not a CT-derived mesh); the 3D twin is an anatomically-faithful stylized model driven by the real state, not a rendered scan.

## Environment variables

See `.env.example`. Highlights: `OPENAI_API_KEY` (+ per-agent `OPENAI_MODEL_*`), `WANDB_*` for Weave tracing, `UPSTASH_REDIS_REST_*` for case memory, `VISTA3D_*` for optional segmentation, and `NEXT_PUBLIC_API_BASE` for the frontend.

## Tests

```bash
pnpm test:py          # Python backend tests (incl. adversarial no-fail + findings)
pnpm build            # build the Next.js frontend (web/)
pnpm verify:all       # env + repo + vercel checks, tests, and build
```

## Deploy (Vercel)

Two pieces: the **frontend** as a Vercel project with **Root Directory = `web`** (framework: Next.js; set `NEXT_PUBLIC_API_BASE` to the backend URL), and the **backend** as a Python serverless function from the repo root (`vercel.json` routes `/api/:path*` → `api/index.py`).

## Safety boundary

DualBeat is an educational simulation. It does **not** diagnose, recommend medication or treatment, or provide emergency guidance. It blocks diagnostic/treatment language at the intake and output boundaries, labels every output `SIMULATION ONLY`, flags every value filled from priors, and frames all anatomic findings as educational observations with reference terminology — never a clinical diagnosis. Use it for education, research, and exploring cardiac physiology — not for clinical decisions.

---

## Built at the Abridge Hackathon

**DualBeat CareGuard** — an additive, feature-flagged (`CAREGUARD_ENABLED` /
`NEXT_PUBLIC_CAREGUARD_ENABLED`), clinician-facing multimorbidity medication-safety and
evidence-review module. It does not diagnose, dose, prescribe, or place orders; every
surface reads *"Clinical decision support draft. Clinician and pharmacist review
required."* With the flags off, DualBeat behaves exactly as before.

New CareGuard functions created during this event:

- **FHIR R4 ingestion** with per-fact JSON-pointer provenance (`careguard/fhir/`)
- **Multimorbidity reconstruction** — FHIR conditions + report-mention NLP with
  negation/temporality/experiencer (`careguard/reports/`, `medications/morbidity_reconciler.py`)
- **Local-first guideline retrieval** with freshness + abstention (`careguard/evidence/`)
- **RxNorm medication normalization** + ingredient decomposition + duplicate detection
  (`medications/medication_reconciler.py`, `rxnorm_client.py`)
- **FDA/DailyMed/openFDA evidence retrieval** + **Orange Book / RxClass / DDInter /
  SIDER / DrugCentral** federation with tiers and a DrugBank license gate
  (`medications/`)
- **Cross-organ contraindication matrix** (`careguard/risk/`)
- **Deterministic conflict engine** (drug–drug/disease/organ/allergy/duplication/monitoring)
- **Evidence-bounded alternative engine** (generic / same-class / cross-class, each
  re-checked; never "safe/best") (`medications/alternative_engine.py`)
- **Anthropic CareGuard agents** with structured output, Fable refusal handling +
  fallback, and a deidentification boundary (`careguard/anthropic/`)
- **Candidate care-plan comparison** + **clinician decision workflow** (`/careguard`)
- **CDS Hooks** cards (patient-view / order-select / order-sign — cards only)
- **CareGuard evals, safety critic, and an audit trail**

See `docs/careguard/` (architecture, clinical-safety-boundary, medication-source-matrix,
anthropic-integration, demo-script, and more). CareGuard reuses DualBeat's existing,
tested simulation through a read-only adapter — it reimplements no DualBeat formula and
mutates no DualBeat state. DualBeat itself predates this event; only the CareGuard
functions listed above were built here.

```bash
pnpm test:careguard            # CareGuard + medication-safety test suite
pnpm verify:careguard          # isolation, env, forbidden-phrase, secret/PHI, source policy
pnpm verify:medication-sources # source tiers, DrugBank license, no-Kaggle-as-authority
```
