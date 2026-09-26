# Physician Brief — Design Note (Wave 3, Agent 14)

Implements `docs/assistant/GLOBAL_ARCHITECTURE.md`'s "PHYSICIAN SUPPORT
ARCHITECTURE" / "DECISION SUPPORT OBJECT" for the `PHYSICIAN_BRIEF`
`AssistantArtifactType` Wave 2 reserved in `schemas.py`. Code:
`python/hearttwin/assistant/physician_brief.py`. Tests:
`python/hearttwin/tests/test_physician_brief.py` (10 passed).

## Scope

Built only from Wave 2's 4 real T0 tools
(`get_cardiac_findings`, `get_ensemble`, `get_ensemble_distributions`,
`get_ensemble_assumptions` — `tool_registry.py`). `get_ensemble` itself
(the full per-sample list) is not called — `get_ensemble_distributions`
already carries the summary statistics plus the same `provenance` block, so
calling both would duplicate a tool call for no new information this brief
needs.

Per `docs/assistant/PHYSICIAN_WORKFLOWS.md`, this brief can answer "what's
the plausible-twin ensemble spread and what assumptions drive it" and
"what AHA-segment findings does the simulation show" — real, tool-backed
questions. It cannot answer "how has this changed over time" (no timeline
tool exists) or "which assumption dominates the result" (no sensitivity
analysis exists) — see Limitations below.

## The observed-vs-derived judgment call (the important one)

`get_cardiac_findings` wraps `derive_findings()`
(`python/hearttwin/tools/cardiac_findings.py`). Its return shape is:

```
{
  "findings": [
    {id, title, region, territory, aha_segments, anchor, severity,
     summary, metric, codes, source, educational}, ...
  ],
  "imaging_source": "vista3d_segmentation" | "image_extraction" | "none",
  "segment_model": "AHA 17-segment",
  "disclaimer": "...",
  "model": "deterministic-cardiac-findings-v1",
}
```

**Every field in every finding is computed, not observed.** Concretely:

- `title`/`summary` are narrative text templated from a threshold decision
  (e.g. EF < 30/40/50 -> severity band) — a computation, not a fact taken
  from a source.
- `region`/`territory`/`aha_segments`/`anchor`/`codes` all come from a
  wall-name -> `(coronary territory, AHA segments, 3D anchor)` lookup table
  (`WALL_MAP`) applied to `tissue_state.damage_zone_location` — an
  anatomical inference, not a raw value.
- `severity` is a threshold classification (`_scar_severity`,
  EF-band logic), not a measurement.
- Even `metric` (e.g. `"EF 32%"`, `"QRS 130 ms"`) is a *formatted*
  string over a number (`ef_pct`, `qrs_duration_ms`, `scar_fraction`) that
  is **itself already the output of the deterministic hemodynamics/ECG/
  tissue simulation** (`hemodynamics.py`, ECG feature extraction, tissue
  modeling) — not a value read directly from an uploaded file or typed by a
  user. Tracing it further back, the *inputs* to that simulation
  (`heart_rate_bpm`, `edv_ml`, etc.) may genuinely be
  `ValueSource.FILE_EXTRACTION`/`USER_INPUT` — but `get_cardiac_findings`
  does not expose that lower layer (`CardiacTwinState.source_map`) at all;
  it only exposes the simulation's *output* metrics, already one full
  computation removed from anything a clinician or file directly reported.
- `imaging_source` looks like a raw fact ("was this VISTA-segmented?") but
  is itself computed by `_imaging_source()` scanning `source_map` for
  keyword hits (`"vista"`, `"segment"`, `"image"`, `"vision"`) — a
  classification, not a passthrough.

