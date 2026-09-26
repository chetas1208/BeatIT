# Wave 3 — Context Resolution + Request Orchestration

> Scope: `python/hearttwin/assistant/context_resolver.py`,
> `python/hearttwin/assistant/orchestrator.py`, and the one-line rewire of
> `python/hearttwin/assistant/router.py` from Wave 2's hardcoded stub to a
> real call into `orchestrator.handle_message`. Read
> `docs/assistant/GLOBAL_ARCHITECTURE.md` and
> `docs/assistant/WAVE_2_HANDOFF.md` first — this note only explains the
> decisions made inside their constraints, it doesn't restate them.

## Why this agent exists

Wave 2 built five isolated, individually-tested pieces
(`schemas.py`, `router.py`'s stub, `laya_adapter.py`, `model_pool.py`,
`tool_registry.py`, `safety_validator.py`) but explicitly wired nothing
together — "architecture-in-isolation," per its own handoff. This wave's job
was the actual wiring: one real request-handling pipeline, plus the
context-resolution logic GLOBAL_ARCHITECTURE.md's "CONTEXT ARCHITECTURE"
section requires ("the assistant must resolve 'this'/'here'/'why did it
change?' from this context without the user restating it") — which nothing
in Wave 1 or 2 built either.

## The pipeline order, and why safety runs first

`orchestrator.handle_message` runs, per request:

```text
1. safety_validator.classify_request_safety(message)
     blocked?  -> return immediately (HUMAN_DECISION_REQUIRED, no tool call)
2. context_resolver.resolve_context(message, context)
     needs_clarification? -> return immediately (CLARIFICATION_REQUIRED)
3. LayaAdapter.classify_intent + select_tool_family
     (intent CLARIFICATION_REQUIRED -> same short-circuit as step 2)
4. tool dispatch: pick a registered tool in the selected family whose
   required input-schema fields are all present (non-None) in context;
   execute it; render deterministic text from its real ToolResult payload
     no matching tool/args -> return honest UNSUPPORTED / INSUFFICIENT_EVIDENCE
5. safety_validator.check_output_safety + validate_numeric_claims on the
   generated text
     either fails -> generic safe fallback text, same execution_class
6. safety_disclaimer is always attached (AssistantResponse's field default)
```

**Safety runs before context resolution and before any Laya call, not
after.** Two reasons:

- GLOBAL_ARCHITECTURE.md is explicit that Laya (System-1) "must never decide
  diagnosis, treatment, medication, emergency triage, or medical safety."
  If safety classification ran *after* a routing decision, a bug or
  edge case in routing could put a blocked request on some other, unguarded
  path before the safety check ever ran. Running it unconditionally first,
  before any other module even sees the request, makes that structurally
  impossible rather than merely unlikely.
- An emergency/diagnosis/treatment request must be blocked regardless of
  what "this" or "here" refers to. There's no scenario where resolving
  context first would change the safety verdict, so there's no reason to
  pay that step, or risk it throwing, before the one check that's actually
  load-bearing for patient safety.

Context resolution runs before Laya's intent/family classification for a
related reason: an ambiguous referent should never be silently guessed at by
a keyword router. `needs_clarification` (Wave 2's own method) is the single
source of truth for that judgment — `context_resolver.py` calls it rather
than re-implementing a second bare-referent heuristic, per
GLOBAL_ARCHITECTURE.md's "ONE decision-control plane" rule.

## `context_resolver.py`

Two functions, matching the task's two distinct concerns:

- **`resolve_context(message, context, laya=None) -> ContextResolution`** —
  calls `LayaAdapter.needs_clarification(message, context.model_dump())` and
  wraps its answer in a small result object (`context` unchanged,
  `needs_clarification: bool`, a human-readable `note`). It does **not**
  write anything new into `context` from the message text — see "what's
  deliberately not built" below.
- **`apply_context_event(context, event_type, value) -> ConversationContext`**
  — a pure function, no I/O, no network, no Laya call. A lookup table maps
  each of the five event types from the task brief to exactly one
  `ConversationContext` field:

  | `event_type`             | field updated    |
  |---------------------------|------------------|
  | `component_selected`      | `component_id`   |
  | `snapshot_selected`       | `snapshot_id`     |
  | `pair_opened`             | `pair_id`         |
  | `scenario_created`        | `scenario_id`     |
  | `target_metric_changed`   | `target_metric`   |

  Implemented via `ConversationContext.model_copy(update={field: value})` so
  every other field is carried over untouched and the input object is never
  mutated. An unknown `event_type` raises `ValueError` naming the valid set,
  rather than silently no-op'ing.

### Expected frontend call shape (not built here)

No frontend code was written this wave — this is backend-side logic the UI
will eventually call into once it exists. The expected flow: whenever the UI
already knows the user changed selection (clicked a component, scrubbed the
timeline, opened a paired twin, created a scenario, changed the target
metric), it posts something like `{conversation_id, event_type, value}` to a
future endpoint; the backend loads that conversation's current
`ConversationContext`, calls `apply_context_event(context, event_type,
value)`, and persists the result as the conversation's new context. No such
endpoint or persistence layer exists yet — this wave only builds the pure
transformation function a future endpoint would call.

## `orchestrator.py`

`handle_message(request, *, laya=None, registry=None) -> AssistantResponse`
is the single entry point. `laya`/`registry` are injectable for tests only;
`router.py` calls it with no overrides and gets Wave 2's process-wide tool
registry singleton and a fresh `LayaAdapter()` per request (the adapter is
stateless — constructing one per call costs nothing and matches how Wave 2's
own tests use it).

### Tool selection is generic, not per-tool-name special-cased

Step 4 above picks a tool by matching **every name in a candidate tool's
`input_schema["required"]` list against a same-named, non-None field on
`ConversationContext`** — e.g. `get_ensemble`'s required `ensemble_id`
against `context.ensemble_id`. This is deliberate: it means adding a new T0
tool to the registry later needs no orchestrator change at all, as long as
its required argument names line up with existing `ConversationContext`
fields.

It also means `get_cardiac_findings` (requires `case_id`) is **not
reachable this wave** — `ConversationContext` has no `case_id` field, only
`patient_id`, and the orchestrator does not guess that the two are
interchangeable. That's a real, visible gap, not a bug: three of the four
registered tools (`get_ensemble`, `get_ensemble_distributions`,
`get_ensemble_assumptions`) are reachable via `context.ensemble_id`;
`get_cardiac_findings` needs either a `case_id` field added to
`ConversationContext` or a documented case_id/patient_id relationship before
a future wave can wire it up. Flagged here rather than worked around with a
silent alias.

When more than one tool in a family could run (the three `UNCERTAINTY`
tools), a small keyword table breaks the tie: "distribution" in the message
prefers `get_ensemble_distributions`, "assumption" prefers
`get_ensemble_assumptions`, otherwise the first candidate whose args are
satisfiable wins (registration order: `get_ensemble` first).

**Known Wave-2-inherited quirk, not fixed here:** `LayaAdapter`'s
`select_tool_family` fallback checks its `EXPERIMENT` bucket (which matches
the literal word "ensemble") *before* its `UNCERTAINTY` bucket, so any
message containing the word "ensemble" itself routes to `EXPERIMENT` — a
category with zero registered tools this wave — rather than `UNCERTAINTY`,
where the real ensemble tools live. A message that says "uncertainty"
instead of "ensemble" (e.g. "what's the uncertainty here?") routes
correctly. This is Wave 2's own fallback keyword table
(`laya_adapter.py::_fallback_select_tool_family`), not something this wave's
task allowed touching (only `router.py` is licensed for edits outside new
files) — noted here as a real, load-bearing gap for whoever tunes that
keyword table next (or for when a real Laya endpoint replaces the fallback
entirely).

### Deterministic rendering, no LLM

`_render_tool_result` builds plain, short text directly from a tool's real
`canonical_payload` — sample counts, distribution metric names, assumption
text, finding counts — never narrative prose. This is intentional: it keeps
every generated string trivially checkable by the numeric-claim gate (no
numbers are stated beyond what's already in the payload), and it's the
correct scope for this wave (see below).

### Output rail always runs when a tool executed

`check_output_safety` runs on every tool-grounded response regardless of
which tool ran. `validate_numeric_claims` runs against that tool's own
`canonical_payload` whenever a tool executed (harmless when the response
happens to contain zero numeric claims, since an empty mismatch list is
valid). Either failing returns a fixed, generic fallback string with the
same `execution_class` and the same `tools_invoked` trace entry — the fact
that a tool ran is still true and worth recording, even though its text
output was withheld.

## What's deliberately NOT built (future work)

- **LLM / model-router integration.** Wave 2 built `model_pool.py` (an
  NVIDIA key pool) but no chat-completion client, and building one was
  explicitly out of this agent's scope. Every response this wave produces is
  therefore one of exactly two kinds: a safety/clarification short-circuit,
  or text rendered directly from a real `ToolResult` payload. Execution
  classes that GLOBAL_ARCHITECTURE.md describes as needing System-2
  reasoning (`GENERATIVE_EXPLANATION`, `COMPLEX_SYNTHESIS`) cannot actually
  be fulfilled yet — a request Laya routes there falls through the same
  "no tool in that family" path as anything else unsupported, which is
  correct: this wave must never pretend to reason when no reasoning step
  exists. Wiring a real model call (fast/deep/safety routing per
  GLOBAL_ARCHITECTURE.md's "MODEL ROUTER" section) is future work, expected
  around Wave 6 per the campaign's own numbering.
- **Message-text-derived context updates.** `context_resolver.resolve_context`
  only ever answers "is the referent already in `message` satisfied by the
  context we already have" — it never extracts a new component/snapshot id
  out of free text and writes it into `ConversationContext`. No such
  entity-extraction step exists anywhere in this codebase yet; guessing one
  out of prose is exactly the unsafe inference `CLARIFICATION_REQUIRED`
  exists to avoid.
- **The `case_id`/`patient_id` gap** noted above — `get_cardiac_findings`
  stays unreachable from the orchestrator until a future wave either adds a
  `case_id` field to `ConversationContext` or defines how it relates to
  `patient_id`.
- **Mounting `router.py` into `python/hearttwin/api.py`.** Still not done —
  `router.py` now calls the real pipeline internally, but the route itself
  remains unmounted from the live app, exactly as Wave 2 left it (see
  `docs/assistant/wave2/conversation-api.md` for the one-line mount this
  implies later: `app.include_router(assistant_router,
  prefix="/api/assistant")`).
- **A frontend endpoint/persistence layer for `apply_context_event`.**
  Described above as the expected call shape; not implemented.

## Tests

`python/hearttwin/tests/test_context_resolver.py` (11 tests) and
`python/hearttwin/tests/test_orchestrator.py` (11 tests), 22 new tests total.
Combined with Wave 2's own suites
(`test_assistant_schemas.py`, `test_assistant_router.py`,
`test_laya_adapter.py`, `test_model_pool.py`, `test_tool_registry.py`,
`test_safety_validator.py`): **94 passed** in one run, matching Wave 2's
pre-existing `datetime.utcnow()` deprecation warnings, no new ones. Full
repo suite: **988 passed, 1 skipped**, no regressions.

## Global Architecture Compliance: YES

No second router, context object, tool registry, or safety layer was
created — this wave calls into the single instances Wave 2 already built.
`router.py`'s edit is the intended integration step Wave 2's own handoff
named as a Wave 3 dependency, not a new competing surface. Laya's boundary
(routing signals only, never a safety verdict) is preserved: the
orchestrator's safety gate runs unconditionally before any Laya call, and no
new code path lets a Laya decision override or bypass
`classify_request_safety`/`check_output_safety`.
