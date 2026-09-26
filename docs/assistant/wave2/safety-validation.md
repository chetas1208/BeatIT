# Safety + Numerical Validation (Wave 2, Agent 10)

> Read first: `AGENTS.md` SS1.4, `GLOBAL_ARCHITECTURE.md` "GUARDRAIL LAYERS" /
> "NUMERICAL CLAIM GATE", `PHYSICIAN_WORKFLOWS.md` "Existing Safety
> Guardrails", `CHAT_SURFACE_AUDIT.md`, `WAVE_1_HANDOFF.md`.

Implementation: `python/hearttwin/assistant/safety_validator.py`.
Tests: `python/hearttwin/tests/test_safety_validator.py` (17 tests, all
passing; full suite 899 passed / 1 skipped after this change — nothing
existing was touched).

This module is deterministic, pre/post validation glue for the *future*
unified assistant. It does not replace `intake_agent.py`, `copilot.py`, or
`careguard/copilot_agent.py` — none of those three files were modified. It
unions their existing safety behavior so a future single conversation
pipeline has one call surface with at-least-as-much coverage as today's two
independent surfaces combined.

## 1. How the two output blocklists were unioned

**Sources (both real, both cited in `CHAT_SURFACE_AUDIT.md` /
`WAVE_1_HANDOFF.md` as the "two independent safety blocklists"):**

1. `python/hearttwin/copilot.py:59-74` — `_OUTPUT_RED_FLAGS`, a 14-entry
   tuple of clinical-advice phrases (`"i recommend you take"`, `"prescribe"`,
   `"your diagnosis is"`, `"milligrams"`, ...). It is only one of three
   layers `copilot.py`'s own `_check_output_safety`
   (`copilot.py:418-448`) runs on every `answer_case_question` response:
   - layer 1: `safety.py`'s `check_request_safety` / `_BLOCKED_PATTERNS`
     (`python/hearttwin/safety.py:24-36`) — a 9-pattern regex matcher for
     diagnosis/prescription/treatment/medication/emergency/"you have"/
     "healed"/"take this"/"clinical" language, applied to the model output
     after `strip_allowed_safety_phrases` removes the approved disclaimer
     wording.
   - layer 2: the 14-entry `_OUTPUT_RED_FLAGS` phrase list itself.
   - layer 3: `safety.py`'s `validate_simulation_outputs`
     (`python/hearttwin/safety.py:100-114`) — flags raw `"diagnosis"`/
     `"treatment"`/`"healed"`/`"prescribe"` vocabulary leaking into output text.
2. `python/hearttwin/careguard/copilot_agent.py:24-25` — `_BLOCK`, an
   8-entry tuple written independently for the CareGuard analysis surface
   (`"what should i take"`, `"what dose"`, `"diagnose me"`, `"am i going
   to"`, ...). It has never been cross-checked against `copilot.py`'s list;
   several of its phrasings (`"how many mg"`, `"should i stop"`, `"am i
   going to"`) are not covered by any of copilot.py's three layers.

**Decision: live import, not replicated-with-citation.** I confirmed both
`_OUTPUT_RED_FLAGS` and `_BLOCK` import cleanly from `safety_validator.py`
with no circular dependency (`copilot.py` and `careguard/copilot_agent.py`
have no import path back into `python/hearttwin/assistant/`), and neither
module has import-time side effects that would make importing them from a
third module unsafe (no network/DB calls at import time; `copilotkit` and
CareGuard's Redis/Anthropic clients are only touched inside function bodies).
Given that, the task's own instruction to "prefer live import over
hardcoded duplication if at all possible" applies cleanly here — there was
no practical obstacle forcing a copy.

`check_output_safety()` in `safety_validator.py` therefore runs **four**
checks on every candidate output text, strictly reproducing all three of
copilot.py's real layers plus CareGuard's list, and blocks if *any* one
matches:

| Layer | Source (live import) |
|---|---|
| `_OUTPUT_RED_FLAGS` phrase scan | `python/hearttwin/copilot.py:59-74` |
| `check_request_safety` regex scan | `python/hearttwin/safety.py:24-36,45-54` |
| `validate_simulation_outputs` vocab scan | `python/hearttwin/safety.py:100-114` |
| `_BLOCK` phrase scan | `python/hearttwin/careguard/copilot_agent.py:24-25` |

This is a strict superset of both original systems' real behavior (not just
their two term lists) — a text that would pass CareGuard's copilot but fail
copilot.py's `_check_output_safety`, or vice versa, is blocked here either
way. Two tests
(`test_check_output_safety_catches_copilot_red_flag_term`,
`test_check_output_safety_catches_careguard_block_term`) each construct a
case that trips one source's list but not the other's, proving the union
actually covers both rather than one silently subsuming the other by
accident.

