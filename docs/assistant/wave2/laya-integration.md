# Laya Integration — Wave 2, Agent 7 ("Laya Integration Engineer")

Implements an isolated, env-guarded adapter for Laya (Apache-2.0,
`github.com/NandhaKishorM/laya`) as BeatIT's System-1 fast-decision layer,
per `docs/assistant/GLOBAL_ARCHITECTURE.md` and `docs/assistant/LAYA_RESEARCH.md`.
**Laya is not reachable from this environment.** This wave builds the
adapter and its deterministic fallback only — no live Laya instance was
called or tested against.

## Files

- `python/hearttwin/assistant/laya_adapter.py` — the adapter.
- `python/hearttwin/tests/test_laya_adapter.py` — 11 tests (unconfigured,
  mocked success, mocked failure/timeout, structural boundary checks).
- This document.

No existing file was modified. `laya_adapter.py` imports
`ExecutionClass` (read-only) from the concurrently-developed
`python/hearttwin/assistant/schemas.py` to reuse the campaign's one
canonical execution-class vocabulary for `classify_intent`'s options,
rather than inventing a second one — per `GLOBAL_ARCHITECTURE.md`'s
"no competing vocabulary" rule.

## Hard boundary (restated, non-negotiable)

Laya may only produce bounded software/routing decisions. `LayaAdapter`
exposes exactly seven named, bounded methods and nothing else:
`classify_intent`, `select_tool_family`, `needs_evidence_retrieval`,
`needs_simulation`, `needs_clarification`, `needs_physician_review_framing`,
`is_complex_reasoning_required`. There is deliberately no generic
`ask_laya_anything`-style method — `test_no_generic_or_clinical_entry_point_exists`
asserts the adapter's public method set is exactly this list and that no
method name contains a clinical or generic-entry-point fragment
(`diagnos`, `prescrib`, `treat`, `medicat`, `dos`, `emergenc`, `triage`,
`ask`, `query`, `complete`, `chat`, `generate`).

## Env vars

| Var | Purpose | Default |
|---|---|---|
| `LAYA_ENABLED` | Explicit opt-in to attempt real Laya HTTP calls | `false` |
| `LAYA_BASE_URL` | Base URL of a running `laya-serve` instance | unset |
| `LAYA_API_KEY` | Optional bearer token | unset; never logged, including in exceptions |
| `LAYA_TIMEOUT_SECONDS` | Per-call timeout | `2.5` |

`is_configured()` mirrors the existing `VISTA3D_ENABLED` +
`VISTA3D_API_BASE` pattern in `tools/vista3d_client.py`: both the boolean
flag AND the base URL must be set, so a stray leftover `LAYA_BASE_URL` in
an environment never triggers a network call on its own. If unconfigured,
every method returns a fallback-sourced decision immediately — the `httpx`
import and any network code path are never reached (verified by
`test_unconfigured_every_method_falls_back_without_network`, which swaps in
an `httpx.AsyncClient` replacement that raises `AssertionError` if
constructed at all).

Every real call goes through `_call_systemone()`, wrapped in a bare
`try/except Exception` with a 2.5s default timeout — any failure (timeout,
connection error, non-2xx status, unparseable body, unknown choice value)
returns `None` and the caller falls through to its fallback. The adapter
never raises to its caller.

## Why the wire call is defensive, not exact

`LAYA_RESEARCH.md` confirms Laya's HTTP server (`POST /v1/systemone`,
Jev-wire-compatible) and its Python-level shape
(`router.predict(state, questions)` → `answers[name][type]`) but explicitly
flags: *"the literal request/response JSON body was not present in the
fetched excerpts"*. Since no live instance exists to test against, the
adapter:

- **Request**: builds `{"state": {"text": ..., **context}, "questions": {name: {"type": "choice"|"noul", "instructions": ..., "criteria": {...}}}}` — the most direct HTTP transliteration of the confirmed Python `predict()` shape.
- **Response**: parses defensively — accepts the answer either under `body["answers"][name]` or directly at `body[name]`; accepts a choice under `choice` or `value` (string or `{"value"|"label": ...}`); accepts a yes/no under `noul`, `answer`, or `value` (bool, numeric ≥0.5, or `"yes"/"no"/"true"/"false"`); accepts a score under `score`, `probability`, or `confidence`.
- Any shape it doesn't recognize returns `None` → fallback. This is intentionally permissive on the parse side and conservative on trust: a shape mismatch never crashes, it just forfeits the Laya answer for that call.

