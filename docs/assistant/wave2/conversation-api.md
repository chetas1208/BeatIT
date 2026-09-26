# Wave 2 — Unified Conversation API: schemas + router skeleton

> Scope: `python/hearttwin/assistant/schemas.py`, `python/hearttwin/assistant/router.py`.
> Read `docs/assistant/GLOBAL_ARCHITECTURE.md` and `docs/assistant/WAVE_1_HANDOFF.md`
> first — this note only explains the decisions made inside their constraints,
> it doesn't restate them.

## Why a new `python/hearttwin/assistant/` package

`python/hearttwin/schemas.py` is the canonical schema module for the
extraction/operate/recovery pipeline (`CardiacTwinState`, `CaseRecord`, etc.).
The unified assistant is a different concern — conversation turns, tool
results, artifacts — layered *on top of* that canonical data, never a second
copy of it. Keeping it in its own package avoids bloating the existing
`schemas.py` and makes the eventual "mount into `api.py`" step a pure
addition (no diff to existing schema classes).

## Schema decisions

- **`ConversationContext`** matches `GLOBAL_ARCHITECTURE.md`'s field list
  exactly, one field per line, all optional except `conversation_id` and
  `audience`. `audience` is a `Literal["general", "physician"]` (not a str)
  so an invalid audience value is a 422 at the schema boundary, not a
  string-matching bug three layers downstream — this is exactly what the
  "physician support is a policy mode, not a second app" section calls for.
- **`AssistantMessage.tool_result_refs: list[str]`** holds references
  (tool/result identifiers), not embedded `ToolResult` objects. This follows
  the architecture doc's "chat text and structured artifacts are separate"
  rule literally: a message says *that* a tool ran, artifacts/tool results
  carry the actual structured payload.
- **`ToolResult.safety_level`** is `Literal["T0","T1","T2","T3"]` mirroring
  the tool safety levels table verbatim (read-only / computational /
  app-state action / high-stakes-never-autonomous). This field is what a
  future execution layer will use to decide "auto-run" vs "confirm first" vs
  "never" — the schema doesn't enforce that policy itself, it just carries
  the label faithfully.
- **`AssistantArtifact`** fields are a direct transcription of the "Artifact
  contract" block in `GLOBAL_ARCHITECTURE.md` (id, type, title,
  conversation_id, patient_id, snapshot_id, source_tool_ids, provenance,
  payload, created_at, version). `type` is a closed `Enum`
  (`AssistantArtifactType`) with the 7 kinds named in the task brief — closed
  rather than a free string so a typo'd artifact type fails fast at
  construction instead of silently producing an artifact the frontend can't
  render.
- **`AssistantRequest`** carries `conversation_id` at the top level *and*
  inside `context`. Rather than pick one and drop the other (the task spec
  asked for both), a `model_validator` rejects the request if they diverge.
  Rationale: `GLOBAL_ARCHITECTURE.md` is explicit that there must be exactly
  one context architecture and no second source of truth — a request where
  the envelope and the context object disagree about which conversation this
  is *is* a second source of truth, so it's treated as invalid input rather
  than silently resolved by picking a winner.
