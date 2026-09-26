# Physician Workflow Audit — What Actually Exists (Wave 1, Agent 4)

Pure discovery. Every claim below is cited `file:line`. Where a campaign-brief
concept has no backing code, it is marked **GAP / aspirational** rather than
guessed at.

## Summary

BeatIT already has a surprisingly rich **frontend** provenance/evidence/causal
model under `web/lib/twin/` and `web/lib/heart/` — evidence kinds, a causal
graph, a scenario-fork engine (baseline vs. counterfactual), an ensemble
uncertainty model with `assumptions[]`, a component report builder, and a
timeline/ECG event model. These are wired into the real UI (`AppShell.tsx` →
`HeartScene.tsx`), not orphaned code. What does **not** exist is a backend
**tool registry** that exposes any of this to an LLM/copilot: the CopilotKit
surface (`python/hearttwin/copilot.py`) only has 5 actions (`create_case`,
`extract`, `operate`, `simulate_recovery`, `answer_case_question`), and
`answer_case_question` only echoes flat summary metrics — it cannot cite
evidence, segments, assumptions, or scenario deltas. The named concepts
"Shadow Trial," "Split Heart," and "Missing Piece" are **planned milestones
that were never implemented** (a plan doc exists, no completion doc, no code).
CareGuard is a separate, real, medication-safety module (not cardiac-twin
physician workflow) with its own evidence/provenance system.

## Existing Physician-Relevant Concepts

| Concept | Exists? | Implementing file(s) | Notes |
|---|---|---|---|
| Shadow Trials | **No — aspirational** | Plan only: `docs/hackathon/M6_AGENT_PLAN.md:1,7` | Titled "Shadow Trial Engine"; describes "a paired, deterministic Shadow Trial over one persisted M5.5 baseline." No `M6_COMPLETION.md` exists (`docs/hackathon/` listing has M1–M5.5 + M6_AGENT_PLAN only, no M6/M7/M8 completion). No `shadow_trial`/`ShadowTrial` identifier anywhere in `python/` or `web/`. |
| Split Heart | **No — aspirational** | Plan only: `docs/hackathon/MILESTONES.md:9`, `docs/hackathon/M6_AGENT_PLAN.md:12` | Named as M7. `docs/hackathon/ARCHITECTURE.md:12,17` explicitly lists it under "Future" work as of M1. No `split_heart`/`SplitHeart` identifier in code. (Note: an unrelated component named `ScenarioFork` at `web/components/twin/timeline/ScenarioFork.tsx` and `web/lib/twin/scenario/fork.ts` does baseline-vs-counterfactual forking — see "Causal experiments" row — but is not named/scoped as "Split Heart" anywhere.) |
| Missing Piece | **No — aspirational** | Plan only: `docs/hackathon/MILESTONES.md:10`, `docs/hackathon/M6_AGENT_PLAN.md:12` | Named as M8, "next-best evidence." No `missing_piece` identifier in code. |
| Probabilistic twins | **Partially — real, different name** | `python/hearttwin/ensemble.py`; API: `python/hearttwin/api.py:156-200` (`/api/v1/twin/ensemble*`) | The README/API call this "plausible-twin ensemble," not "probabilistic twin." Real, tested (`EnsembleRequest`/`EnsembleResponse`/`EnsembleSample`/`EnsembleMetricDistribution` in `ensemble.py:31-257`), with seeded sampling, rejected-sample accounting (`ensemble.py:213,246`), and percentile distributions. Frontend consumes it in `web/lib/twin/ensemble/*` (`adapter.ts`, `runner.ts`, `inspectorModel.ts`, `pvEnvelope.ts`) and renders via `web/components/twin/ensemble/PlausibleTwinsPanel.tsx` / `EnsembleUncertaintyInspector.tsx`, wired into `web/components/heart/HeartScene.tsx:61` (`plausibleTwinVisualization`). |
| Causal experiments | **Yes — real, wired to UI** | `web/lib/twin/scenario/*.ts` (causal graph: `causal.ts`; fork: `fork.ts`; parameter changes: `parameters.ts`; effect propagation: `propagation.ts`; PV-loop rescaling: `pv.ts`; text report: `report.ts`) | `web/lib/twin/scenario/causal.ts:1-7` states it deliberately: "describes relationships and propagation evidence only... Numeric propagation remains an explicit consumer of these types." Rendered live via `web/components/twin/scenario/ScenarioPanel.tsx`, imported in `web/components/layout/AppShell.tsx:31,160` as "Causal physiology explorer." `docs/hackathon/M4_CAUSAL_GRAPH.md` / `M4_SCENARIO_MODEL.md` document its build (M4), which post-dates the earlier "future work" note in `ARCHITECTURE.md:17` (M1) — that note is stale. |
| PV loops | **Yes, both deterministic-baseline and scenario-rescaled** | Backend: `python/hearttwin/tools/hemodynamics.py`, `python/hearttwin/agents/hemodynamics_agent.py` | Frontend scenario overlay: `web/lib/twin/scenario/pv.ts:1-36` rescales the baseline PV loop into a "scenario" loop from EDV/ESV deltas. Rendered in `web/components/charts/SimulationCharts.tsx`. |
| ECG state | **Yes, partial (frontend model + backend agent)** | `python/hearttwin/agents/electrophysiology_agent.py`; `python/hearttwin/tools/ecg_features.py`; frontend event model: `web/lib/twin/ecg/index.ts:1-35` | Frontend `ECGSignalKind = "measured" \| "extracted" \| "simulated" \| "missing"` (`web/lib/twin/ecg/index.ts:3`) is a richer provenance taxonomy for ECG points specifically than the backend's generic `ValueSource` enum (see Evidence model section). |
| Component reports | **Yes — real, wired to UI** | `web/lib/heart/report/reportModel.ts:1-2` (delegates to) `web/lib/heart/patient/adapter.ts` (`buildComponentReport`) | Rendered by `web/components/heart/report/ComponentReportPanel.tsx`, invoked from `web/components/heart/HeartScene.tsx:50,52`. No backend equivalent — this is a pure frontend derivation over `CardiacTwinState` + `source_map`, not an API endpoint. |
| Longitudinal / timeline snapshots | **Yes — real, wired to UI** | `web/lib/twin/snapshots/index.ts`, `web/lib/twin/time/contracts.ts`, `web/components/twin/timeline/Timeline.tsx` | `TwinTimeline` imported into `web/components/heart/HeartScene.tsx:55`. Backed by `TwinSnapshot`/`TwinEvent`/`TwinTimestamp` contracts in `web/lib/twin/time/contracts.ts:28-42`. This is a frontend-only event/snapshot store (no backend longitudinal persistence endpoint was found — see Gaps). |
| Ensembles | **Yes** (same as "probabilistic twins" row) | — | — |