**Anti-drift tripwire.** Because both lists are imported live, growth in
either source is automatically picked up by the union with zero code
changes here — but a human should still know when the underlying behavior
changed shape (e.g. if `_BLOCK` were replaced with a regex list instead of
plain substrings, live-importing it as strings would silently stop working).
`test_check_output_safety_source_lists_have_not_silently_grown` snapshots
both lists' current lengths (14 and 8) and fails with an explicit pointer
back to this file and to `check_output_safety`'s docstring if either changes
— it is a deliberate, loud "please re-read this design note" trip, not a
correctness assertion in itself.

## 2. Pre-request classification: reuse, not reimplementation

`classify_request_safety()` calls `_classify_intent_with_rules()`
(`python/hearttwin/agents/intake_agent.py:284-392`) directly as its base
decision — the exact regex patterns for emergency/treatment/diagnosis intent
are never copied. Because this module never invokes the OpenAI intent
classifier (`_classify_intent_with_openai`) at all, `_merge_decisions`'s
guarantee that "a rule-blocked decision is never softened by the model"
(`intake_agent.py:395-413`) is trivially preserved — there is no model in
this path to soften anything.

**Supplemental patterns are additive only.** They run *after* the rule
decision, *only* when the rule decision did not already block, and can only
turn `blocked=False` into `blocked=True` — never the reverse. This was
checked concretely: none of the six supplemental-pattern test phrases
(`"I have crushing chest pain right now and I can't breathe."`, `"What pill
should I take for this?"`, `"What's wrong with me?"`) match any of
intake_agent.py's own regexes (verified by reading `intake_agent.py:289-350`
pattern-by-pattern against each phrase before writing the test), so these
tests prove genuinely new coverage, not a restatement of an existing hit.

### Judgment calls flagged for human review (err-stricter per the brief)

- **Emergency supplement.** `intake_agent.py`'s emergency block requires an
  explicit `"heart attack"` / `"emergency room"` / `"911"` / `"ambulance"` /
  `"triage"` phrase — a bare `"I have crushing chest pain right now, I can't
  breathe"` does **not** match any of its patterns today. I added
  acute-symptom phrasing (`"can't breathe"`, `"passed out"`, `"fainted"`,
  `"collapsed"`, `"severe/crushing chest pain"`) and self-harm phrasing
  (`"suicidal"`, `"want to end my life"`, `"self-harm"`) to the emergency
  category. This is a real behavior change relative to what exists today
  (nothing changes in `intake_agent.py` itself, but a request that flows
  through this new validator will be blocked where the bare intake agent
  would not have blocked it) — flagged explicitly per the task's "err toward
  stricter... and say so explicitly" instruction. A human should confirm
  self-harm phrasing belongs in a cardiac-twin app's safety scope at all (I
  judged yes, since blocking is strictly safer than not, and the cost of a
  false positive here is just "DualBeat declines and suggests real
  emergency services," not a functional regression).
- **Treatment supplement.** Added bare `"pill(s)"`, `"skip/double a dose"`,
  `"is it safe to take"`, `"can I take"`, `"over-the-counter"`. Risk: `"can I
  take"` is fairly broad (e.g. "can I take this simulation further?" is a
  plausible benign phrasing that would false-positive-block). I judged this
  acceptable under "err toward stricter" for a hackathon-grade validator,
  but flag it explicitly as the single most likely false-positive source in
  this file and a good first thing to narrow if it causes demo friction.
- **Diagnosis supplement.** Added `"what's wrong with me"`, `"am I sick"`,
  `"what condition do I have"`, `"do you think I have"`. Lower false-positive
  risk than the treatment supplement; no concerns flagged.