**I considered and rejected** putting the `metric` string alone into
`observed_evidence` (reasoning: "it's just a number, closest thing to raw
data here"). I rejected this because it would misrepresent a simulation
*output* as a directly-observed fact — exactly the failure mode
`GLOBAL_ARCHITECTURE.md`'s own example query calls out ("explain which
findings are directly observed versus model-derived"). Since this campaign's
entire observed/derived promise depends on that boundary being drawn
correctly everywhere, I chose rigor over cosmetically populating both
fields: **`observed_evidence` is empty this wave; every finding goes to
`derived_evidence`.**

This is a distinct kind of gap from `missing_evidence`/`conflicts`/
`possible_interpretations` being empty (those are empty because *no
detection logic exists yet*). `observed_evidence` is empty because *no tool
in this wave's registry exposes data that meets the "observed" bar* — the
one place genuinely-observed data lives in this codebase,
`CardiacTwinState.source_map` (tagged `ValueSource.FILE_EXTRACTION` /
`USER_INPUT`), is not surfaced by any of the 4 T0 tools. Both are stated
explicitly in `limitations`, with different wording, so a physician reading
the brief understands *why* each is empty.

`ProvenanceRef.kind` for the whole `get_cardiac_findings` tool call is set
to `CanonicalProvenanceKind.DERIVED`; the ensemble distributions call is
tagged `SIMULATED`; the assumptions call is tagged `MODEL_PRIOR`.

## Field-by-field mapping

| Bundle field | Source | Notes |
|---|---|---|
| `question` | authored | Templated one-liner naming the case/ensemble id. |
| `clinical_context` | `get_cardiac_findings` (`imaging_source`, `segment_model`) + `get_ensemble_distributions`'s `provenance` (`origin_quality`, `origin_snapshot_id`) + `ConversationContext` (`audience`, `patient_id`, `snapshot_id`) | Framing facts, not evidence claims. |
| `observed_evidence` | — | Empty this wave (see above). |
| `derived_evidence` | `get_cardiac_findings` findings | One entry per finding. |
| `simulated_results` | `get_ensemble_distributions` | Point-estimate summary per metric (`mean`/`median`/`min`/`max`/`sample_count`). |
| `uncertainty` | `get_ensemble_distributions` | Spread per metric (`standard_deviation`/`variance`/`quantiles`/`range`) — same records as `simulated_results`, split by field, not by source. |
| `missing_evidence` | — | Empty — no evidence-completeness logic exists (`PHYSICIAN_WORKFLOWS.md` confirms this is an unimplemented GAP). |
| `conflicts` | — | Empty — no cross-source conflict detection exists. |
| `assumptions` | `get_ensemble_assumptions` | Verbatim `EnsembleProvenance.assumptions` list. |
| `provenance` | Built by this module (one `ProvenanceRef` per tool call) + optional `extra_provenance` param | See "Provenance integration" below. |
| `limitations` | authored, auto-populated | See below. |
| `possible_interpretations` | — | Empty — no differential/interpretation-ranking logic exists. |

## What's empty, and why each is correct (not a bug)

- `observed_evidence` — no tool exposes `source_map`/raw-measurement data (see above).
- `missing_evidence`, `conflicts`, `possible_interpretations` — confirmed by
  `docs/assistant/PHYSICIAN_WORKFLOWS.md` ("Gaps Summary") as unimplemented
  anywhere in the codebase, not something this brief chose to skip.
- `simulated_results`/`uncertainty`/`assumptions` — empty only when no
  `ensemble_id` is supplied to `generate_physician_brief`; populated in
  full, verbatim, when one is.

Every one of these is named explicitly in the auto-populated `limitations`
list (`_SCOPE_LIMITATION`, `_LONGITUDINAL_LIMITATION`,
`_SENSITIVITY_LIMITATION`, `_MISSING_EVIDENCE_LIMITATION`,
`_CONFLICTS_LIMITATION`, `_INTERPRETATIONS_LIMITATION`,
`_NO_ENSEMBLE_LIMITATION` in `physician_brief.py`) — transparency about gaps
is itself a `GLOBAL_ARCHITECTURE.md`-mandated feature, not boilerplate.

## Safety scan false positives (discovered, not hypothesized)

Running `safety_validator.check_output_safety` against every string field —
as the task requires, "belt and suspenders" on top of the structural
guarantee that `DecisionSupportBundle` has no `recommended_treatment` field
— surfaced a **real, universal, pre-existing false positive**, not a corner
case:

- `ensemble.py`'s `provenance.assumptions` **always** includes the literal,
  hardcoded string `"Percentiles summarize accepted deterministic
  simulations and are not clinical confidence intervals."`
  (`python/hearttwin/ensemble.py:441`) on **every single ensemble** ever
  produced. `safety_validator.py`'s `check_output_safety` unions in
  `safety.py`'s `_BLOCKED_PATTERNS`, which has a bare `\b(clinical(ly)?)\b`
  word-boundary rule. `safety.py`'s `_ALLOWED_SAFETY_PHRASES` allowlists
  its own `DISCLAIMER`'s wording ("not for diagnosis or treatment
  decisions") before this blocklist runs, but has no entry for "clinical
  confidence intervals" — so this benign statistical qualifier trips the
  filter 100% of the time.
- Independently, `cardiac_findings.py`'s own `DISCLAIMER` ("...Not a
  clinical diagnosis.") trips the same class of false positive on
  `"diagnosis"` — both the `_BLOCKED_PATTERNS` regex and
  `validate_simulation_outputs`'s substring check. (This module does not
  include that string in the bundle — it's redundant with
  `AssistantResponse`-level `safety_disclaimer` — but the finding is
  recorded here because it's independent corroboration that this is a
  systemic allowlist gap, not a one-off in `ensemble.py`.)