## Existing Evidence/Provenance Model

**Backend (`python/hearttwin/schemas.py`)** — a single, simple provenance
enum used on nearly every numeric field:

- `ValueSource` enum, 4 members only: `FILE_EXTRACTION`, `USER_INPUT`,
  `DEFAULT_MODEL_PRIOR`, `DERIVED` (`python/hearttwin/schemas.py:72-76`).
- `MeasuredValue` wraps every clinical number with `value`, `unit`, `source`,
  `confidence`, `source_file_id`, `method`, `evidence` (`schemas.py:84-91`).
- `SourceMapEntry` is a flat, field-keyed provenance ledger attached to the
  whole state: `field`, `value`, `unit`, `source`, `source_file_id`,
  `confidence`, `method`, `evidence` (`schemas.py:232-240`), collected as
  `CardiacTwinState.source_map: list[SourceMapEntry]` (`schemas.py:260`).
- There is **no `simulated` value in the backend `ValueSource` enum** — only
  4 kinds. "Simulated" provenance (e.g. recovery/scenario outputs) is not
  represented in the canonical state's source map today.

**Frontend (`web/lib/heart/evidence/index.ts`)** — a superset taxonomy that
the backend doesn't emit but the frontend already models:

- `EvidenceKind` (imported from `@/lib/heart/contracts`) has **6** members
  vs. the backend's 4: `directly_observed`, `extracted`, `derived`,
  `default_model_prior`, `simulated`, `unavailable`
  (`web/lib/heart/evidence/index.ts:11-42`).
- `evidenceKind()` maps backend `ValueSource` strings onto this richer set
  (`index.ts:44-66`) — `"simulated"`/`"simulation"` is handled in the mapper
  but the backend never actually sends those source strings today, so that
  branch is presently dead on live data.
- `sourceMapEntryToEvidence()` converts a backend `SourceMapEntry` into a UI
  `ComponentEvidence` (`index.ts:86-97`); `getComponentEvidence()` filters a
  component's evidence by matching `source_map[].field` against the
  component's `physiologyBindings` (`index.ts:99-105`).
