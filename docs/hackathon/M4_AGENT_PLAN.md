# BeatIT M4 Agent Plan

Status: integration complete enough for audit; acceptance remains incomplete.

The lead agent owns integration, shared contracts, final review, and the
deterministic physiology boundary. Each implementation agent has a disjoint
write set. Agents must not change observed timeline semantics, canonical
cardiac formulas, or provider transport without an explicit integration
amendment.

| ID | Scope | Owned files / directory | Dependencies | Deliverable | Status |
|---|---|---|---|---|---|
| 01 | Formula audit | `docs/hackathon/M4_PHYSIOLOGY_AUDIT.md` | Existing Python formulas | Formula/unit/assumption map | complete |
| 02 | Causal graph contract | `web/lib/twin/scenario/causal.ts` | Formula audit concepts | Typed nodes/edges/paths | complete |
| 03 | Units and parameter validation | `web/lib/twin/scenario/parameters.ts` | Causal contract | Bounded manipulable parameters | complete |
| 04 | Scenario state model | `web/lib/twin/scenario/types.ts` | Snapshot contracts | Observed/scenario types | complete |
| 05 | Snapshot fork engine | `web/lib/twin/scenario/fork.ts` | Scenario state model | Immutable fork with origin | complete |
| 06 | Deterministic propagation | `web/lib/twin/scenario/propagation.ts` | Parameters, causal graph | Explicit causal recomputation | lead-integrated |
| 07 | Causal trace | `web/lib/twin/scenario/trace.ts` | Propagation | Numeric deltas and paths | complete |
| 08 | Deterministic report | `web/lib/twin/scenario/report.ts` | Trace/types | Scenario report generator | complete |
| 09 | Undo/redo | `web/lib/twin/scenario/history.ts` | Fork/propagation | Isolated history stack | complete |
| 10 | Local persistence | `web/lib/twin/scenario/persistence.ts` | Scenario types | Safe save/load envelope | complete |
| 11 | PV projection | `web/lib/twin/scenario/pv.ts` | Propagation output | Baseline/scenario PV data | lead-integrated |
| 12 | Heart binding | `web/lib/twin/scenario/heart.ts` | Scenario types | Non-quantitative visual binding | lead-integrated |
| 13 | Component deltas | `web/lib/twin/scenario/components.ts` | State/types | Baseline/scenario component view | lead-integrated |
| 14 | Causal graph UI | `web/components/twin/scenario/CausalGraph.tsx` | Causal contract | Inspectable graph paths | lead-integrated |
| 15 | Parameter controls UI | `web/components/twin/scenario/ParameterControls.tsx` | Parameters | Baseline/current/delta controls | lead-integrated |
| 16 | Scenario panel UI | `web/components/twin/scenario/ScenarioPanel.tsx` | Core scenario API | Experiment surface | lead-integrated |
| 17 | Scenario inspector UI | `web/components/twin/scenario/ScenarioInspector.tsx` | Component deltas | Explicit hypothetical labeling | complete |
| 18 | Timeline fork UI | `web/components/twin/timeline/ScenarioFork.tsx` | Snapshot timeline | Snapshot -> Experiment action | complete |
| 19 | Scenario integration hook | `web/lib/twin/scenario/useScenario.tsx` | Core scenario API | UI orchestration hook | lead-integrated |
| 20 | M4 scenario tests | `web/lib/twin/scenario/__tests__` | Core scenario API | Fork/propagation/history tests | complete |
| 21 | Hardware audit | `docs/models/HARDWARE_AUDIT.md` | Host inspection | Evidence-backed hardware report | lead-integrated |
| 22 | Model inventory | `docs/models/LOCAL_MODEL_INVENTORY.md` | Host inspection | Local artifact inventory | lead-integrated |
| 23 | Model registry | `python/hearttwin/models/` | Model inventory | Lazy capability registry | lead-integrated |
| 24 | Imaging boundary | `python/hearttwin/imaging/` | Existing VISTA client | Provider-neutral segmentation seam | lead-integrated |
| 25 | M4 documentation | `docs/hackathon/M4_CAUSAL_GRAPH.md`, `M4_SCENARIO_MODEL.md`, `M4_PARAMETER_RANGES.md` | Contracts | Architecture and safety docs | lead-integrated |
| 26 | Adversarial review | `docs/hackathon/M4_QA.md` | Integrated implementation | Scientific/architecture findings | complete; follow-up required |

## Integration rules

1. Observed snapshots are immutable and never receive scenario values.
2. Scenario computation is deterministic and accepts explicit input state.
3. Models may explain an already-computed trace but never calculate physiology.
4. No agent may download weights; model acquisition is lead-controlled after
   hardware and inventory evidence.
5. The lead agent reviews every change, runs regression tests, and records
   unresolved findings in `M4_COMPLETION.md`.

## Actual dispatch ledger

The collaboration runtime did not allow 20 concurrent threads. The following
agents were actually dispatched (IDs are runtime evidence, not simulated
documentation). Completed meaningful contributions are marked; stopped/no-op
threads are retained so the limitation is auditable.

| Agent ID | Scope | Result |
|---|---|---|
| `01a0db12-3da1-7602-9f67-0c341ebbfa3c` | M4 formula audit | completed |
| `01a0db12-3e4e-7a10-afc7-fefd326c48b5` | M4 architecture audit | completed |
| `01a0db44-7c8f-7621-a9b7-8bb7a8f579d6` | formula audit | completed audit |
| `01a0db44-7d73-7f02-b8c4-f62decbbe284` | causal contracts | completed |
| `01a0db44-7e37-78d0-b690-5e2648cca1e7` | scenario types | completed |
| `01a0db44-7f09-7b20-9696-6d431b915242` | immutable fork | completed |
| `01a0db47-ec00-78b2-a893-72d9a071baed` | parameter constraints | completed |
| `01a0db47-ec4d-7a91-aeec-e1ff8e6ceb60` | persistence | completed |
| `01a0db47-ec92-79f0-9ded-453ecf0f4647` | formula read-only audit | completed |
| `01a0db4e-47a0-7a80-8c8b-194d60e5092f` | hook | stopped after lead takeover |
| `01a0db4e-47ec-7c21-9c2d-53108ac0166f` | UI contracts | stopped before edits |
| `01a0db4e-482e-7601-bbc8-874773676110` | inspector | shutdown during lead takeover |
| `01a0db52-e47e-7c31-b46b-3ed6a2a6f9f0` | timeline fork | completed |
| `01a0db52-e4c4-7bd0-a26b-437b2136197b` | history tests | completed |
| `01a0db52-e50c-7d21-a0cf-01f4cf3485f8` | architecture review | completed |
| `01a0db55-2b84-74d1-9a0f-aa41b08e035f` | duplicate registry test | no-op stopped |
| `01a0db55-65d5-7d00-bb42-32436f15de13` | architecture review document | completed |
| `01a0db60-4cd6-7de0-9678-ffe7b2a368d9` | model runtime review | completed |
| `01a0db60-4d18-7580-b2f1-045bc548f125` | UX review | completed |
| `01a0db60-4d5f-73a1-b38c-73805a906609` | test plan review | dispatched; runtime did not complete before cutoff |
| `01a0db64-ab39-7971-a44c-5119f7ac2796` | medical integrity review | dispatched; runtime did not complete before cutoff |

**Actual dispatched total: 24. Meaningful completed contributions: 16 plus
lead integration. The mandatory 20-meaningful-agent gate is therefore not
claimed as satisfied.**
