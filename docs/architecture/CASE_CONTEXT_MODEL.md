# Case Context Model (Wave 6.5 — Case Context Hardening)

> Implements a slice of `docs/assistant/PHYSICIAN_HELPER_HARDENING.md`
> (§2-§10, §16-§18, §71-§75: case context stack, context resolver
> responsibilities, reference resolution, per-product-space context) and
> closes `docs/assistant/BACKLOG.md` item 8 (`case_id`/`patient_id` schema
> mismatch). This is a **hardening/extension** of Wave 3's
> `context_resolver.py`, not a second context system — see "Relationship to
> already-built work" for why the implementation lives in a new file
> (`python/hearttwin/assistant/case_context.py`) instead of editing
> `schemas.py`/`context_resolver.py` directly.

## Relationship to already-built work

- `python/hearttwin/assistant/schemas.py`'s `ConversationContext` (Wave 2) is
  **not modified**. It is a shared file other Wave 2/3/4 code already
  imports; this wave's constraint is new files only. `CaseContext` is an
  additive companion model, not a competing shape — every "current
  selection" field it carries (`component_id`, `scenario_id`, `ensemble_id`,
  `shadow_trial_id`, `pair_id`, `target_metric`, `product_space`,
  `audience`) is copied verbatim from an existing `ConversationContext`
  instance by `resolve_case_context`, never redefined with new semantics.
- `python/hearttwin/assistant/context_resolver.py`'s `resolve_context`/
  `apply_context_event` (Wave 3) are untouched and still own bare-referent
  detection and the 5 UI context-event types. `case_context.py` answers a
  different question ("which case, which revision, which prior snapshot")
  that `context_resolver.py` was never scoped to answer.
- `python/hearttwin/assistant/laya_adapter.py`'s `needs_clarification` is
  reused conceptually (same "don't guess, ask" philosophy) but not imported
  — `case_context.py`'s ambiguity handling is a typed return value
  (`CaseContextResolutionError`), not a second Laya-style heuristic.

## The `case_id` / `case_revision` decision, and the evidence for it

`docs/assistant/BACKLOG.md` item 8 (found Wave 3): `ConversationContext` has
no `case_id` field, so `orchestrator.py::_resolve_required_args` (which
matches a tool's required argument names 1:1 against `ConversationContext`
fields) can never satisfy `get_cardiac_findings` / `get_pv_loop` /
`get_raw_provenance_ledger` / `get_findings_by_region` — all four declare
`case_id` as a required input in `physician_tools.py`'s tool schemas
(`python/hearttwin/assistant/physician_tools.py:233,252,275,296` region).
Wave 3 explicitly declined to guess `patient_id` was a `case_id`
(`orchestrator.py`'s `_resolve_required_args` docstring says so directly).
This wave had to make that decision for real. The evidence read directly
from the current backend:

1. **`case_id` is a real, single, stable identity** —
   `python/hearttwin/schemas.py:352-364`'s `CaseRecord.case_id` (a
   `uuid4`-default string) is the literal key used everywhere a case is
   persisted or loaded: `python/hearttwin/tools/storage.py`'s
   `store_case`/`get_case` key on `f"case:{case_id}"` in Redis (when
   configured) or an in-memory dict otherwise. Every real case-scoped tool
   handler in `physician_tools.py` (`_load_case`, and `copilot.py`'s own
   `_load_case`) loads a case by exactly this id and nothing else.
2. **`case_id` is not the same concept as `patient_id`.**
   `ConversationContext.patient_id` exists (Wave 2) but `CaseRecord` has no
   patient-identity field of its own anywhere in the real backend schema —
   there is nothing to unify `case_id` with. Unifying them would mean either
   inventing a patient-identity field that doesn't exist yet, or silently
   treating an unrelated string as a case id — exactly the guess Wave 3
   already refused to make. **Decision: `case_id` is added as its own field,
   on the new `CaseContext` companion model, not merged into `patient_id`.**