Neither string is treatment-recommendation language — both are
**safety-protective disclaiming language** ("this is NOT a diagnosis,"
"these are NOT clinical confidence intervals") that happen to use a word
the blocklist also uses. Both are real, already-shipped text in files this
task is forbidden from touching (`ensemble.py`, `cardiac_findings.py`); the
correct fix is extending `safety.py`'s `_ALLOWED_SAFETY_PHRASES`, which is
out of this file's scope and is flagged here for human/Wave-4 review —
the same pattern Wave 2's Agent 10 used for its own supplemental safety
judgment calls (see `WAVE_2_HANDOFF.md`).

**Resolution implemented in `physician_brief.py`:**

1. `_hard_safety_gate` — zero-tolerance. Applied to every string this module
   itself authors (`question`, every `limitations[]` entry). Any block here
   is fatal (`PhysicianBriefSafetyError`) with no exceptions — this module
   fully controls this text.
2. `scan_bundle_strings` — runs `check_output_safety` over **every** string
   field (authored and pass-through alike) and returns every result,
   including passes, so nothing is hidden from a caller or test.
3. `generate_physician_brief` treats a block from step 2 as fatal **unless**
   it is *exactly* the one documented pattern (`_is_known_benign` /
   `_KNOWN_BENIGN_REGEX_PATTERNS = {r"\b(clinical(ly)?)\b"}`) — any other
   matched term (any `_OUTPUT_RED_FLAGS` phrase, any CareGuard phrase, any
   `validate_simulation_outputs` warning, any other `_BLOCKED_PATTERNS`
   regex) still hard-fails immediately, unchanged. This is a narrow,
   fully-documented carve-out for one specific, verified-benign,
   already-real string pattern — not a general softening of the safety
   gate. It does not touch `safety_validator.py`/`safety.py`.

`test_physician_brief.py::test_check_output_safety_finds_no_treatment_language`
asserts precisely this: any blocked field's `matched_terms` must equal
exactly `["regex:\\b(clinical(ly)?)\\b"]`, and that field must live under
`assumptions[]` — nowhere else. A second test
(`test_authored_strings_pass_check_output_safety_cleanly`) asserts the
module-authored strings pass with **zero** exceptions, no carve-out at all.

## Provenance integration status

`python/hearttwin/assistant/provenance_mapping.py` (Agent 13) **did not
exist** when this task started (confirmed via `find`/`ls` before writing any
code). `generate_physician_brief` was built to accept an optional
`extra_provenance: list[ProvenanceRef] | None` parameter for exactly this
case, defaulting to empty, and this module builds its own minimal
tool-level `ProvenanceRef`s (`get_cardiac_findings` -> `DERIVED`,
`get_ensemble_distributions` -> `SIMULATED`, `get_ensemble_assumptions` ->
`MODEL_PRIOR`) so the bundle's `provenance[]` is never empty even standalone.

**Agent 13's `provenance_mapping.py` landed later in this same wave**
(discovered when re-running the full suite after this file was written —
`test_provenance_mapping.py` now exists and passes). It exposes
`get_provenance_for_ensemble(ensemble_id) -> list[ProvenanceRef]` and
`get_provenance_for_cardiac_findings(case_id) -> list[ProvenanceRef]` — a
richer, per-value legacy-vocabulary mapping (translating
`ValueSource`/`origin_quality` into `CanonicalProvenanceKind` per field)
than this module's own coarse, one-`ProvenanceRef`-per-tool-call approach.

**Wiring left to the lead, as instructed** (task brief: "the lead will do
that wiring at handoff time if both pieces exist by then — don't block on
it"): a future integration step can replace/extend this module's
hand-built `tool_provenance` list by calling
`get_provenance_for_cardiac_findings(case_id)` and
`get_provenance_for_ensemble(ensemble_id)` and passing their results in via
`extra_provenance=`, or by editing `generate_physician_brief` directly to
call them instead of building `tool_provenance` itself. Either integration
is additive and does not require changing `DecisionSupportBundle`'s shape.

## Reconciliation note: `DecisionSupportBundle`'s location

`DecisionSupportBundle` is defined in `physician_brief.py`, not
`schemas.py`, per this task's file-ownership constraint (don't touch
`schemas.py`). It is a plausible candidate to move into `schemas.py`
alongside `AssistantArtifact`/`AssistantArtifactType` in a later
integration pass, once a lead confirms no other Wave 3 agent has
independently defined a competing version of this same object (per
`GLOBAL_ARCHITECTURE.md`'s "ONE artifact model" invariant — this file
should be checked for collisions with any other wave-3 agent's work at
handoff time).

## async signature note

The task brief's signature sketch (`def generate_physician_brief(...)`) is
implemented as `async def` because `ToolRegistry.execute(...)` is itself a
coroutine — every other Wave 2/3 consumer of the registry (`router.py`,
`test_tool_registry.py`, `physician_tools.py`) is async for the same
reason; a sync wrapper would need its own event-loop management for no
benefit.
