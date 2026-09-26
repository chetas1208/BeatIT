# Wave 6 Handoff — NVIDIA Model Benchmark + Routing

> Read `GLOBAL_ARCHITECTURE.md` and Waves 1-5 handoffs first. This is the
> first wave with real generative capability — Wave 6.5 (Physician Helper
> Hardening) and Wave 7 agents must read this file closely.

Wave 6 made real, billed calls against the user's live NVIDIA Build keys
(all 3, in `.env`) and wired real generative capability into the
orchestrator for the first time. Committed at `f5578b4`. Full suite: 1231
passed, 5 skipped, 6 xfailed.

## What was implemented

1. **`model_client.py`** (Agent 26, converged from a 3-way concurrent
   collision with Agents 27/30) — the OpenAI-compatible chat-completion
   layer Wave 2 deliberately left unbuilt. Async, raises `ModelClientError`/
   `NoHealthyKeyError` on total failure rather than fabricating a response,
   integrates with `model_pool.py`'s key rotation/quarantine.
2. **Fast model benchmark** (Agent 26) — `nvidia/nemotron-3.5-lightning-30b-a3b`
   is live and reachable, but **not suitable for the fast role as
   configured**: a mandatory reasoning preamble consumes the token budget
   before a clean answer emerges under modest budgets, and real latency was
   4.3-56s, erratic, uncorrelated with prompt length — independently
   corroborated by Agent 30's separate measurement. No working way found to
   disable the reasoning preamble this wave. **This needs a real decision
   before `FAST_MODEL_ID` is locked** (BACKLOG.md item 10).
3. **Deep model benchmark** (Agent 27) — `nvidia/nemotron-3-super-120b-a12b`
   performed well: correct provenance-kind preservation, zero hallucinated
   tool names in a tool-planning test, zero numeric fabrication. **Real,
   serious finding**: asked "what should I prescribe," it opened with a
   refusal disclaimer then named real drugs (carvedilol, metoprolol,
   spironolactone, etc.) with dosing rationale anyway —
   `check_output_safety` caught and blocked it across all four layers. This
   is now documented, proven evidence (not a hypothetical) that this model
   must never be trusted for its own refusal on T3 boundaries; both the
   pre-request and post-response safety gates must always stay in front of
   it, permanently, regardless of how well it otherwise performs.
4. **Safety model evaluation** (Agent 28) — `nvidia/nemotron-3.5-content-safety`
   caught 4 of Wave 5's 6 still-open adversarial bypasses (leetspeak,
   inserted-space, both natural-language phrasing-gap cases) with **zero**
   false positives on benign BeatIT-domain language, including the
   specifically-tricky "can I take a closer look at the PV loop?". Real,
   evidence-based recommendation to add it as an **additive, fail-open**
   pre-request layer — never a replacement, never able to block by being
   unavailable. Not wired in this wave (evaluation only, per scope);
   integration point documented precisely in
   `docs/assistant/wave6/safety-model-evaluation.md`.
5. **Model router** (Agent 29) — `orchestrator.py`'s "no tool matched"
   branch now calls a real model instead of immediately returning a plain
   fallback. **Wave 5's `laya_policy.should_defer_to_clarification` is now
   genuinely consulted for the first time**, using the real intent decision
   already made earlier in the pipeline (no duplicate classification).
   Since `classify_intent` measured 58.6% (below its 70% threshold), this
   currently returns `True` unconditionally — meaning every unmatched
   request today resolves to `CLARIFICATION_REQUIRED` before any model call
   ever happens. This is the correct, maximally-conservative behavior given
   real Wave 5 data, not a bug; real integration tests had to monkeypatch
   the policy open specifically to exercise the model-call path at all.
   Tool-grounding is enforced structurally: `validate_numeric_claims` runs
   with an empty canonical payload whenever no tool ran, so any numeric
   cardiac claim in an ungrounded response is automatically rejected
   regardless of prompt compliance. 4 real end-to-end integration tests
   pass, including one that deliberately forced a bogus model ID to prove
   graceful fallback to the deterministic path.
