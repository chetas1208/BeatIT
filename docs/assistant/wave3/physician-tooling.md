# Wave 3 — Physician Tooling Extension (Agent 12)

Extends the ONE canonical tool registry (`python/hearttwin/assistant/tool_registry.py`,
Wave 2, untouched by this file) with new, real, backend-verified tools in a
new file, `python/hearttwin/assistant/physician_tools.py`. No new physiology,
uncertainty, or evidence logic was added — every handler wraps a function or
field that already exists and is already load-bearing elsewhere in the
backend, matching the discipline `tool_registry.py`'s own docstring sets.

## Part A — re-investigation of Wave 2's skipped candidates

Wave 2 declined 5 candidates from `PHYSICIAN_WORKFLOWS.md` as frontend-only
TypeScript with no Python entry point: component report, evidence-by-component,
provenance, timeline, scenario/PV-loop. Each was re-checked from scratch
against `python/hearttwin/` (not just Wave 2's conclusion):

| Candidate | Re-investigation result |
|---|---|
| **Component report** (`buildComponentReport`) | **Confirmed still frontend-only.** `web/lib/heart/patient/adapter.ts` / `web/lib/heart/report/reportModel.ts`. No `grep` hit for `component_report`/`buildComponentReport`/equivalent logic anywhere under `python/hearttwin/`. No new tool built for this. |
| **Evidence-by-component** (`getComponentEvidence`) | **Partially real — see `get_raw_provenance_ledger` below.** The *component → field binding* (`physiologyBindings`) that turns a flat ledger into "evidence for this component" is confirmed still frontend-only (`web/lib/heart/evidence/index.ts:99-105`), and this file does **not** fake that binding. But the *raw ledger itself* (`CardiacTwinState.source_map`) is real, populated, backend-native data, already consumed by `orchestrator.py:585` and `tools/scoring.py` (lines 161, 182, 240, 297) — not orphaned. That's exposed honestly, unbound, as `get_raw_provenance_ledger`. |
| **Provenance** (`lineageForSnapshot`/`lineageForEvent`) | **Confirmed still frontend-only** as a snapshot/event lineage lookup (`web/lib/twin/provenance/index.ts`) — there is no backend snapshot/event store to look this up against (see Timeline row). The underlying raw provenance data it would need (`source_map`) is now exposed via `get_raw_provenance_ledger`, but the snapshot/event lineage *lookup* itself was not rebuilt — that would require inventing a Python-side timeline store, out of scope. |
| **Timeline** (`web/lib/twin/snapshots`, `Timeline.tsx`) | **Confirmed still frontend-only, no new backend path found.** Re-grepped `python/hearttwin/` for `timeline`/`snapshot_history`/`TwinSnapshot`: zero hits outside this campaign's own docs. `CaseRecord` (`schemas.py:352-364`) is a single mutable record — no `/cases/{id}/history` route exists in `api.py`. No tool built for this. |
| **Scenario / PV-loop experiments** | **Split finding.** The *scenario* half (`run_scenario_experiment`, causal propagation, counterfactual rescaling) is confirmed still 100% frontend-only (`web/lib/twin/scenario/{parameters,propagation,fork}.ts`) — no Python entry point, no tool built. But the *baseline* PV loop (not the scenario-rescaled one) turned out to be real, computed, and cached backend data that Wave 2 never wrapped: `generate_pressure_volume_loop()` (`tools/hemodynamics.py:190`) runs inside every `/operate` call via `run_hemodynamics_agent` (`agents/hemodynamics_agent.py:672-686`) and is cached on `CaseRecord.simulation_result["pv_loop"]`. `GLOBAL_ARCHITECTURE.md`'s own registry sketch even names `get_pv_loop` under PHYSIOLOGY — this was a real gap, not aspirational. Exposed as `get_pv_loop` below, explicitly labeled baseline-only. |

Also re-read `tools/cardiac_findings.py`'s `derive_findings()` in full
(lines 129-272) per the brief's specific instruction. Finding: Wave 2's
`get_cardiac_findings` already returns the *entire* dict `derive_findings()`
produces (`findings`, `imaging_source`, `segment_model`, `disclaimer`,
`model`) — nothing was held back or unused. There is no hidden
evidence/component-shaped sub-structure Wave 2 missed. What *is* useful,
without adding logic, is a narrower **view**: each finding dict already
carries `region` and `territory` fields (e.g. `"Anteroseptal wall"`, `"LAD"`)
that can be filtered on directly — that became `get_findings_by_region`
below. This is explicitly not a "component report" or a
`physiologyBindings`-style mapping; it is a substring filter over fields the
real data already has.

**Honest summary of Part A:** two of five original gaps (component report,
timeline) remain confirmed frontend-only with no backend path — no tool was
forced for them. One (snapshot/event provenance lineage) remains gapped for
the same reason (no timeline store), though its raw ingredient is now
exposed. Two turned up real, previously-unwrapped backend data
(`source_map`, baseline `pv_loop`) plus one legitimate narrower slice of
already-fully-exposed data (`findings` by region) — these became the four
new tools below.

## New tools registered

All four are **T0** (read-only, auto-execute) — nothing computational was
discovered or invented this wave, matching Wave 2's own T0-only scope.

| Tool | Safety | Category | Wraps (file:line, verified) |
|---|---|---|---|
| `get_raw_provenance_ledger` | T0 | EVIDENCE | `CardiacTwinState.source_map: list[SourceMapEntry]` — field declared `schemas.py:260`, entry shape `schemas.py:232-240`. Fetched via the same `get_case`/`CaseRecord` pattern Wave 2 used (`tools/storage.py:85-97`, `schemas.py:352-364`). |
| `get_findings_by_region` | T0 | PHYSIOLOGY | Calls the real, registered `get_cardiac_findings` tool (`tool_registry.py:220-238`, itself wrapping `derive_findings()` — `tools/cardiac_findings.py:129-272`) via `ToolRegistry.execute()`, then filters the returned `findings` list by the `region`/`territory` fields each finding already carries (`cardiac_findings.py:151-264`, e.g. `region="Anteroseptal wall"`, `territory="LAD"`). |
| `get_pv_loop` | T0 | PHYSIOLOGY | `generate_pressure_volume_loop()` (`tools/hemodynamics.py:190`), cached onto `CaseRecord.simulation_result["pv_loop"]` by `run_hemodynamics_agent` (`agents/hemodynamics_agent.py:672-686`) during `run_operation_pipeline` (`orchestrator.py:134-198`, cache write at line 198). Confirmed populated by **both** real `/operate` entry points — `api.py:1068` and `copilot.py:258` (`operate()`) — since both call the same `run_operation_pipeline`, so reading the cache (rather than recomputing, unlike `get_cardiac_findings`) is safe. |
| `get_ensemble_summary` | T0 | UNCERTAINTY | Composite: calls the three real, already-registered Wave 2 tools — `get_ensemble`, `get_ensemble_distributions`, `get_ensemble_assumptions` (`tool_registry.py:240-296`) — through `ToolRegistry.execute()` and combines their outputs verbatim. No ensemble logic reimplemented. |

### Signatures

- `get_raw_provenance_ledger(case_id: str)`
- `get_findings_by_region(case_id: str, region: str)`
- `get_pv_loop(case_id: str)`
- `get_ensemble_summary(ensemble_id: str)`

### Honesty notes baked into each tool's output

- `get_raw_provenance_ledger` returns `scope: "raw"` and a `note` field
  explicitly stating this is the flat, field-keyed ledger, **not** a
  per-anatomical-component evidence view — the component binding
  (`physiologyBindings`) remains frontend-only and is not faked.
- `get_pv_loop` returns a `note` field explicitly stating this is the
  **baseline** loop only, and that scenario/counterfactual rescaling
  (`web/lib/twin/scenario/pv.ts`) is frontend-only with no backend entry
  point.
- `get_findings_by_region`'s description explicitly says it is a filter over
  `get_cardiac_findings`'s existing output, not a new evidence model.

## Why registration is not automatic at import time

`register_physician_tools(registry: Optional[ToolRegistry] = None) -> ToolRegistry`
(default target: the real `get_tool_registry()` singleton) is exported from
`physician_tools.py` but is **never called at module import time**. Reason,
found empirically while building this wave: Wave 2's
`test_tool_registry.py::test_default_registry_has_expected_tools_and_categories`
asserts an *exact* set of 4 tool names on the shared process-wide singleton.
pytest imports every test module during collection, so if importing
`physician_tools.py` had a side effect of mutating that singleton, the two
test files colliding in one pytest session would break Wave 2's committed
test — confirmed by running both files together before landing on this
design (`python -m pytest python/hearttwin/tests/test_physician_tools.py
python/hearttwin/tests/test_tool_registry.py -q` → all pass with the
explicit-registration design; the auto-register-at-import alternative was
not shipped because it fails this exact check).

Explicit, caller-invoked registration avoids that entirely and mirrors Wave
2's own pattern of building the registry lazily inside `get_tool_registry()`
rather than eagerly. Wiring `register_physician_tools(get_tool_registry())`
into the live request-handling pipeline is left to whichever wave actually
mounts the assistant (`WAVE_2_HANDOFF.md`'s Next-Wave Dependency #2/#3) —
consistent with Wave 2 itself leaving `router.py` built but unmounted.

`python/hearttwin/tests/test_physician_tools.py` reflects the same
isolation concern: it resets `tool_registry._REGISTRY` to `None` before and
after every test in the file (an autouse fixture), so that exercising the
two composite tools against the real singleton (which they call internally
by design, to compose through the one true registry rather than a side
channel) never leaves that singleton polluted for any other test file. Full
suite run to confirm: `python -m pytest python/hearttwin/tests/ -q` →
**943 passed, 1 skipped**, no regressions.

## Files added (no existing file modified)

- `python/hearttwin/assistant/physician_tools.py`
- `python/hearttwin/tests/test_physician_tools.py`
- `docs/assistant/wave3/physician-tooling.md` (this file)

`python/hearttwin/assistant/tool_registry.py`, `schemas.py`, and every other
existing file were read but not edited. `git status` was checked before and
after this work — the only pre-existing working-tree changes are Codex's
concurrent, unrelated edits (`api.py`, `ensemble.py`,
`web/components/twin/scenario/ScenarioPanel.tsx`, `web/lib/api.ts`, docs,
etc.) and this campaign's own hackathon docs; `shadow_trial_*.py` was not
read or imported by anything in this file.

## Test run

```
$ python -m pytest python/hearttwin/tests/test_physician_tools.py -v
...
14 passed, 12 warnings in 0.16s

$ python -m pytest python/hearttwin/tests/ -q
...
943 passed, 1 skipped, 461 warnings in 11.26s
```
