# Tool Authority Matrix (Certification Wave A4)

Rule: assistant tools must read **canonical domain data**, never LLM inference.

Registry: `get_tool_registry()` → Wave 2 tools + Wave 3 `register_physician_tools`.

| Tool | Category | Safety | Canonical authority | Never |
|------|----------|--------|---------------------|-------|
| `get_cardiac_findings` | PHYSIOLOGY | T0 | `get_case` → `derive_findings(case.state, simulation_result)` (`tools/cardiac_findings.py`) | LLM |
| `get_ensemble` | UNCERTAINTY | T0 | `ensemble_store.get` — same record as `GET /api/v1/twin/ensemble/{id}` | Resample |
| `get_ensemble_distributions` | UNCERTAINTY | T0 | Slice of persisted ensemble | LLM |
| `get_ensemble_assumptions` | UNCERTAINTY | T0 | `EnsembleProvenance.assumptions` on persisted record | LLM |
| `get_raw_provenance_ledger` | EVIDENCE | T0 | `CaseRecord.state.source_map` | Frontend binding table |
| `get_findings_by_region` | PHYSIOLOGY | T0 | Filter on `get_cardiac_findings` output | New inference |
| `get_pv_loop` | PHYSIOLOGY | T0 | `CaseRecord.simulation_result` PV fields from `/operate` | Scenario rescale |
| `get_ensemble_summary` | UNCERTAINTY | T0 | Composes three registry tools above | LLM |

## Not yet in registry (GLOBAL_ARCHITECTURE categories)

Shadow Trial, Missing Piece, scenario create/run, timeline, compare pair —
available via **REST** (`api.py`) but not wrapped as assistant tools. CopilotKit
**actions** in `copilot.py` invoke pipeline directly — parallel authority path.

## LLM role (System 2)

`model_client.chat_completion` — explanation only; numeric claims validated
against tool payload (empty if no tool ran).