- A parallel, independent provenance model exists for the timeline/scenario
  layer: `TwinProvenance` (`source`, `sourceId`, `method`, `confidence`,
  `evidenceIds`, `note`) in `web/lib/twin/time/contracts.ts:28-35`, consumed
  by `web/lib/twin/provenance/index.ts:3-25` (`lineageForSnapshot`,
  `lineageForEvent`) and rendered by
  `web/components/twin/provenance/ProvenanceBadge.tsx`. Its `TwinEventSource`
  union (`clinical_record`, `imaging`, `ecg`, `wearable`, `synthetic_replay`,
  `user_annotation`, `derived_model` — labels in
  `web/lib/twin/ensemble/inspectorModel.ts:20-30`) is a **third**,
  independent provenance vocabulary alongside the backend `ValueSource` and
  the `EvidenceKind` enum. **These three provenance vocabularies are not
  unified** — a fourth, separate one exists in
  `web/lib/twin/scenario/causal.ts:31-46` (`CausalSourceKind`: `measurement`,
  `clinical_evidence`, `deterministic_formula`, `assumption`,
  `derived_state`, `documentation`).
- Ensemble-specific provenance: `EnsembleProvenance` carries
  `origin_snapshot_id`, `origin_provenance`, `evidence_ids`, `seed`,
  `physiology_version`, `distribution_config_version`, `prior_version`, and
  an explicit **`assumptions: list[str]`** field
  (`python/hearttwin/ensemble.py:233,435`), e.g. *"Input proxies are sampled
  independently because no validated joint correlation model is available."*
  This is the only place in the codebase where "assumptions" are captured as
  first-class, enumerable, machine-readable data.
- CareGuard has its own, separate provenance system for medications/FHIR
  (`python/hearttwin/careguard/schemas.py`, `careguard/fhir/*.py`), out of
  scope for the cardiac-twin physiology questions below but real and
  per-fact-cited (README.md:164).

## Existing Safety Guardrails

`python/hearttwin/agents/intake_agent.py` is the real, load-bearing
implementation (not a stub):

- **Rule-based classifier first, LLM classifier only refines** — never
  overrides a blocked rule decision: `_classify_intent_with_rules()`
  (`intake_agent.py:284-392`) checks regex patterns for emergency/triage
  (`intake_agent.py:289-308`), medication/treatment
  (`intake_agent.py:310-331`), and diagnosis (`intake_agent.py:333-350`)
  requests, each returning `safety_level="blocked"` with a `blocked_reason`.
  `_merge_decisions()` (`intake_agent.py:395-413`) guarantees a rule-blocked
  decision is never softened by the model.
- The OpenAI-based intent classifier (`_classify_intent_with_openai`,
  `intake_agent.py:247-281`) is instructed to "not answer the request" and
  only returns one of a fixed enum of `_INTENT_CLASSES`
  (`intake_agent.py:32-42`), rejecting any unrecognized label.
  `provider_available()` gates it off entirely when no LLM key is set — the
  regex rules alone still enforce blocking, so the safety gate stays intact
  with or without an LLM configured.
- PII redaction happens before anything is logged to trace:
  `_redact_pii_for_intake()` (`intake_agent.py:452-480`) regexes out SSNs,
  emails, phones, DOB, street address, and patient-name-labeled text.
- Output-side check: `python/hearttwin/copilot.py:418`
  (`_check_output_safety`) is called on every `answer_case_question` and
  `_deterministic_case_answer` response (`copilot.py:129,451+`) before it
  reaches the user — a second, output-boundary gate distinct from intake.
- Every response carries `CORE_SAFETY_PHRASE`/`DISCLAIMER` from
  `python/hearttwin/safety.py` (imported at `intake_agent.py:21`,
  `copilot.py`), and `_with_disclaimer()` (`copilot.py:96-98`) stamps it onto
  every copilot action's payload.

## Physician Question → Tool Mapping

