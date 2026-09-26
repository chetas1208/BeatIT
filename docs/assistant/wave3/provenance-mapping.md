# Wave 3 — Legacy Provenance Vocabulary Mapping (Agent 13)

`python/hearttwin/assistant/provenance_mapping.py` is the mapping layer
`WAVE_2_HANDOFF.md` ("Next-wave dependencies" #1) deferred: translating
BeatIT's legacy, per-subsystem provenance vocabularies into
`assistant.schemas.CanonicalProvenanceKind`, so physician-facing claims can
carry real, inspectable provenance instead of a made-up label.

## What was actually verified as Python-side (vs. frontend-only)

`docs/assistant/PHYSICIAN_WORKFLOWS.md` names 4 vocabularies. Re-verified
against current code (not trusted from the doc), by grepping for each type
name across `python/`:

| Vocabulary | Real Python type? | Evidence |
|---|---|---|
| backend `ValueSource` | **Yes** | `python/hearttwin/schemas.py:72-76`, a real `Enum`, imported and used in `ensemble.py`, `shadow_trial_engine.py`, `agents/electrophysiology_agent.py`, `agents/hemodynamics_agent.py`, `agents/state_builder_agent.py`. |
| frontend `EvidenceKind` | **No — TypeScript only** | `web/lib/heart/contracts`/`web/lib/heart/evidence/index.ts`. `grep -rn "EvidenceKind" python/` returns zero hits outside this doc's own text. |
| timeline `TwinEventSource` | **No — TypeScript only** | `web/lib/twin/ensemble/inspectorModel.ts:20-30`. `grep -rn "TwinEventSource" python/` returns zero hits. |
| causal `CausalSourceKind` | **No — TypeScript only** | `web/lib/twin/scenario/causal.ts:31-46`. `grep -rn "CausalSourceKind" python/` returns zero hits. |

**Only 1 of the 4 named legacy vocabularies is a real, mappable Python-side
type.** The other 3 are real code (confirmed real and wired to the live UI
per `PHYSICIAN_WORKFLOWS.md`), but they exist exclusively in
`web/lib/twin/`/`web/lib/heart/` TypeScript — there is no Python definition
to import or map from. Per this wave's brief, they are **not** faked with an
invented Python mirror; see "What's still needed" below.

While reading `ensemble.py` for the "whatever else is genuinely
provenance-shaped" part of the brief, one more real, closed, Python-side
vocabulary turned up that isn't on the original list of 4:
`EnsembleProvenance.origin_quality` — a `Literal["observed", "derived",
"interpolated", "synthetic"]` (`ensemble.py:230`). It's mapped too, since
it's real and something will need to cite it.

## Mapping tables

### `ValueSource` -> `CanonicalProvenanceKind` (`map_value_source_to_canonical`)

| `ValueSource` (schemas.py:72-76) | `CanonicalProvenanceKind` | Why |
|---|---|---|
| `FILE_EXTRACTION` | `OBSERVED` | Pulled from an uploaded clinical file/image — real-world data, not computed. Nothing in the 4-member backend enum means "simulated," so this is the closest real bucket (also consistent with the frontend's `evidenceKind()` mapping `file_extraction` toward its `extracted`/`directly_observed` cluster, per `PHYSICIAN_WORKFLOWS.md`). |
| `USER_INPUT` | `USER_ASSERTED` | Direct, unambiguous match. |
| `DEFAULT_MODEL_PRIOR` | `MODEL_PRIOR` | Direct, unambiguous match. |
| `DERIVED` | `DERIVED` | Direct, unambiguous match. |

Exhaustive over all 4 current members (asserted by
`test_every_value_source_member_maps_without_raising`); an unrecognized
value raises `UnmappedProvenanceValueError`, not a silent default.

### `EnsembleProvenance.origin_quality` -> `CanonicalProvenanceKind` (`map_origin_quality_to_canonical`)

| `origin_quality` (ensemble.py:230) | `CanonicalProvenanceKind` | Why |
|---|---|---|
| `"observed"` | `OBSERVED` | Direct match. |
| `"derived"` | `DERIVED` | Direct match. |
| `"interpolated"` | `DERIVED` | Computed between known points — not a raw observation, not a full simulation run. |
| `"synthetic"` | `SIMULATED` | `ensemble.py`'s own docstring: "never labels a simulation percentile as a clinical confidence interval" — synthetic data is exactly what `SIMULATED` exists to flag. |

Same exhaustive-with-raise pattern as above.

## `get_provenance_for_ensemble(ensemble_id)`

Loads the real persisted record via `create_ensemble_store()` (the same
factory `api.py`'s `/api/v1/twin/ensemble/{id}` routes and Wave 2's
`get_ensemble` tool use — one store, not a parallel one) and turns
`EnsembleProvenance` (`ensemble.py:223-239`) into `ProvenanceRef`s:

- `origin_quality` -> one ref via `map_origin_quality_to_canonical`.
- `assumptions: list[str]` -> one ref per assumption string, kind
  `MODEL_PRIOR` (an assumption is a prior belief baked into how the model
  samples inputs — not an observation, not a computed value, not a
  simulation result itself).
- `evidence_ids: list[str]` -> one ref per id, kind `EXTERNAL_REFERENCE`
  (from the ensemble's perspective these are pointers to evidence that lives
  elsewhere, not values in hand).

**Deliberately excluded:** `origin_provenance: list[dict[str, Any]]`. It is
freeform — `ensemble.py`'s only real use of it is one ad hoc
`.get("source") == "synthetic_replay"` string check
(`ensemble.py:106-108`), not a closed, enumerable vocabulary. Mapping it
would mean inventing a taxonomy for keys that have no real type anywhere in
the codebase, which the brief explicitly rules out.

## `get_provenance_for_cardiac_findings(case_id)`

`derive_findings()` (`tools/cardiac_findings.py:129-272`) tags every finding
with a free-text `source` path (e.g. `"visualization.summary.ef_pct"`,
`"state.tissue_state.damage_zone_location + scar_fraction"`,
`"ct_segmentation.vista3d"`) — these are not `ValueSource` members. To stay
honest rather than inventing a second parallel classification:

1. For each finding, look for a `CardiacTwinState.source_map` entry
   (`schemas.py:232-260`, real, per-field, already carries a real
   `ValueSource`) whose `field` string is contained in the finding's
   `source` path (longest match wins, so `"tissue_state.damage_zone_location"`
   beats a shorter accidental substring). If found, map that entry's *real*
   `.source` through `map_value_source_to_canonical` — this is genuine,
   traced, per-value provenance, not a guess.
2. If no `source_map` field matches (this is the case for every
   `visualization.*`-sourced finding — EF, QRS, QTc — since those are
   outputs of the deterministic simulation pipeline itself, never raw
   tracked input fields), classify as `DERIVED`. This is not a default in
   the "silently misclassify" sense the brief warns against — it's a
   correct classification: `AGENTS.md` §1 says the deterministic physics
   core computes, never observes, and these are exactly its outputs.

Both branches are exercised by tests (`test_get_provenance_for_cardiac_findings_traces_source_map_field`
covers a `USER_INPUT`-sourced regional finding; `test_..._defaults_pipeline_output_to_derived`
covers the EF-derived global finding).

`CardiacTwinState.source_map` itself was verified genuinely provenance-shaped
and Python-accessible (it's a first-class `list[SourceMapEntry]` field on the
canonical state, populated by `agents/state_builder_agent.py`) — this reuses
it as raw per-field provenance only, with no component-binding logic
invented (Wave 2's tool-registry doc already flagged that
`physiologyBindings`/component-binding is frontend-only TS and out of scope;
this wave doesn't need it either, since the brief only asked for generic
per-finding provenance, not "evidence for component X").

## `ProvenanceRef`

Already existed in `python/hearttwin/assistant/schemas.py` (Wave 2, Agent
6) — **not** redefined here. `build_provenance_ref()` constructs it directly;
`source_module` + `detail` are folded into `ProvenanceRef.description`
rather than added as new fields, since the model is deliberately thin (its
own docstring: "it never carries a second copy of the value itself") and
this wave's constraints forbid editing `schemas.py`. No reconciliation is
needed on this point.

## What's still needed before all 4 vocabularies are covered

Only 1 of 4 is unified from the Python side today. The other 3
(`EvidenceKind`, `TwinEventSource`, `CausalSourceKind`) are real,
TypeScript-only code with no server-side presence to map from. Two paths
close the gap, and both are **Wave 4 (UI) dependencies**, not something this
wave's Python-only scope can finish:

1. **Mirror this mapping in TypeScript.** Write
   `web/lib/.../provenanceMapping.ts` with the equivalent
   `mapEvidenceKindToCanonical` / `mapTwinEventSourceToCanonical` /
   `mapCausalSourceKindToCanonical` functions, same exhaustive-with-throw
   discipline as this file, targeting the same `CanonicalProvenanceKind`
   values (as a shared string union, since the frontend can't import a
   Python enum).
2. **Or**, have the frontend send its own canonical-kind tag when it calls
   the future assistant API (e.g. as part of whatever payload eventually
   carries `web/lib/twin/provenance`'s `TwinProvenance`/`lineageForSnapshot`
   data into a physician conversation), so the backend never needs to
   re-derive canonical kind from a vocabulary it can't see.

Either way, nothing in this file blocks that work — `CanonicalProvenanceKind`
and `ProvenanceRef` are already the shared target contract (Wave 2), and nothing
about the frontend vocabularies changes as a result of this wave.

## Files added (no existing file modified)

- `python/hearttwin/assistant/provenance_mapping.py`
- `python/hearttwin/tests/test_provenance_mapping.py`
- `docs/assistant/wave3/provenance-mapping.md` (this file)

## Test run

```
python -m pytest python/hearttwin/tests/test_provenance_mapping.py -v
...
15 passed, 6 warnings in 0.23s
```

(The 6 warnings are the pre-existing repo-wide `datetime.utcnow()`
deprecation warning, matching Wave 2's noted convention — not new.)

Full-suite sanity check: `python -m pytest python/hearttwin/tests/ -q` ->
`968 passed, 1 skipped` immediately after adding these two files — no
regression, and no collision with the other Wave 3 agents' concurrently
in-flight, untracked files (`physician_brief.py`, `physician_tools.py`,
`orchestrator.py`, `context_resolver.py`, `language_integrity.py`), which
were left untouched per this wave's file-ownership rule. Two of those files
(`physician_brief.py`, `clinical-language-integrity.md`) already reference
`provenance_mapping.py` as a forthcoming dependency, confirming this is the
expected integration point for later Wave 3 work.

## Global Architecture Compliance: YES

No second provenance vocabulary or `ProvenanceRef`-like contract was
created — `CanonicalProvenanceKind`/`ProvenanceRef` (Wave 2) remain the one
canonical target, and this file only adds mapping *into* them. No existing
file was modified (`schemas.py`, `tool_registry.py`, `ensemble.py`,
`cardiac_findings.py` were all read-only inputs). The two new functions
(`get_provenance_for_ensemble`, `get_provenance_for_cardiac_findings`) are
plain importable functions, not a second tool registry or a competing
result contract — they return `list[ProvenanceRef]` for a caller (a tool
handler, `physician_brief.py`, or Laya) to attach to whatever `ToolResult`/
`AssistantArtifact` it's building.
