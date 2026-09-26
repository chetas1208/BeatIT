# Wave 2 Handoff — Core Architecture

> Read `docs/assistant/GLOBAL_ARCHITECTURE.md` and `docs/assistant/WAVE_1_HANDOFF.md`
> first. Wave 3 agents must also read this file before starting.

Wave 2 built five isolated pieces under a brand-new
`python/hearttwin/assistant/` package — **nothing existing was modified**,
and **nothing is mounted into the live app yet**. All 74 new tests pass;
combined Wave 2 test run: `74 passed, 6 warnings` (pre-existing
`datetime.utcnow()` deprecation warnings matching existing repo convention,
not new). Committed at `7cae9e3`.

## What was implemented

1. **Conversation schemas + stub router** (`schemas.py`, `router.py`) —
   `ConversationContext`, `AssistantMessage`, `ToolResult`,
   `AssistantArtifact` (7 canonical types), `ExecutionClass` (11 values),
   `AssistantRequest`/`AssistantResponse` (disclaimer required, sourced
   verbatim from `python/hearttwin/safety.py`'s `DISCLAIMER`). `POST
   /message` router exists but is **not mounted** into `api.py` — that's an
   explicit, deferred one-line change (`app.include_router(assistant_router,
   prefix="/api/assistant")` near `api.py:1090`), left for a later
   integration step since `api.py` is shared with Codex's concurrent work.
2. **Laya adapter** (`laya_adapter.py`) — 7 named, bounded decision methods
   only (`classify_intent`, `select_tool_family`, `needs_evidence_retrieval`,
   `needs_simulation`, `needs_clarification`, `needs_physician_review_framing`,
   `is_complex_reasoning_required`). No generic "ask Laya anything" entry
   point exists — enforced by a test on the exact public method set.
   Env-guarded (`LAYA_ENABLED`, `LAYA_BASE_URL`, `LAYA_API_KEY`,
   `LAYA_TIMEOUT_SECONDS`); unconfigured or any failure → deterministic
   keyword-based fallback, never raises. Every decision carries
   `calibration_status: "uncalibrated"` hardcoded until Wave 5 runs a real
   calibration campaign — this must not change before then.
3. **NVIDIA key pool** (`model_pool.py`) — provider-neutral `ModelKeyPool`,
   reads `MODEL_API_KEY_1/2/3` + `MODEL_POOL_BASE_URL` (extends the existing
   `.env.example` `MODEL_API_KEY` convention, no vendor name in the public
   class/API). Round-robin over healthy keys; 429 quarantines immediately,
   other failures need 3 consecutive before quarantine; exponential backoff
   2s→300s cap. `FAST_MODEL_ID`/`DEEP_MODEL_ID`/`SAFETY_MODEL_ID` env vars
   default to Wave 1's researched candidates but are explicitly marked
   unlocked pending Wave 6 benchmarking. Zero secret exposure verified by
   tests (health output, `repr()`, no logging calls in the module at all).
   **Real NVIDIA keys are now live in `.env`** (user-supplied) — the pool
   will pick them up automatically once something calls it; nothing calls it
   yet (no chat-completion client was built this wave — that's a model-router
   task for a later wave, deliberately out of this wave's scope).
4. **Tool registry** (`tool_registry.py`) — 4 real, verified, T0
   (read-only, auto-execute) tools: `get_cardiac_findings`, `get_ensemble`,
   `get_ensemble_distributions`, `get_ensemble_assumptions`. All wrap
   confirmed-real backend code (see `docs/assistant/wave2/tool-registry.md`
   for file:line citations). No T1+ tool was registered — the only T1
   candidate from Wave 1 (`run_scenario_experiment`) turned out to be
   frontend-only TypeScript with no Python entry point; **do not fake it**.
   `get_ensemble_assumptions`'s signature was corrected from Wave 1's
   proposed `(case_id)` to the actually-real `(ensemble_id)` — Wave 1's doc
   should be treated as slightly imprecise on this one point, this handoff's
   version is authoritative.
5. **Safety validator** (`safety_validator.py`) — `classify_request_safety`
   directly imports and calls `intake_agent.py`'s real
   `_classify_intent_with_rules` (no copy-pasted regex, no way to soften a
   rule-based block); `check_output_safety` live-imports and unions
   `copilot.py`'s `_OUTPUT_RED_FLAGS` + `_BLOCKED_PATTERNS`/
   `validate_simulation_outputs` (from `safety.py`) + CareGuard's `_BLOCK` —
   a strict superset of **three** existing layers, not just the two
   blocklists originally scoped. An anti-drift test fails loudly if either
   source list's length changes without this file being updated.
   `validate_numeric_claims` checks EF/SV/CO/MAP/HR/EDV/ESV/QTc against a
   canonical payload dict, ±0.5 tolerance, flags claims with no matching
   canonical field as unsupported. **Known gap, not yet fixed:** "45% EF"
   (number-before-label) phrasing isn't matched — precision-over-recall
   tradeoff, documented in `docs/assistant/wave2/safety-validation.md`.

## Shared contracts changed

None — Wave 2 added a new, currently-disconnected package. No existing
schema, route, or module was touched. This is intentional: Wave 2 was
architecture-in-isolation: Wave 3+ will do the actual wiring together and
into the live app, at which point real integration risk begins.

## Files added

`python/hearttwin/assistant/{__init__,schemas,router,laya_adapter,model_pool,tool_registry,safety_validator}.py`,
`python/hearttwin/tests/test_{assistant_schemas,assistant_router,laya_adapter,model_pool,tool_registry,safety_validator}.py`,
`docs/assistant/wave2/{conversation-api,laya-integration,nvidia-key-pool,tool-registry,safety-validation}.md`.

## Files modified

None (by this campaign — `api.py`, `web/lib/api.ts`, `Progress.md`,
`Decisions.md`, `README.md` etc. show as modified in `git status` but that's
Codex's concurrent Shadow Trial work, not Wave 2's).

## Architecture decisions

- **Provenance vocabulary**: new minimal `CanonicalProvenanceKind` enum
  (OBSERVED/DERIVED/SIMULATED/MODEL_PRIOR/EXTERNAL_REFERENCE/USER_ASSERTED)
  defined in `schemas.py`. The 4 legacy vocabularies (backend `ValueSource`,
  frontend `EvidenceKind`, timeline `TwinEventSource`, causal
  `CausalSourceKind`) are **not** unified yet — a mapping layer
  (legacy enum → `CanonicalProvenanceKind`) is a **Wave 3 dependency**,
  needed before any tool can populate `ProvenanceRef.kind` from real
  evidence data.
- **`Tool.execution_class` field** was added beyond the original Wave 2
  scope (Agent 9's judgment call) so `ToolRegistry.execute()` can populate
  `ToolResult.execution_class` without the caller guessing it per call.
  Reasonable, not flagged as a concern.
- **Safety validator scope grew** from "union 2 blocklists" to "union 3 real
  safety layers" (Agent 10 found `copilot.py`'s actual behavior includes
  `_BLOCKED_PATTERNS` and `validate_simulation_outputs` beyond just
  `_OUTPUT_RED_FLAGS`). Correct call — the brief said "union both systems'
  actual behavior," and this is what actually replicating that behavior
  required.
- **Judgment calls needing human sign-off before Wave 3 treats them as
  settled** (all in `docs/assistant/wave2/safety-validation.md`): Agent 10
  added emergency/self-harm/treatment phrasings that `intake_agent.py`
  itself does not currently catch (e.g. "can't breathe," "crushing chest
  pain," "suicidal," "what pill should I take"). This is a **real behavior
  expansion** beyond today's production intake agent — flagged, not
  silently shipped. The phrase "can I take" was flagged by the agent itself
  as the highest false-positive-risk addition (could trigger on
  "can I take this simulation further?").

## Tests

74 new tests (schemas 14, router 5, Laya adapter 11, model pool 15, tool
registry 12, safety validator 17), all passing individually and in a
combined run. Full-suite runs during the wave (by different agents, at
different points) showed 843→858→875→899 passing with the only failures
ever seen being Codex's own concurrent, unrelated `shadow_trial_*` work
(resolved on Codex's side by the end of the wave). No regression introduced
by this campaign at any point.

## Known failures

None in Wave 2's own scope. Two known **gaps**, not failures: (1) numeric
claim validator misses "45% EF" phrasing (number-before-label), (2) no
chat-completion client exists yet to actually use `model_pool.py`'s keys —
both are explicitly out of this wave's scope, not oversights.

## Security / medical risks

- Real NVIDIA keys are live in `.env` (gitignored, mode 600, never echoed
  in any conversation, tool output, or subagent prompt). No code path in
  `model_pool.py` logs or exposes them (verified by test).
  `LAYA_API_KEY` has the same guarantee in `laya_adapter.py`.
- Safety validator's phrase-expansion judgment calls (above) need a human
  (or Wave 3's Clinical-Language Integrity work) to confirm they're
  desired before being treated as load-bearing — they are currently
  stricter than production `intake_agent.py`, which is the safe direction
  to err, but "stricter" still means new false-positive risk on ambiguous
  phrasing like "can I take this simulation further?"
- Nothing in Wave 2 is reachable from any live endpoint yet — zero
  production risk surface from this wave until something mounts `router.py`
  and wires the tool registry/Laya/safety validator together.

## Next-wave dependencies (Wave 3 — Physician Intelligence)

1. Build the legacy-provenance → `CanonicalProvenanceKind` mapping layer
   before physician-facing provenance claims can cite real evidence.
2. Wire `ToolRegistry` + `LayaAdapter` + `safety_validator` together into an
   actual request-handling pipeline (still doesn't need to be mounted into
   `api.py` yet — can remain testable-in-isolation per Wave 2's pattern).
3. Decide whether/how to grow the tool registry beyond the 4 T0 tools —
   `PHYSICIAN_WORKFLOWS.md`'s frontend-only gaps (component report,
   evidence-by-component, provenance, timeline, scenario/PV-loop) need a
   real decision: expose a new Python-side data path, or accept these stay
   frontend-only for now and scope Wave 3's physician conversations to what
   the 4 existing tools can actually answer.
4. Re-run `hacp --peer a poll` before touching any file outside
   `python/hearttwin/assistant/`/`tests/`/`docs/assistant/` — Codex has not
   joined the hacp session as peer b at any point in Waves 1-2 despite being
   continuously active in the shared tree; treat every shared file
   (`api.py` especially) as needing a fresh `git status` check immediately
   before any edit, not just before the wave starts.

## Global Architecture Compliance: YES

No second router, context, tool registry, safety layer, or conversation
store was created — this wave built the first (and so far only) instance of
each. No competing provenance vocabulary was introduced (the new canonical
enum is additive, with legacy-vocabulary unification explicitly deferred,
not duplicated). Laya's boundary (7 bounded decisions, never clinical
authority) was structurally enforced, not just documented.
