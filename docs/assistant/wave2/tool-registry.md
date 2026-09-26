# Wave 2 — Canonical Tool Registry (Agent 9)

`python/hearttwin/assistant/tool_registry.py` is the ONE tool registry
required by `docs/assistant/GLOBAL_ARCHITECTURE.md` ("SINGLE TOOL REGISTRY").
It wraps only functionality verified to be real and backend-callable today;
it adds zero new physiology, uncertainty, or evidence logic.

Agent 6's `python/hearttwin/assistant/schemas.py` already existed when this
work started (it defines `ExecutionClass`, `ToolResult`, `ProvenanceRef`,
`CanonicalProvenanceKind`, `ConversationContext`, etc.). `ToolResult` is
reused as-is for every `ToolRegistry.execute()` return value — no second
result contract was created. **No reconciliation is needed**; the only
addition on top of Agent 6's schema is `Tool.execution_class`, populated
from a small per-tool constant (see "Why `execution_class` was added"
below) purely to fill `ToolResult.execution_class`.

## Tools implemented

All four are **T0 (read-only, auto-execute)**. Nothing computational (T1) or
higher was safe to register this wave — the only T1 candidate in
PHYSICIAN_WORKFLOWS.md (`run_scenario_experiment`) has no Python entry point
(see "Deliberately not implemented" below).

| Tool | Safety | Category | Wraps (file:line, verified) | Signature |
|---|---|---|---|---|
| `get_cardiac_findings` | T0 | PHYSIOLOGY | `derive_findings()` — `python/hearttwin/tools/cardiac_findings.py:129-272` | `get_cardiac_findings(case_id: str)` |
| `get_ensemble` | T0 | UNCERTAINTY | Same store lookup as `GET /api/v1/twin/ensemble/{id}` — `python/hearttwin/api.py:171-179`, backed by `SQLiteEnsembleStore.get()` — `python/hearttwin/storage/ensemble_store.py:117-138` | `get_ensemble(ensemble_id: str)` |
| `get_ensemble_distributions` | T0 | UNCERTAINTY | Same lookup + slice as `GET /api/v1/twin/ensemble/{id}/distributions` — `python/hearttwin/api.py:182-195` | `get_ensemble_distributions(ensemble_id: str)` |
| `get_ensemble_assumptions` | T0 | UNCERTAINTY | Slices `EnsembleProvenance.assumptions` — `python/hearttwin/ensemble.py:233` (field), `:435` (populated in `run_ensemble()`) | `get_ensemble_assumptions(ensemble_id: str)` |

### Verification notes (what I actually checked, not just what the doc claimed)

- **`derive_findings`**: read the full function body
  (`cardiac_findings.py:129-272`). Confirmed signature
  `derive_findings(state: Optional[dict], visualization: Optional[dict]) -> dict`
  and confirmed it is genuinely called today from
  `api.py:973` inside `POST /api/v1/cases/{case_id}/operate`. Also checked
  `python/hearttwin/copilot.py` for the same call — **it is not called
  there**, so a case operated only through the CopilotKit `operate` action
  (not the REST route) has no `cardiac_findings` key cached on
  `case.simulation_result`. Rather than trust the cache, the tool handler
  calls `derive_findings()` itself, directly, on `case.state` +
  `case.simulation_result` — the same real function, just invoked
  independently of which code path last ran `/operate`. This is why the
  handler is a few lines longer than "return a cached field."
- **`case_id` resolution**: PHYSICIAN_WORKFLOWS.md's candidate list writes
  `get_component_report(case_id, ...)` etc. throughout, implying case-scoped
  lookup is already a real pattern — confirmed via
  `python/hearttwin/tools/storage.py:85-97` (`get_case(case_id) -> Optional[dict]`,
  Redis-backed when configured, in-memory dict otherwise). This is the one
  genuinely-existing "resolve by id" mechanism in the backend; no invented
  "current case" singleton was used.
- **Ensemble read endpoints**: read `api.py:156-195` in full. Confirmed
  `/api/v1/twin/ensemble/{id}` and `/{id}/distributions` are real, mounted
  routes backed by the module-scope `_ensemble_store = create_ensemble_store()`
  (`api.py:105`). My tool handlers call `create_ensemble_store()` themselves
  (same factory, same `BEATIT_ENSEMBLE_DB_PATH` env var,
  `storage/ensemble_store.py:141-146`) rather than importing api.py's
  private `_ensemble_store` — this is the same persisted SQLite file the
  real API writes to, so an ensemble created via `POST /api/v1/twin/ensemble`
  is genuinely retrievable through this tool, not a parallel store.
- **`get_ensemble_assumptions` signature correction**: PHYSICIAN_WORKFLOWS.md
  writes this candidate as `get_ensemble_assumptions(case_id)`. That's stale
  — `EnsembleRequest`/`EnsembleRequest.state` carries `origin_snapshot_id`,
  not `case_id`, and `EnsembleStore` (`storage/ensemble_store.py`) keys
  exclusively by `ensemble_id` (`_validate_id(ensemble_id)` at
  `ensemble_store.py:44-46`, `save`/`get` signatures at `:88`/`:117`). There
  is no case_id → ensemble_id index anywhere in the backend. Implemented
  with the real key instead: `get_ensemble_assumptions(ensemble_id: str)`.