3. **There is no case-revision/version/history concept in the backend at
   all.** Verified directly:
   - `tools/storage.py::store_case` **overwrites** the single stored value
     for a `case_id` on every call (`client.set(f"case:{case_id}", ...)` /
     the equivalent in-memory dict assignment) — no history list, no
     versioned keys, nothing retained from the previous save.
   - `CaseRecord.updated_at` (`schemas.py:355`) *looks* like a revision
     marker but is not maintained as one: every mutation route in `api.py`
     (`upload_file`, the extract/operate/simulate/recovery endpoints —
     `api.py:975,1129,1185,1239,1282`, each followed by
     `store_case(case_id, case.model_dump(...))`) reconstructs
     `case = CaseRecord(**case_data)` from the previously-stored dict and
     never reassigns `updated_at` before saving again. Since the stored dict
     already contains a concrete `updated_at` value, pydantic uses it
     as-is rather than re-running its `default_factory` — the field is
     effectively frozen at case-creation time across the whole pipeline.
     This was checked by grepping every `updated_at`/`store_case` call site
     in `api.py`; none reassigns the timestamp. **Using `updated_at` as
     `case_revision` would silently misreport every case as "never
     changed" — rejected.**
   - The one real, always-current, per-case signal that does change as the
     pipeline runs is `CaseRecord.status`, set explicitly at each stage in
     `orchestrator.py` (`"created"` → `"extracted"` → `"operated"` →
     `"recovery_simulated"` → `"self_improved"`, or an error branch like
     `"blocked"`/`"extraction_failed"`).
   - **Decision: `CaseContext.case_revision` is backed by `CaseRecord.status`
     today.** This is documented as a **coarse lifecycle marker, not a
     monotonic revision counter** — `"blocked"` is not orderable against the
     happy-path stages, and two different cases at the same status are not
     "the same revision" in any meaningful sense beyond "reached the same
     pipeline stage." A real revision system would need the backend to
     retain prior snapshots of `CaseRecord` (e.g. `case:{case_id}:rev:{n}`
     keys, or an append-only stage-result log with real timestamps) — not
     built here, since `AGENTS.md`/this wave's scope forbid touching
     `tools/storage.py` or the pipeline routes to add that.

## `CaseContext` schema

Defined in `python/hearttwin/assistant/case_context.py`:

| Field | Type | Source |
|---|---|---|
| `case_id` | `str` | The resolved `CaseRecord.case_id` |
| `conversation_id` | `str` | `ConversationContext.conversation_id` |
| `case_revision` | `Optional[str]` | `CaseRecord.status` (see decision above) |
| `current_snapshot_id` | `Optional[str]` | `ConversationContext.snapshot_id` |
| `component_id`, `scenario_id`, `ensemble_id`, `shadow_trial_id`, `pair_id`, `target_metric`, `product_space`, `audience` | as `ConversationContext` | copied verbatim, not redefined |
| `snapshot_history` | `list[str]` | caller-supplied only (see below); empty by default |

## How historical-reference resolution works, and its honest current scope

`resolve_historical_reference(case_context, reference_text)` detects a
"prior" cue (`before`/`earlier`/`prior`/`previously`/`last time`/`used to`/
`pre-`) versus a "current" cue (`now`/`current(ly)`/`today`/`right now`) in
`reference_text` via a small regex vocabulary (same style as
`laya_adapter.py`'s fallback keyword matchers, not imported from it since
those are private module functions).

- If a "prior" cue is present and `case_context.snapshot_history` (ordered
  oldest→newest) contains `current_snapshot_id`, it resolves to the entry
  **immediately before** it in that list (`resolution_kind="immediately_prior"`).
- If no such history is available, or the current snapshot is already the
  earliest known one, it returns `resolution_kind="unresolved"` — **it never
  guesses a snapshot id**.
- With no historical cue at all, it resolves to the case's current snapshot
  (`resolution_kind="current"`).

**Honest scope**: the real backend has **no persisted snapshot timeline for
a case at all** — no `Snapshot` model, no history list anywhere in
`python/hearttwin/schemas.py`. `ConversationContext.snapshot_id` is an
opaque, frontend-supplied *current* value only. `snapshot_history` is
therefore a caller-supplied input with nothing wired up to populate it yet;
today it is always empty in practice, so every "before"/"earlier" reference
resolves to `unresolved` until some future caller supplies real history
(the most plausible source, per
`docs/assistant/wave4/contextual-interaction.md`, is the frontend's
`Timeline.tsx` snapshot list — client-side today, never sent to the
backend). This module is **not** a temporal-reasoning engine: it has no
concept of "two visits ago," specific dates, or named/labeled snapshots —
only "immediately before the current one, if a real ordered list is given."

## Case isolation guarantee

Both public functions are pure/keyed strictly on their own inputs:

- `resolve_case_context` looks up exactly one case (`get_case(case_id)`,
  itself a strict key lookup — `tools/storage.py` never merges or falls back
  across keys) and copies fields only from that case's `CaseRecord` and the
  `ConversationContext` passed in. There is no process-global "current case"
  or cache that could leak between calls.
- `resolve_historical_reference` takes a `CaseContext` and reference text as
  its only inputs and reads nothing else (no globals, no other `CaseContext`
  instance, no shared mutable state).
- `test_case_context.py` persists two real, independent cases (`case_a_id`,
  `case_b_id`, distinct `uuid4`-suffixed ids, distinct `status`) and asserts
  resolving one never returns the other's `case_id`, `case_revision`,
  `component_id`, or `current_snapshot_id`; a separate test asserts an
  unknown `case_id` never silently falls back to a previously-resolved real
  case; a third asserts two `CaseContext`s with different `snapshot_history`
  resolve "before" independently.

## `orchestrator.py` integration points (documented, not implemented)

Per this wave's constraint, `orchestrator.py` is not touched. Exact points a
future wave should wire this into:

1. **`_resolve_required_args`** (`python/hearttwin/assistant/orchestrator.py:324-340`).
   This is the literal fix for BACKLOG item 8: it currently builds
   `context_dict = context.model_dump()` (line 369, inside
   `_select_and_execute_tool`) and matches each tool's required argument
   names against that dict's keys — `case_id` is never present, so
   `get_cardiac_findings`/`get_pv_loop`/`get_raw_provenance_ledger`/
   `get_findings_by_region` are permanently unreachable. A future wave
   should extend `context_dict` (a plain `dict[str, Any]`, not the
   `ConversationContext` model itself) with `case_id` before calling
   `_resolve_required_args` — the natural way is to call
   `resolve_case_context` first and, on success, merge
   `{"case_id": case_context.case_id}` into `context_dict`. This is a
   one-line, additive change at the call site (`orchestrator.py:369`), not a
   change to `_resolve_required_args`'s matching logic itself.
2. **`handle_message`** (`python/hearttwin/assistant/orchestrator.py:428-501`),
   specifically between step (b) (`resolve_context` / clarification gate,
   line 450-452) and step (c) (Laya routing, line 455). This is the natural
   place to call `resolve_case_context(request.context, case_id)` once a
   real `case_id` is available on the request path (today, `AssistantRequest`
   /`router.py`'s `POST /message` route has no `case_id` field or path
   param at all — that is itself a follow-up change, not assumed here). On
   `CaseContextResolutionError`, the integration should mirror the existing
   `_clarification_response()` short-circuit at line 451-452 (same pattern:
   return `ExecutionClass.CLARIFICATION_REQUIRED` rather than guessing which
   case is active) — this is the concrete home for spec §18's "if ambiguous,
   ask one clarifying question" UX. Building that response function is
   explicitly left to the orchestrator owner, not done here.
3. **Historical-reference resolution** has no orchestrator call site yet
   because nothing upstream currently detects a "before"/"earlier" chat
   message and routes it here — that detection would live alongside Laya's
   `classify_intent`/`select_tool_family` calls (`handle_message` step (c),
   `orchestrator.py:455-461`), most naturally as an additional bounded
   Laya-style yes/no decision (e.g. `needs_historical_reference`) feeding
   into a call to `resolve_historical_reference` before tool dispatch. Not
   built here — flagged as the next real gap, not a silent omission.

## What remains to be improved

- No real case-revision/version history exists in the backend; `case_revision`
  is a coarse status proxy today, not a true revision id. A real fix needs
  backend storage changes (append-only stage log or versioned keys) that are
  out of this wave's file-ownership scope (`tools/storage.py`,
  `orchestrator.py`).
- `snapshot_history` has no real producer yet — frontend `Timeline.tsx` data
  is never sent to the backend. Until it is, `resolve_historical_reference`
  will always return `unresolved` for "before"/"earlier" references in
  practice, which is the correct honest behavior but not yet a useful one
  end-to-end.
- Ambiguous-case detection (as opposed to missing-case detection) is not
  implemented — there is no backend concept of "more than one candidate case
  for this conversation" to detect ambiguity from yet.
- `AssistantRequest`/`router.py`'s `POST /message` route carries no `case_id`
  at all today; wiring `resolve_case_context` into `handle_message` (see
  integration point 2 above) requires that field to exist somewhere on the
  request path first.
