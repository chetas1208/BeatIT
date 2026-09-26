# Wave 5 Handoff — Laya Decision Specialization (COMPLETE)

> Read `GLOBAL_ARCHITECTURE.md` and Waves 1-4 handoffs first. Wave 6 agents
> must also read this file.

Wave 5 was interrupted mid-run by an account-wide spend-limit rate limit
(3 of 5 sub-agents failed before producing output). The user raised the
limit and said "resume." The 3 failed agents (Decision Fixture Engineer,
Laya Evaluation Engineer, Decision Adversary) were re-run from scratch and
all completed successfully this time. This document reflects the final,
complete state — an earlier "INCOMPLETE" version of this file existed
between the interruption and the resume; it is fully superseded by this one.

## What was delivered

- **Agent 21 (Decision Fixture Engineer)** — 160 independently-labeled
  fixtures across all 7 `LayaAdapter` decision types
  (`python/hearttwin/tests/fixtures/laya_decision_fixtures.py`), labeled
  from `GLOBAL_ARCHITECTURE.md`'s own decision definitions, never by
  copying the fallback's current output. Found a real structural gap by
  re-reading the fallback source: `classify_intent`'s if/elif cascade never
  contains 3 of the 11 real `ExecutionClass` values
  (`INSUFFICIENT_EVIDENCE`, `HUMAN_DECISION_REQUIRED`, `UNSUPPORTED`) in any
  branch — these are unreachable by construction, not just unlikely.
- **Agent 22 (Laya Evaluation Engineer)** — got a REAL Laya instance
  running (pip-installed `laya[serve]` + the `convaiinnovations/laya`
  checkpoint, reusing a ~13.7GB venv/HF-cache orphaned by the first,
  interrupted attempt) and benchmarked it head-to-head against the
  deterministic fallback on all 160 real fixtures:

  | Decision type | Fallback (live in prod) | Real zero-shot Laya |
  |---|---:|---:|
  | classify_intent | 58.6% | **75.9%** (Laya wins) |
  | select_tool_family | **73.3%** | 63.3% |
  | needs_evidence_retrieval | **85.0%** | 65.0% |
  | needs_simulation | **90.0%** | 70.0% |
  | needs_clarification | **95.2%** | 52.4% |
  | needs_physician_review_framing | **90.0%** | 75.0% |
  | is_complex_reasoning_required | **85.0%** | 50.0% |
  | **Overall** | **80.6%** (129/160) | 65.0% (104/160) |

  Brier/ECE computed only for real Laya (it has probabilities); explicitly
  not fabricated for the fallback, which has none by design. Also found and
  proved, live, a real integration bug (see "Integration fixes" below) and
  cleaned up all Docker/process state afterward (including a second,
  previously-undetected orphaned `laya-serve` process from the first
  interrupted attempt — flagged for future retries that a plain
  `docker ps -a` check misses bare processes).
- **Agent 23 (Laya Specialization Engineer)** — delivered before the first
  interruption fully landed. Conditional decision framework, honestly built
  without Agent 22's numbers (which didn't exist yet at the time): **no
  fine-tuning justified for any of the 7 decision types**, independent of
  accuracy — Laya isn't reliably reachable from a normal run of this
  environment and there's nowhere near enough labeled data regardless. This
  conclusion is unchanged by Agent 22's now-real numbers (the reasoning was
  infra/data-scarcity based, not accuracy-based).
- **Agent 24 (Decision Policy Engineer)** — `laya_policy.py`, a fully
  parameterized per-decision-type trust threshold with a structural
  clinical-authority guard (verified live: raises `ClinicalAuthorityRefused`
  on 8 misuse variants, e.g. `recommend_treatment`, `adjust_dosage`). Built
  entirely provisional (0.70 uniform floor) since no real numbers existed
  yet — now updated (see "Integration fixes" below) with Agent 22's real
  measurements.
- **Agent 25 (Decision Adversary)** — red-teamed the real, shipped
  `orchestrator.py` → `safety_validator.py`/`laya_adapter.py` pipeline (not
  a mock). 10 confirmed bypasses across prompt sensitivity, ambiguous
  intents, OOD input, and — most seriously — Unicode/leetspeak/spacing
  evasion of both the input gate (`classify_request_safety`) and, critically,
  the **output gate** (`check_output_safety`). Confirmed the multi-turn
  social-engineering vector is architecturally unreachable (no cross-call
  memory exists yet). All captured as `xfail(strict=True)` tests.

## Integration fixes applied by the lead (all directly evidenced by an agent's findings)

1. **`safety_validator.py` — Unicode evasion, the CRITICAL finding.** Added
   `_deobfuscate()`: strips zero-width characters (U+200B/200C/200D/2060/FEFF),
   NFKD-decomposes and drops combining marks, then NFKC-refolds (closes
   fullwidth-homoglyph evasion too). Wired into both `classify_request_safety`
   (text is deobfuscated before reaching `intake_agent.py`'s regex, without
   editing that file) and `check_output_safety` (before any of its four
   independent layers). Verified live against Agent 25's exact proof-of-concept
   inputs — all now correctly blocked. 4 of the 10 `xfail` tests flipped to
   permanent regression guards (`git log` for `fae8024` has the exact diff);
   the other 6 remain honestly `xfail` — leetspeak, inserted-mid-word spacing,
   punctuation-broken multi-word phrases, and a plain-English phrasing
   coverage gap ("what to take") are real, different-shaped problems that need
   their own review, not a rushed follow-on fix riding on this one's coattails.