| Question | Existing tool/endpoint | Notes |
|---|---|---|
| "What evidence supports the reduced LV function?" | **Partial** — `getComponentEvidence()` (`web/lib/heart/evidence/index.ts:99-105`) via `ComponentReportPanel` | Frontend-only; filters `state.source_map` by the LV component's `physiologyBindings`. No backend/copilot tool surfaces this — `answer_case_question` (`copilot.py:451`) doesn't call it. |
| "How has EF changed longitudinally?" | **GAP** | `web/lib/twin/snapshots/index.ts` + `Timeline.tsx` model an event/snapshot timeline in the browser, but there is no backend endpoint that persists or serves a longitudinal series of `CardiacTwinState`s across visits — each case-run is a single snapshot (`api.py` has no `/cases/{id}/history` route). |
| "Which AHA segments are involved?" | **Yes** — `python/hearttwin/tools/cardiac_findings.py` (`WALL_MAP`, lines ~41+), surfaced via `/api/v1/cases/{id}/operate` → `visualization.cardiac_findings` (README.md:90) | Deterministic wall→territory→AHA-segment mapping (`cardiac_findings.py:1-19` docstring cites Cerqueira et al. 2002). Not yet exposed as a standalone copilot action. |
| "Compare baseline and counterfactual LV mechanics." | **Yes, frontend-only** — `web/lib/twin/scenario/types.ts` (`ScenarioResult` with `.baseline`/`.scenario`), `report.ts:scenarioReport()` | `scenarioReport()` (`web/lib/twin/scenario/report.ts:4-17`) already produces exactly this text comparison. Not exposed via any backend/copilot endpoint — purely client-side (`ScenarioPanel.tsx`). |
| "Why is the Shadow Trial range wide?" | **GAP** | Shadow Trial doesn't exist (see table above). Closest real analog — ensemble percentile width — has no "why is it wide" explainer; `EnsembleProvenance.assumptions` (`ensemble.py:233`) lists *why* independence was assumed, but nothing ranks which assumption drives width. |
| "Which assumptions dominate this result?" | **GAP (partial data exists)** | `EnsembleProvenance.assumptions: list[str]` (`ensemble.py:233`) and `CausalSource.kind: "assumption"` (`web/lib/twin/scenario/causal.ts:36`) are the only structured "assumption" records in the codebase. Neither is ranked/scored by dominance/sensitivity — no sensitivity-analysis code was found anywhere in `python/hearttwin/`. |
| "What evidence would most constrain this simulation?" | **GAP** | No code computes value-of-information / constraint-ranking. `SourceMapEntry.confidence` (`schemas.py:238`) exists per-field but nothing aggregates "which missing/low-confidence field most widens the ensemble." |
| "Show the provenance for this value." | **Yes** — `ProvenanceBadge.tsx` + `lineageForSnapshot`/`lineageForEvent` (`web/lib/twin/provenance/index.ts:9-24`); also `sourceMapEntryToEvidence()` (`web/lib/heart/evidence/index.ts:86-97`) | Real and wired into `HeartScene.tsx:57`. Not exposed to the LLM/copilot — it's a UI-only lookup over already-fetched state. |
| "What part of this report is observed versus derived?" | **Yes** — `EVIDENCE_KIND_METADATA` + `groupEvidenceByKind()` (`web/lib/heart/evidence/index.ts:11-42,107-115`) | Groups a component's evidence list by kind (`directly_observed`/`extracted`/`derived`/`default_model_prior`/`simulated`/`unavailable`). Frontend-only. |
| "Run the afterload experiment." | **Yes** — `web/lib/twin/scenario/parameters.ts` (parameter changes) + `propagation.ts` (causal propagation) + `ScenarioPanel.tsx` UI | Real, deterministic, bounded (`ScenarioParameterChange` type, `web/lib/twin/scenario/types.ts:33-39`). Only reachable by clicking in the UI today — **not** a copilot action (`copilot.py`'s `build_actions()` at line 538 has no scenario/experiment action). |
| "Compare the resulting PV loop." | **Yes** — `web/lib/twin/scenario/pv.ts:scenarioPvLoop()` (lines 23-36) | Rescales the baseline PV loop by scenario EDV/ESV deltas; rendered in `SimulationCharts.tsx`. Frontend-only, not a copilot action. |

## Gaps Summary

- **No unified provenance vocabulary.** Four independent, non-interoperable
  taxonomies exist: backend `ValueSource` (4 kinds, `schemas.py:72-76`),
  frontend `EvidenceKind` (6 kinds, `evidence/index.ts:11-42`), timeline
  `TwinEventSource` (7 kinds, `ensemble/inspectorModel.ts:20-30`), and causal
  `CausalSourceKind` (6 kinds, `scenario/causal.ts:31-46`). Any Wave 3 tool
  registry must pick or reconcile one, or explicitly map between them.
- **No backend copilot/tool access to any of the rich frontend
  physiology-explanation surfaces.** `python/hearttwin/copilot.py` exposes
  only `create_case`/`extract`/`operate`/`simulate_recovery`/
  `answer_case_question` (`copilot.py:538-654`). Evidence lookup, component
  reports, AHA-segment findings, scenario/causal experiments, PV-loop
  comparison, and ensemble uncertainty all exist as real code but are
  reachable only by clicking in the React UI — none is an `Action` an LLM
  can call.
- **`answer_case_question` is shallow.** Its LLM path is unaudited in this
  pass, but its deterministic fallback (`copilot.py:101-140`) only echoes
  5 flat summary metrics — it cannot cite `source_map`, AHA segments, or
  scenario deltas.
- **No longitudinal/history persistence on the backend.** The timeline
  concept (`web/lib/twin/snapshots`, `Timeline.tsx`) is real but
  browser-local; there is no `/cases/{id}/history` or multi-visit store in
  `api.py`.
- **No sensitivity/dominance analysis anywhere.** "Which assumptions
  dominate" and "what evidence would most constrain this" have no
  implementing code — only unranked, textual `assumptions: list[str]` on the
  ensemble provenance object.
- **Shadow Trial / Split Heart / Missing Piece are 100% unbuilt.** Plans
  exist (`docs/hackathon/M6_AGENT_PLAN.md`, `MILESTONES.md`); zero code,
  zero completion docs. Wave 3 should not assume any backing logic survives
  from these names — the closest real primitives are the ensemble engine
  (`python/hearttwin/ensemble.py`) and the scenario/causal engine
  (`web/lib/twin/scenario/*`), which could be *extended toward* those ideas
  but currently implement neither.
- **CareGuard's evidence/provenance system is separate and should not be
  conflated** with the cardiac-twin physiology evidence model — it answers
  medication-safety questions (`/cases/{id}/evidence` in
  `careguard/routes_case.py:30-32` returns guideline citations, not cardiac
  `source_map` provenance).

## Canonical Tool Candidates

Based only on what has real, working logic behind it today (all currently
frontend-only unless noted):

- `get_component_report(case_id, component_id)` — backed by
  `buildComponentReport` (`web/lib/heart/patient/adapter.ts`, entry point
  `web/lib/heart/report/reportModel.ts:2`).
- `get_component_evidence(case_id, component_id)` — backed by
  `getComponentEvidence()` / `groupEvidenceByKind()`
  (`web/lib/heart/evidence/index.ts:99-115`).
- `get_provenance(case_id, value_or_snapshot_id)` — backed by
  `lineageForSnapshot`/`lineageForEvent` (`web/lib/twin/provenance/index.ts`).
- `get_cardiac_findings(case_id)` — backed by the existing
  `/api/v1/cases/{id}/operate` → `visualization.cardiac_findings` payload
  (already a real endpoint field, README.md:90; just needs a copilot
  `Action` wrapper) from `python/hearttwin/tools/cardiac_findings.py`.
- `run_scenario_experiment(case_id, parameter, delta)` /
  `compare_scenario(case_id, scenario_id)` — backed by
  `web/lib/twin/scenario/{parameters,propagation,fork}.ts` and
  `scenarioReport()` (`report.ts`).
- `get_scenario_pv_loop(case_id, scenario_id)` — backed by
  `scenarioPvLoop()` (`web/lib/twin/scenario/pv.ts:23-36`).
- `get_ensemble(case_id)` / `get_ensemble_distributions(case_id)` — already
  **real backend endpoints**: `/api/v1/twin/ensemble/{id}` and
  `/api/v1/twin/ensemble/{id}/distributions`
  (`python/hearttwin/api.py:171-200`); only needs a copilot `Action` wrapper.
- `get_ensemble_assumptions(case_id)` — backed by
  `EnsembleProvenance.assumptions` (`python/hearttwin/ensemble.py:233,435`).
- `get_timeline(case_id)` — would need new backend persistence; frontend
  model exists (`web/lib/twin/snapshots/index.ts`,
  `web/lib/twin/time/contracts.ts`) but has no server-side store today.

Not proposed as tools yet (no real backing found): `get_shadow_trial`,
`compare_split_heart`, `get_missing_piece`, `get_dominant_assumptions`
(needs new sensitivity-analysis logic), `get_constraining_evidence` (needs
new value-of-information logic).