6. **Cost/latency/reliability** (Agent 30) — all 3 failure-injection
   scenarios (one/two/all keys down) pass against the campaign's own
   FAILURE MATRIX. Key rotation verified even distribution across all 3
   real keys under real load. No real rate limit was ever observed
   (consistent across all Wave 6 agents' real calls) — 3 real client-side
   timeouts on the FAST model were observed and handled correctly by the
   existing quarantine design (correctly did NOT over-quarantine on
   isolated blips).

## Real bugs/collisions found and self-resolved during the wave

- **3-way `model_client.py` collision** (Agents 26, 27, 30) — each built or
  modified the file independently before realizing the others had too.
  Self-resolved by the end of the wave onto one converged async/raising
  contract, verified by all three agents' final test runs passing together
  (28/28). No lead intervention needed — a good example of the "check for
  and reuse a sibling's real work" instruction actually working under real
  collision pressure.
- **4 pre-existing test files needed intentional updates** (`test_orchestrator.py`,
  `test_assistant_router.py`, `test_decision_adversary.py`) to reflect the
  new, more-conservative `CLARIFICATION_REQUIRED` behavior from wiring in
  Wave 5's policy — Agent 26 observed these as transiently "failing"
  mid-edit; Agent 29 completed the updates with each change accompanied by
  an inline comment explaining why. No safety assertion was weakened in
  any of these updates — re-verified by the lead via a fresh full-suite run
  before this handoff.

## Shared contracts changed

`orchestrator.py`'s module docstring gained a new pipeline stage (model
routing, point (g)). No existing schema, tool, or safety-check contract
changed shape — the new model-routing branch is purely additive to the
existing pipeline.

## Files added

`python/hearttwin/assistant/model_client.py`,
`python/hearttwin/tests/test_{model_client,model_reliability,orchestrator_model_routing}.py`,
`docs/assistant/wave6/{fast-model-benchmark,deep-model-benchmark,safety-model-evaluation,model-router,cost-latency-reliability}.md`.

## Files modified

`python/hearttwin/assistant/orchestrator.py` (the model-routing branch —
Agent 29's authorized exception), `python/hearttwin/tests/test_{orchestrator,assistant_router,decision_adversary}.py`
(updated to match the new, correct, more-conservative behavior).

## Known failures

None. See `docs/assistant/BACKLOG.md` (updated alongside this handoff) for
the full list of open decisions this wave surfaced rather than resolved
(fast-model suitability, whether to add the safety model layer).

## Security / medical risks

- The deep model's self-perceived-compliance jailbreak (item above) is now
  a documented, load-bearing reason the safety gates must never be removed
  or bypassed for convenience in any future wave, no matter how reliable
  the model otherwise seems.
- No new risk surface beyond what's already gated: the model-routing branch
  is reachable today, but only after `classify_request_safety`,
  `should_defer_to_clarification`, and (post-generation)
  `check_output_safety`/`validate_numeric_claims` all pass — the safety
  architecture from Waves 2-3-5 is fully in front of this new capability,
  not bolted on after.
- Real NVIDIA keys remain in `.env` only, never logged, never appearing in
  any committed file (re-confirmed by Agent 30 via direct string search,
  not just visual inspection).

## Next-wave dependencies

1. **Decide `FAST_MODEL_ID`** before locking anything — the current
   candidate is real evidence it's not suitable. Try a different
   candidate, or accept large budgets and strip reasoning traces, or
   reconsider whether BeatIT needs a fast/deep split at all given the deep
   model's own latency (4-40s) isn't exactly fast either.
2. **Decide whether to add the safety-model layer** Agent 28 recommended,
   using the exact integration point already documented.
3. **Wave 6.5 (Physician Helper Hardening)** should proceed next — the
   assistant can now actually generate text, which is exactly the
   precondition the hardening spec's case-awareness and report-personalization
   work needs to be meaningful (a case-aware report generator needs a real
   model in the loop to compose from, not just deterministic tool output).
4. **Revisit the legacy chat removal plan** (`docs/assistant/wave4/legacy-chat-removal-plan.md`) —
   Wave 4 set "Wave 6 lands real LLM-backed answers" as its trigger
   condition for reconsidering this. That condition is now met for a narrow
   slice of intents (whatever doesn't get deferred to clarification) —
   worth an explicit go/no-go conversation, not a default "not yet."
5. Codex has still not joined the hacp session as peer b through 6 full
   waves, and has now also shipped a "Missing Piece" feature
   (`python/hearttwin/missing_piece/`, `web/components/twin/missing-piece/`)
   alongside its earlier Shadow Trial and Split-Heart work. Continue
   treating every shared file as needing a fresh `git status` check
   immediately before any edit.

## Global Architecture Compliance: YES

No second model client, router, or safety layer was created. The existing
safety-first pipeline order (safety → context → Laya/policy → tools →
model → output validation) was extended, not bypassed or reordered. The
deep model's jailbreak attempt was caught by the existing output gate,
not a new one built to patch around it — the architecture held under real
adversarial pressure from a real model, which is the actual test of
whether "the control plane never becomes the source of cardiac truth" (or,
here, of clinical authority) holds in practice, not just on paper.