- **`AssistantResponse.safety_disclaimer`** defaults to the same `DISCLAIMER`
  constant `python/hearttwin/schemas.py` already uses for `CaseRecord` and
  `HealthResponse` (`python/hearttwin/safety.py`), not a new string. This is
  the direct implementation of AGENTS.md §1.4 ("every API response keeps the
  `safety_disclaimer`") for the new conversation surface.
- **`AssistantTraceMeta`** is intentionally a thin stub (`request_id`,
  `tools_invoked`, `model_used`, `latency_ms`) rather than the full
  observability record described in `GLOBAL_ARCHITECTURE.md`'s
  "OBSERVABILITY" section (System-1 decision, confidence, validation status,
  fallbacks, ...). It's split into its own model specifically so
  `AssistantResponse`'s shape doesn't need to change when a later wave fills
  in the real trace — only `AssistantTraceMeta` grows.

## Canonical provenance vocabulary

Wave 1 found four incompatible provenance vocabularies already live in the
codebase: backend `ValueSource` (4 kinds), frontend `EvidenceKind` (6 kinds),
timeline `TwinEventSource` (7 kinds), causal `CausalSourceKind` (6 kinds).
Per the Wave 1 handoff's explicit recommendation, this schema does **not**
attempt to unify those four. Unifying four already-shipped vocabularies used
by different subsystems is a real migration with its own blast radius — out
of scope for a schema-and-router skeleton task.

Instead, `CanonicalProvenanceKind` defines a fifth, deliberately minimal enum
that only the *new* conversation/artifact schema uses:

```text
OBSERVED            — directly measured / user-provided, unmodified
DERIVED             — computed deterministically from other canonical values
SIMULATED           — produced by a scenario/ensemble/simulation run
MODEL_PRIOR         — a default/prior value substituted for missing data
EXTERNAL_REFERENCE  — literature/reference-range value, not patient-specific
USER_ASSERTED       — stated in conversation, not independently verified
```

This set was sized to exactly cover the one guardrail-layer distinction
`GLOBAL_ARCHITECTURE.md` calls out as load-bearing — "observed vs. derived
vs. simulated" — plus the two cases (`MODEL_PRIOR`, `EXTERNAL_REFERENCE`) the
existing `ValueSource`/ensemble `assumptions` docs already need, and
`USER_ASSERTED` for claims a physician states directly in chat before any
tool confirms them. It is intentionally not a superset of all ~20 distinct
values across the 4 existing enums.

**Explicit future work, not done here:** a mapping layer
(`ValueSource → CanonicalProvenanceKind`, `EvidenceKind → CanonicalProvenanceKind`,
`TwinEventSource → CanonicalProvenanceKind`, `CausalSourceKind → CanonicalProvenanceKind`)
must be written before any real tool wraps existing evidence/timeline/causal
data into a `ToolResult` or `AssistantArtifact`. Until that mapping layer
exists, nothing in this codebase can actually populate `ProvenanceRef.kind`
from real data — that's expected and fine for a schema-only wave; it's a
dependency for whichever Wave 3+ agent wires a real tool through this schema.

## Vercel 60s / no-WebSocket fit

`POST /message` (in `router.py`) is a single synchronous request/response —
no streaming, no long-lived connection — so it fits Vercel's 60s serverless
function limit with no special handling. The stub handler returns
immediately; a real pipeline (Laya decision → tool call(s) → optional model
call → validators) has to complete inside that same request, same as the
existing `/extract`/`/operate`/`/simulate-recovery` routes in `api.py`
already do.

If a future wave needs incremental output (e.g. streaming a long
`GENERATIVE_EXPLANATION`/`COMPLEX_SYNTHESIS` response token-by-token), the
existing trace-stream SSE pattern (`XADD`/poll → FastAPI SSE endpoint →
browser `EventSource`, per `WAVE_1_HANDOFF.md`) is the model to reuse — a
second endpoint (e.g. `GET /message/{request_id}/stream`) the client opens
after issuing the same synchronous `POST /message`, not a WebSocket and not
a change to `POST /message`'s own contract. Not built here — no wave has a
concrete need for it yet, and speculative streaming plumbing isn't justified
at this stage per AGENTS.md §7 ("no over-engineering").

## How this would mount into `python/hearttwin/api.py` (not done here)

`api.py` is explicitly a shared file another integration step owns
carefully, so this wave does not edit it. The mount is a small, additive
change once the real pipeline exists behind `router.py`:

```python
from python.hearttwin.assistant.router import router as assistant_router
...
app.include_router(assistant_router, prefix="/api/assistant")
```

placed next to the existing `_app.include_router(build_router())` call
(`python/hearttwin/api.py:1090`). That's the entire integration: `router.py`
takes no dependency on `api.py`, so there's nothing to reconcile beyond the
one `include_router` line and picking the prefix. No existing route,
including the CopilotKit `/copilotkit` endpoint or the CareGuard routes,
needs to change for this to land — this is additive, not a merge. The actual
CopilotDock/CareGuardCopilot consolidation described in the Wave 1 handoff
is a separate, later step (Wave 4 per that handoff), not a prerequisite for
mounting this router.

## Deliberately deferred (not built in this wave)

- The mapping layer from the 4 legacy provenance vocabularies into
  `CanonicalProvenanceKind` (see above).
- Laya, the tool registry, and the model router — `router.py`'s
  `_build_stub_response()` is the single, clearly-marked extension point
  where that pipeline plugs in later; nothing else in the route handler
  should need to change.
- Mounting `router.py` into `api.py` (described above, not executed).
- Any streaming/SSE endpoint for this conversation surface (no concrete need
  yet).
- Physician-mode presentation policy differences (evidence density, raw
  measurements shown, etc.) — `ConversationContext.audience` carries the
  signal, but no formatting/policy logic consumes it yet; that's Wave 3+
  once real tools and a model exist to format against it.
