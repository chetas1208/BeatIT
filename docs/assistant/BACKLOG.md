# BeatIT Unified Assistant Campaign — Consolidated Backlog

> Built by reviewing this campaign's full history turn by turn (Waves 1-6,
> plus the two mid-campaign requirement additions). A subagent could not do
> this — it starts cold with no memory of this conversation — so this was
> compiled directly by the lead. Snapshot as of mid-Wave-6 integration
> (Agents 29/30 still finishing). Supersedes scanning individual
> `WAVE_N_HANDOFF.md` files for open items; each entry below cites its
> source.

## Not yet started

1. **Wave 6.5 — Physician Helper Hardening** (`docs/assistant/PHYSICIAN_HELPER_HARDENING.md`,
   added mid-Wave-6). Scoped as 5 agents: case-context hardening,
   report-personalization engine, report-consistency validator, UI
   cleanliness audit, case-isolation/report test matrix. Scheduled to run
   after Wave 6 integrates, before Wave 7.
2. **Wave 7 — E2E + Chaos** (original 8-wave plan). Should run against the
   *hardened* assistant (i.e. after Wave 6.5), not before.
3. **Wave 8 — Final Optimization + Release** (original 8-wave plan).
4. **The 25-agent certification campaign** (`docs/assistant/CERTIFICATION_CAMPAIGN.md`,
   saved during Wave 1). Explicitly scoped to run *after* the 8-wave build
   campaign finishes, not concurrently.
5. **Statusline setup** — the very first system reminder of this session
   (caveman-mode plugin) asked me to "proactively offer to set this up for
   the user on first interaction." I never made that offer. Flagging it
   here rather than doing it now unprompted, since it's unrelated to the
   BeatIT campaign and the user didn't ask for it.

## Real bugs/gaps found but deliberately not fixed yet (each has a named owner-wave)

6. **`safety_validator.py`'s "clinical" word false positive** (found Wave 3
   by the Physician Brief Engineer, still open per `WAVE_3_HANDOFF.md`):
   the bare `\bclinical(ly)?\b` pattern in `_BLOCKED_PATTERNS` has no
   allowlist entry, unlike `safety.py`'s own `DISCLAIMER`, so any text
   containing "clinical" (e.g. ensemble.py's own protective disclaimer)
   trips it. Currently handled by a narrow per-caller workaround inside
   `physician_brief.py`, not a proper fix. **Still unfixed as of Wave 6.**
   Recommended owner: a dedicated safety-validator review, not a rushed
   integration-time patch (per Wave 3's own recommendation).
7. **6 open adversarial gaps from Wave 5** (`docs/assistant/wave5/decision-adversary.md`,
   `docs/assistant/WAVE_5_HANDOFF.md`), still tracked as `xfail` in
   `test_decision_adversary.py`: leetspeak evasion, inserted-mid-word
   whitespace evasion, punctuation-broken multi-word phrases, a plain-English
   "what to take"/"what can i take" phrasing-coverage gap, one routing-only
   false positive ("at this moment in time" triggers spurious
   clarification), and 2 confirmed fallback bucket-ordering quirks
   (`select_tool_family`'s REPORT-shadows-TWIN bug; `classify_intent`/
   `select_tool_family` disagreement on dual-intent messages) — the latter
   two are routing-only, zero safety impact. **Wave 6 Agent 28's real safety-model
   evaluation found NVIDIA's content-safety model independently catches 4 of
   these 6** (leetspeak, inserted-space, both phrasing-gap cases) with zero
   false positives — a real, evidence-based argument for adding it as an
   additive layer (see item 9).
8. **`case_id`/`patient_id` schema mismatch** (found Wave 3, `WAVE_3_HANDOFF.md`):
   `ConversationContext` has no `case_id` field, so `get_cardiac_findings`,
   `get_pv_loop`, `get_raw_provenance_ledger`, `get_findings_by_region` are
   unreachable through the orchestrator's generic context-based dispatch —
   only the 3 `ensemble_id`-keyed tools are reachable today. Needs a
   deliberate decision (add `case_id` to the context, or unify it with
   `patient_id`), not a quick patch.

## Real findings from Wave 6 not yet acted on (integration decisions pending)

9. **Add NVIDIA content-safety model as an additive, fail-open pre-request
   layer** — Agent 28's recommendation, with real evidence (4/6 open
   bypasses caught, 0 false positives, ~0.35s median latency). Exact
   integration point documented: `classify_request_safety()`, after the
   existing rule-based + supplemental checks both return "normal," gated by
   a new off-by-default env flag, fails open on any error. Not implemented
   — a deliberate evaluation-only deliverable per that agent's scope.
10. **Fast-model candidate (`nvidia/nemotron-3.5-lightning-30b-a3b`) is
    likely NOT suitable for the fast/System-1 role as configured** — Agent
    26's real benchmark found a mandatory reasoning preamble consumes the
    token budget before any answer emerges under a modest budget, with
    erratic 4.3–28.6s latency on short prompts (not fast at all in
    practice). No working way found to disable the reasoning preamble.
    **This needs a real decision before FAST_MODEL_ID is locked**: try a
    different fast candidate, accept large budgets and strip the reasoning
    trace, or reconsider the fast/deep split entirely. Deep model
    (`nvidia/nemotron-3-super-120b-a12b`) performed well by contrast (Agent
    27), with the caveat that reasoning+content share one token budget
    there too (budget generously).
11. **Deep model's self-perceived-compliance jailbreak** (Agent 27, real
    finding): asked "what should I prescribe," the model opened with a
    refusal disclaimer but then named real drugs with dosing rationale
    anyway. `check_output_safety` caught and blocked it — confirms
    defense-in-depth works — but this is now documented, real evidence that
    **this model must never be trusted for its own refusal on T3
    boundaries**; both the pre-request and post-response gates must always
    stay in front of it. Not a bug to fix, a constraint to keep enforcing.
