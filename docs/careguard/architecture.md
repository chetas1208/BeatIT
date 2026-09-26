# CareGuard Architecture

CareGuard is an **additive, feature-flagged** module inside the DualBeat
monorepo. It adds a clinician-facing multimorbidity **medication-safety & evidence
review** workflow without changing any existing DualBeat behavior.

## Isolation

- Backend mounts only when `CAREGUARD_ENABLED=true` (one guarded `include_router`
  in `python/hearttwin/api.py`). Flag off → byte-identical baseline (proven by
  `test_careguard_isolation.py` + `verify:careguard`).
- Frontend nav + `/careguard` route appear only when
  `NEXT_PUBLIC_CAREGUARD_ENABLED=true`.
- Anthropic is used **alongside** (never replacing) DualBeat's OpenAI/Weave.
- Redis keys are namespaced under `careguard:*`.

## Backend layout (`python/hearttwin/careguard/`)

```
api.py, api_routes.py        router + exception handlers (mounted when enabled)
feature_flags.py config.py   flags + secret-free config + env validation
constants.py errors.py       stage IDs, safety strings, typed exceptions
security.py audit.py         deidentification/redaction + append-only audit
schemas.py                   core Pydantic contracts
orchestrator.py              Vercel-safe staged run engine (1 stage / call)
agents/                      8 CareGuard agents (deterministic-first)
fhir/                        R4 parser, validator, extractors, provenance
evidence/                    local-first guideline retrieval + freshness + policy
medications/                 Multimorbidity Medication Safety engine (see below)
reports/                     report-mention NLP (negation/temporality/experiencer)
risk/                        cross-organ matrix + signals
simulation/                  read-only DualBeat adapter
memory/                      namespaced Redis store + keys + fallback
cds_hooks/                   discovery + patient-view + order-select + order-sign
```

## The 8 CareGuard agents (separate from DualBeat's 8)

1. **Encounter Intake & Safety** — enable check, intent gate, PHI redaction.
2. **FHIR Patient Context** — normalized `PatientContext`, provenance coverage.
3. **Clinical Problem & Multimorbidity** — cross-organ matrix, evidence domains.
4. **Guideline Evidence** — local-first passages, freshness, abstains when unverifiable.
5. **Medication & Contraindication** — hosts the Multimorbidity Medication Safety engine.
6. **Candidate Care-Plan Composer** — 2–3 evidence-linked options, no dose, no order.
7. **DualBeat Scenario** — bounded physiologic comparison via the read-only adapter.
8. **Evidence, Safety & Clinical Critic** — blocks display on any safety violation.

Every agent is **deterministic-first**: it produces valid structured output with no
Anthropic key. Claude, when configured, only structures evidence and writes prose —
it never computes a number or a clinical fact (DualBeat's "LLMs never do the math").

## Staged orchestration (Vercel-safe)

`POST /runs` creates a run; `POST /runs/{id}/next` executes **exactly one** bounded
stage (Redis lock + idempotency + audit); `GET /runs/{id}` returns status. State is
rebuilt from persisted case + accumulated prior outputs each call, so no single
request runs the whole pipeline (no serverless-timeout risk). Stage order:
`encounter_intake → fhir_context → multimorbidity_analysis → guideline_evidence →
medication_safety → candidate_composition → hearttwin_scenarios → clinical_critic →
clinician_review_ready`.

## Multimorbidity Medication Safety engine (`medications/`)

Evidence federation with source tiers (see `medication-source-matrix.md`), medication
reconciliation (RxNorm identity + ingredient decomposition + duplicate detection),
morbidity reconciliation (FHIR conditions + report-mention NLP), a deterministic
conflict engine (drug–drug/disease/organ/allergy/duplication/monitoring), an
alternative engine (generic / same-class / cross-class, each re-checked against the
full patient context, never "safe/best"), and a safety critic. See
`medication-safety-research.md`.

## Read-only DualBeat bridge

`simulation/hearttwin_adapter.py` deep-copies inputs and calls the existing tested
functions in `python/hearttwin/tools/cardiac_state.py` (SV/EF/CO/MAP) — CareGuard
reimplements no formula and mutates no DualBeat state. It records which functions it
reused and preserves the baseline unchanged.

## Deployment

Root Vercel deployment is unchanged (`api/index.py` → FastAPI app). No second backend,
no large datasets in the function bundle; supplemental data sources load from
configured `*_DATA_PATH` snapshots / object storage. VISTA stays external.