**Before wiring this against a real `laya-serve` instance**, re-verify the
actual JSON body from source or a live server and tighten `_call_systemone`
accordingly (`LAYA_RESEARCH.md`'s prerequisite #5).

## Calibration caveat (why there's no `confidence` field anywhere)

`LAYA_RESEARCH.md`'s benchmark numbers: Laya's fine-tuned checkpoint reaches
higher accuracy (0.766) than the stated Jev baseline (0.727) but **worse**
calibration — ECE 0.213 vs. Jev's 0.144. Higher accuracy and better
calibration are not the same claim, and an uncalibrated probability used as
an automation-confidence threshold is exactly the failure mode
`GLOBAL_ARCHITECTURE.md`'s "LAYA EVALUATION REQUIREMENT" warns against.

Consequently:
- Every `ChoiceDecision` / `YesNoDecision` carries `raw_score` (a plain
  float, explicitly not named "confidence") and a hardcoded
  `calibration_status: Literal["uncalibrated"]` field — there is no code
  path that can produce any other value for `calibration_status` today.
- `test_every_decision_carries_source_and_uncalibrated_status` asserts both
  fields exist on the schemas and that no field named `confidence` exists.
- `raw_score` is informational only in this wave; nothing in the adapter or
  its (nonexistent) callers thresholds on it.

## Fallback heuristics chosen, and why

All fallbacks are intentionally simple regex/keyword rules over the
lowercased, whitespace-normalized request text (`_normalize`,
`_contains_any` — the same small-helper pattern already used in
`agents/intake_agent.py`'s rule-based classifier, duplicated locally rather
than imported so this new adapter has zero coupling to another agent's
file). They are the safety net, not the product — a wrong fallback route
costs a retry or a slightly-too-deep model call, never a safety failure,
per `LAYA_RESEARCH.md`'s "MAY decide" framing.

- **`classify_intent`** — keyword router over
  `python/hearttwin/assistant/schemas.py`'s `ExecutionClass` enum (the one
  canonical vocabulary, not a second invented one). Ordered so
  high-precision cues (simulation/evidence/report/computation keywords)
  are checked before the broad, low-recall "why/explain" bucket, and an
  empty or single-word request routes straight to
  `CLARIFICATION_REQUIRED`.
- **`select_tool_family`** — keyword router over the seven
  `GLOBAL_ARCHITECTURE.md` "SINGLE TOOL REGISTRY" categories
  (TWIN/EVIDENCE/PHYSIOLOGY/EXPERIMENT/COMPARE/UNCERTAINTY/REPORT) plus
  `NONE` for no-tool-needed follow-ups.
- **`needs_evidence_retrieval`** — true on explicit evidence/source/
  provenance/citation language.
- **`needs_simulation`** — true on scenario/what-if/recovery/rerun/
  experiment language.
- **`needs_clarification`** — true if the request is near-empty or a single
  word, OR it contains a bare referent (`this`/`that`/`it`/`here`) with no
  context id (`patient_id`/`snapshot_id`/`component_id`/`scenario_id`/
  `ensemble_id`/`pair_id`) available to resolve it — mirroring
  `GLOBAL_ARCHITECTURE.md`'s "CONTEXT ARCHITECTURE" resolution rule for
  `this`/`here`/`why did it change?`.
- **`needs_physician_review_framing`** — true whenever
  `context["audience"] == "physician"`, or (in general audience) the text
  touches risk/uncertainty language (`concerning`, `abnormal`, `risk`,
  `uncertain`, `assumption`, "should I be worried"). This only controls
  *framing density*, never whether something actually is risky — the
  actual safety blocking stays entirely in `intake_agent.py` and
  `copilot.py::_check_output_safety`, untouched by this adapter.
- **`is_complex_reasoning_required`** — true for longer requests (>18
  words) or explicit comparison/synthesis language (`compare`,
  "summarize ... and", "which findings/results are",
  "directly observed versus"), approximating
  `GLOBAL_ARCHITECTURE.md`'s `COMPLEX_SYNTHESIS` example query.

## What Wave 5 (Laya calibration campaign) must do before any of this changes

Per `LAYA_RESEARCH.md`'s "Calibration Campaign Prerequisites", none of these
fallback heuristics should be replaced with trusted Laya-only routing until:

1. A small BeatIT-specific labeled eval set exists for these exact seven
   routing decisions (not cardiac content — the software-routing decisions
   themselves).
2. Accuracy, Brier score, and ECE are measured on that set — Laya's
   self-reported 0.766/0.061/0.213 do not transfer to an unseen domain
   without re-measurement.
3. A temperature-refit / calibration pass runs on held-out BeatIT data,
   mirroring Laya's own documented ECE improvement after refit
   (0.466→0.081, 0.314→0.106).
4. An explicit confidence threshold + fallback path is decided and
   documented per decision (e.g. "below X, fall back to this same
   deterministic router"), with every Laya call logged (input, output,
   `raw_score`) through the existing `trace_sink` seam in
   `python/hearttwin/tools/weave_trace.py` for auditability.
5. The real `POST /v1/systemone` request/response schema is re-verified
   against source or a live instance, and `_call_systemone`'s defensive
   parsing in `laya_adapter.py` is tightened to match exactly (dropping the
   speculative alternate key names once the real shape is confirmed).
6. Regardless of 1–5, this adapter's hard boundary does not move: Laya
   still only answers the seven bounded routing questions above, and
   `calibration_status` only ever changes away from `"uncalibrated"` once a
   real calibration campaign has run and its results are documented here —
   it must never be flipped as a matter of convenience.

## Global Architecture Compliance

No competing router, context object, tool registry, or safety layer was
created. The adapter reuses `ExecutionClass` from the shared
`assistant/schemas.py` rather than defining a second intent vocabulary, and
does not touch `intake_agent.py`'s or `copilot.py`'s existing safety
blocking in any way — both remain the sole authority on
diagnosis/treatment/emergency blocking.