2. **`laya_adapter.py` — wire-format bug.** Real Laya's `choice`-question
   parser reads `criteria` as `{label: description}` pairs; the adapter was
   sending `{"options": [list]}`, which the server parsed as one bogus
   option literally named `"options"`. Fixed to `{opt: opt for opt in
   options}` — each option's own label doubles as its description (no
   richer per-option description format was ever specified anywhere in this
   campaign's research). This means, as of this fix, flipping
   `LAYA_ENABLED=true` would for the first time actually exercise Laya for
   `classify_intent`/`select_tool_family` rather than silently always
   falling through.
3. **`laya_policy.py` — wired in real measured accuracy.** `DEFAULT_POLICY`'s
   7 provisional (0.70 placeholder) entries were replaced with Agent 22's
   real fallback-accuracy numbers via the module's own designed
   `with_measured_accuracy` API (`accuracy`/`source`/`reference` change;
   `defer_threshold`, a policy choice not a measurement, stays at 0.70).
   Net effect: `classify_intent` (58.6%) is now the one decision type that
   doesn't clear its own threshold — `should_defer_to_clarification` returns
   `True` for it until either the fallback cascade is improved or the
   threshold is deliberately revisited. The other 6 clear it. 3 of Agent
   24's own tests were updated to match this new, correct reality (they had
   correctly asserted the old all-provisional state at the time they were
   written).

## Files added

`python/hearttwin/tests/fixtures/{__init__,laya_decision_fixtures,laya_decision_fixtures_stopgap}.py`,
`python/hearttwin/tests/test_{laya_decision_fixtures,laya_fallback_evaluation,decision_adversary}.py`,
`docs/assistant/wave5/{decision-fixtures,laya-evaluation,decision-adversary}.md`,
`docs/assistant/wave5/artifacts/*` (raw pip/server logs, full raw request/response
JSON for all 160 real-Laya calls, the wire-format bug evidence, both
fallback/real-Laya per-fixture prediction dumps — preserved per the
campaign's "preserve all benchmark artifacts" rule).

## Files modified

`python/hearttwin/assistant/{laya_adapter,laya_policy,safety_validator}.py`
(the 3 integration fixes above), `python/hearttwin/tests/test_laya_policy.py`
(3 tests updated to match the now-measured `DEFAULT_POLICY`),
`python/hearttwin/tests/test_decision_adversary.py` (4 tests flipped from
`xfail` to permanent regression guards).

## Tests

1202 passed, 1 skipped, 6 xfailed (down from 10 xfailed before the Unicode
fix — each remaining one is a real, open, documented gap). No regressions
at any point across the whole wave, including through all 3 integration
fixes.

## Known failures / open gaps (genuinely unresolved, tracked as `xfail`)

- Leetspeak substitution ("wh4t sh0uld i t4ke") bypasses `classify_request_safety`.
- Whitespace inserted inside a word ("medi cation") bypasses it too — a
  different, higher-false-positive-risk fix than Unicode normalization,
  deserving its own review.
- Punctuation-broken multi-word phrases ("should. i. go. to. the. er")
  bypass `intake_agent.py`'s literal multi-word regex.
- Plain-English phrasing coverage gap: "what to take" / "what can i take"
  are never recognized as treatment-seeking (only the exact "what should i
  take" is).
- Routing-only false positive: "at this moment in time" spuriously triggers
  `CLARIFICATION_REQUIRED` (the bare-referent check matches "this" as a
  temporal determiner). Zero safety impact, UX-only.
- `select_tool_family`'s fallback still has 2 confirmed-real bucket-ordering
  quirks (REPORT shadowing TWIN for "component report" phrasing;
  `classify_intent`/`select_tool_family` can disagree on dual-intent
  messages) — routing-only, zero safety impact since `classify_intent`'s
  output isn't otherwise consumed downstream yet.

## Security / medical risks

- The CRITICAL Unicode-evasion finding against `check_output_safety` is now
  fixed, not just documented — this matters because Wave 6 is about to wire
  in real LLM-generated text, which is exactly when this gate becomes
  load-bearing for the first time.
- `classify_intent` measuring below its own trust threshold is now a real,
  policy-encoded fact (`laya_policy.py`), not a hidden risk — the
  orchestrator doesn't consume this policy module yet (confirmed: only
  `classify_intent`/`select_tool_family` are even called today, and neither
  goes through `should_defer_to_clarification`), so this is armed and ready
  for whichever wave wires the policy module into the orchestrator, not yet
  exploitable.
- No clinical decision authority was added or implied anywhere — Laya's
  boundary (7 bounded routing decisions, never clinical) is unchanged.

## Next-wave dependencies

1. Wire `laya_policy.py`'s `should_defer_to_clarification` into
   `orchestrator.py` (still not connected — flagged by both Wave 3 and
   Agent 24 independently).
2. Consider the 6 remaining open adversarial gaps above for a future
   dedicated pass — none are blocking, but the "what to take" phrasing gap
   and the inserted-space evasion are the two most likely to matter once
   real users start typing naturally.
3. If/when Laya is ever enabled in production, re-verify the wire-format
   fix against a real server one more time before trusting it fully — Agent
   22's fix was proven against the same real server instance it was found
   on, but a fresh end-to-end confirmation after this fix lands is cheap
   insurance.
4. Codex has still not joined the hacp session as peer b through 5 full
   waves. Continue treating every shared file as needing a fresh
   `git status` check immediately before any edit.

## Global Architecture Compliance: YES

No second router/context/registry/safety-layer/conversation-store was
created. Laya's decision boundary remains exactly the 7 bounded
non-clinical routing questions, now backed by real measured accuracy
instead of guesses. The one below-threshold decision type
(`classify_intent`) is handled by policy (defer to clarification), not by
silently lowering the bar to make it look fine.