- **`requires_tool_grounding`.** This field does not exist in
  `intake_agent.py` at all — it is new classification this module adds to
  feed the NUMERICAL CLAIM GATE / provenance-gate design in
  `GLOBAL_ARCHITECTURE.md` ("if a deterministic tool can answer the factual
  part, use it"). I scoped it conservatively to the five intents with
  confirmed real deterministic backing per `PHYSICIAN_WORKFLOWS.md`
  (`physiology_explanation`, `operation_simulation`, `recovery_simulation`,
  `educational_simulation`, `report_structuring`) rather than defaulting
  every non-blocked intent to `True`, to avoid forcing intents with no real
  tool behind them (e.g. `unclear`) through a grounding requirement they
  can't satisfy.

## 3. Numeric claim gate: approach and known gaps

`validate_numeric_claims(generated_text, canonical_payload)` extracts claims
for 8 metrics (EF, SV, CO, MAP, HR, EDV, ESV, QTc) via per-metric regex, then
diffs each against `canonical_payload` (matched through a small alias table
covering both `copilot.py`'s `_build_state_snapshot` naming convention —
`ejection_fraction_pct`, `stroke_volume_ml`, etc. — and bare abbreviations).
A metric mentioned in text but absent from `canonical_payload` entirely is
flagged as an unsupported claim (`canonical_value=None`), per
`GLOBAL_ARCHITECTURE.md`'s "Mismatch -> reject/regenerate/fallback. No
exceptions." Tolerance is a flat ±0.5 across all metrics (task spec's
"rounding/±0.5" example), on the reasoning that this gate exists to catch
fabrication, not to police the pipeline's own rounding precision.

**Known gaps (regex-inherent, flagged for human review):**

- **Requires a connector word between metric name and number.** Patterns
  match `"EF is 45%"` / `"EF of 45"` / `"EF: 45"` / `"EF ~45"` but **not**
  `"EF, 45%, was recorded"` or `"45% EF"` (number before the metric name).
  This was a deliberate precision-over-recall tradeoff: 2-3 letter
  abbreviations (`CO`, `HR`, `SV`, `MAP`) are common enough as ordinary
  English/acronym fragments that matching a bare number anywhere near them
  would create false positives (e.g. "CO-morbidities" contains "CO"). A
  human should confirm which failure mode is worse for the real generation
  prompts once System-2 model output is observed — if models reliably put
  the number before the label, this gate will under-catch.
- **No unit-mismatch detection.** `"stroke volume is 70"` matches the SV
  pattern regardless of whether 70 means mL or something else — the regex
  captures the number, not the unit, and unit words are optional/ignored in
  matching. A claim in the wrong unit but numerically close to a different
  field's canonical value could pass by coincidence.
- **First-claim-per-position, not de-duplicated across phrasing.** If the
  same metric is mentioned twice with two different numbers (e.g. an EF
  quoted once at intake and once after a scenario), both are checked
  independently against the *same* flat `canonical_payload` — this module
  has no concept of "which snapshot in time" a given sentence refers to.
  That's a caller-side concern (the future assistant must pass the right
  `canonical_payload` per turn); flagged here so it isn't silently assumed
  solved.
- **QTc alias `"QTC"` vs `"qtc"` vs `"corrected QT"`** — covered, but any
  further clinical abbreviation drift (e.g. `"QTc interval"`) is untested
  beyond the alias list actually used in `copilot.py`'s snapshot builder.

## 4. `REQUIRED_SAFETY_DISCLAIMER`

Set to `python/hearttwin/safety.py`'s `DISCLAIMER` verbatim (imported, not
retyped) — this is the exact string `copilot.py`'s `_with_disclaimer`
(`copilot.py:96-98`) stamps onto every action payload's `safety_disclaimer`
key, matching AGENTS.md SS1.4's "every API response keeps the
`safety_disclaimer`." CareGuard uses a separate, shorter string
(`"Clinical decision support draft. Clinician review required."`,
`careguard/copilot_agent.py:22`) scoped to its own medication-safety domain
— `WAVE_1_HANDOFF.md` item 4 already flags reconciling the two disclaimer
strings as a later-wave decision, so this module intentionally does not
invent a merged disclaimer; it only guarantees the primary DualBeat string
is available under one name for whatever wires the unified pipeline next.

## 5. Files touched

New only, per the task's file-ownership constraint:

- `python/hearttwin/assistant/safety_validator.py`
- `python/hearttwin/tests/test_safety_validator.py`
- `docs/assistant/wave2/safety-validation.md` (this file)

Nothing under `python/hearttwin/agents/intake_agent.py`,
`python/hearttwin/copilot.py`,
`python/hearttwin/careguard/copilot_agent.py`,
`python/hearttwin/tools/cardiac_state.py`/`hemodynamics.py`/`recovery_sim.py`,
or any `python/hearttwin/shadow_trial_*.py` file was modified.