- Read `ensemble.py:410-462` (`run_ensemble`) in full to confirm the
  `provenance["assumptions"]` list (`:435`) is genuinely populated
  human-readable text (not a stub), e.g. *"Input proxies are sampled
  independently because no validated joint correlation model is available."*
  — asserted verbatim (substring) in `test_get_ensemble_assumptions_returns_real_provenance_text`.

### Why `execution_class` was added to `Tool`

The task brief's minimal `Tool` field list (`name`, `description`,
`safety_level`, `category`, `input_schema`, `handler`) doesn't include it,
but `ToolRegistry.execute()` must return Agent 6's `ToolResult`, which
requires `execution_class: ExecutionClass` on every result
(`assistant/schemas.py:122-128`). Guessing it per-call from the tool name
would be a second, implicit taxonomy; instead each `Tool` carries the one
`ExecutionClass` it always resolves to (`EVIDENCE_RETRIEVAL` for all four —
each is presenting already-computed/persisted evidence, not performing
`DIRECT_STATE_READ` off raw twin state or a new `SIMULATION`). Flagging this
explicitly in case a later wave wants it reconciled differently.

## Deliberately NOT implemented (from PHYSICIAN_WORKFLOWS.md's candidate list)

| Candidate | Why skipped |
|---|---|
| `get_component_report(case_id, component_id)` | Frontend-only TypeScript: `buildComponentReport` in `web/lib/heart/patient/adapter.ts`, entry `web/lib/heart/report/reportModel.ts`. No Python entry point — confirmed no equivalent function exists under `python/hearttwin/`. |
| `get_component_evidence(case_id, component_id)` | Frontend-only: `getComponentEvidence()`/`groupEvidenceByKind()` in `web/lib/heart/evidence/index.ts`. The backend does have a real, raw provenance ledger (`CardiacTwinState.source_map: list[SourceMapEntry]`, `schemas.py:232-260`), but the *component → field binding* (`physiologyBindings`) that turns a flat source_map into "evidence for this component" is itself frontend-only TS. Building a Python-side component/field binding table to fake this tool would be inventing new mapping logic that doesn't exist server-side today — explicitly out of scope per this wave's brief ("do not invent new physiology logic"). |
| `get_provenance(case_id, value_or_snapshot_id)` | Frontend-only: `lineageForSnapshot`/`lineageForEvent` in `web/lib/twin/provenance/index.ts`, over the browser-local `TwinSnapshot`/`TwinEvent` timeline model. No backend snapshot/event store exists to look this up against (see `get_timeline` row below). |
| `run_scenario_experiment(case_id, parameter, delta)` / `compare_scenario(case_id, scenario_id)` | Frontend-only: `web/lib/twin/scenario/{parameters,propagation,fork}.ts` + `report.ts`. This was the only T1 (computational) candidate in the doc; no backend entry point exists to wrap, so no T1 tool was registered this wave. |
| `get_scenario_pv_loop(case_id, scenario_id)` | Frontend-only: `scenarioPvLoop()` in `web/lib/twin/scenario/pv.ts:23-36`. Rescales the baseline PV loop client-side from scenario EDV/ESV deltas that only exist once a scenario has been run in the browser. |
| `get_timeline(case_id)` | No backend persistence at all. `web/lib/twin/snapshots/index.ts` + `web/lib/twin/time/contracts.ts` model a longitudinal timeline, but confirmed (via `api.py`) there is no `/cases/{id}/history` route or any multi-visit store — a case record is a single mutable snapshot (`get_case`/`store_case` overwrite in place). Building this would require designing new backend persistence, not wrapping an existing function. |

Also confirmed still true from Wave 1 and out of scope regardless: Shadow
Trial / Split Heart / Missing Piece have zero backing code
(`get_shadow_trial`, `compare_split_heart`, `get_missing_piece`,
`get_dominant_assumptions`, `get_constraining_evidence` — none registered).
`python/hearttwin/shadow_trial_*.py` was not read for implementation
purposes and not imported anywhere in `tool_registry.py` — confirmed via
`grep` that no such import exists in the new file — since Codex is
concurrently live-editing those files per the Wave 1 handoff note.

## Files added (no existing file modified)

- `python/hearttwin/assistant/tool_registry.py`
- `python/hearttwin/tests/test_tool_registry.py`
- `docs/assistant/wave2/tool-registry.md` (this file)

## Test run

```
python -m pytest python/hearttwin/tests/test_tool_registry.py -v
...
12 passed, 2 warnings in 0.26s
```

Full-suite sanity check (`python -m pytest python/hearttwin/tests/ -q`) was
also run to confirm this new file doesn't collide with anything: 875 passed,
1 skipped, and 6 pre-existing failures confined to
`test_shadow_trial_api.py` / `test_shadow_trial_engine.py` — unrelated to
this change (no file this registry touches is imported by those tests), and
those modules were flagged in this wave's brief as concurrently
being edited by Codex and explicitly out of scope.