12. **`model_client.py` had a real 3-way agent collision** (Agents 26, 27,
    30 each touched it) that self-resolved during Wave 6 into one converged
    async/raising contract (28/28 tests passing together per Agent 26's
    final check). Worth a quick sanity re-check during Wave 6 integration
    that the final committed version is actually the intended one, not an
    accidental partial merge.
13. **Transient test failures Agent 26 observed** (`test_assistant_router.py`,
    `test_decision_adversary.py`) — re-checked directly just now: **currently
    passing, 63 passed + 6 xfailed**, matching Wave 5's expected tracked-gap
    count. This was almost certainly a snapshot mid-edit by Agent 29 (Model
    Router Engineer), not a real regression. Will re-verify once more at
    final Wave 6 integration.

## Coordination status (unchanged across all 6 waves)

14. **Codex has never joined the hacp session as peer b**, across 6 full
    waves of continuous, visible activity in the shared working tree
    (Shadow Trial feature, Split-Heart comparison feature, and most
    recently what looks like a "Missing Piece" feature per Agent 25's
    passing mention). No file collisions have occurred because file
    ownership has been managed unilaterally (explicit do-not-touch lists in
    every agent prompt) rather than through bilateral hacp contracts.
    `AppShell.tsx`'s Wave 4 mount point remains uncommitted for this reason
    (item 15).
15. **`AppShell.tsx`'s Wave 4 chat-trigger mount is still uncommitted**
    (`WAVE_4_HANDOFF.md`) — verified working in the live tree, interleaved
    with Codex's Split-Heart changes in the same file. Whoever next touches
    that file (Codex, or a future wave doing a careful hand-split) will
    incidentally commit both.
16. **Legacy chat removal (`CopilotDock`/`CareGuardCopilot` → unified
    panel) is still deliberately deferred** (`docs/assistant/wave4/legacy-chat-removal-plan.md`).
    Wave 6 landing real LLM generative capability is the trigger condition
    Wave 4 set for revisiting this — worth an explicit go/no-go decision
    once Wave 6 fully integrates, rather than letting it lapse silently.

## Smaller open items (low priority, tracked for completeness)

17. 6 of 7 `AssistantArtifact` types have no real detail view in the UI yet
    (only `PHYSICIAN_BRIEF` does) — Wave 4, honest placeholder fallback in
    place, not a regression.
18. `target_metric_changed` context event has no UI control anywhere in the
    frontend yet (Wave 4, Agent 19's finding) — genuinely unbuilt, not just
    unwired.
19. Provenance mapping covers 1.5 of the 4 originally-named legacy
    vocabularies from Python (Wave 3) — the other 2-3 are confirmed
    TypeScript-only; closing this needs either a frontend-side mirror or
    the frontend sending an already-canonical tag.
20. Numeric-claim validator doesn't catch "45% EF" (number-before-label)
    phrasing (Wave 2, documented limitation, not yet revisited).

## What this backlog is not

This does not re-litigate anything already fixed and closed (e.g. the
Unicode-evasion CRITICAL finding, the Laya wire-format bug, the "can I
take"/"ensemble" bucket-ordering bugs — all fixed and verified in Waves
3/5). Those are closed; see the relevant `WAVE_N_HANDOFF.md` for the
historical record if needed. This file tracks what's still open.
