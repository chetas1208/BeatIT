# Clinical-Language Integrity Review + Guard (Wave 3, Agent 15)

> Read first: `AGENTS.md` SS1.4, `GLOBAL_ARCHITECTURE.md`'s "Output rail" /
> "Decision support object (no `recommended_treatment` field, ever)" sections,
> `docs/assistant/wave2/safety-validation.md`.

Implementation: `python/hearttwin/assistant/language_integrity.py`.
Tests: `python/hearttwin/tests/test_language_integrity.py` (19 tests, all
passing; full suite 929 passed / 1 skipped after this change — nothing
existing was touched).

This is an audit of Wave 2's `safety-validation.md` judgment calls, plus a
new, narrower style/tone guard that composes with (does not replace)
`safety_validator.py`'s `check_output_safety`.

One correction to the task brief: `GLOBAL_ARCHITECTURE.md` does not contain a
section literally titled "HIGH-STAKES DECISION RULE" with the exact quoted
sentences ("never 'Do X,' prefer 'The available evidence supports these
considerations...'"). The closest real content is the "Output rail"
guardrail bullet (`unsupported recommendations`), the T3 tool-safety-level
definition (`prescribe medication ... NOT ordinary BeatIT tools ... Never
executed autonomously`), and the "Decision support object (no
`recommended_treatment` field, ever)" section, which states "Laya **cannot**
decide which therapy a patient should receive." The brief's quoted phrasing
is a paraphrase of that intent, not a verbatim quote — noted here rather than
silently treated as a direct citation.

## Part A — Audit of Wave 2's flagged judgment calls

Wave 2's `safety-validation.md` SS"Judgment calls flagged for human review"
lists four items. Verdict on each:

### 1. Emergency supplement (acute-symptom + self-harm phrasing)

Patterns added: `"can't breathe"`, `"passed out"`, `"fainted"`,
`"collapsed"`, `"severe/crushing chest pain"`, plus self-harm phrasing
(`"suicidal"`, `"want to end my life"`, `"self-harm"`).

**Verdict: KEEP AS-IS.**

These are strictly additive to a category that already blocks (emergency),
and the failure mode of a false positive here is "DualBeat declines and
points to real emergency services" — not a functional regression, not a
blocked legitimate cardiac-simulation question. None of the added patterns
plausibly collide with DualBeat's actual domain vocabulary (simulation,
ensembles, PV loops, twins) the way "can I take" does. Self-harm phrasing
belongs in scope: a cardiac digital-twin app absolutely should not attempt to
engage with a self-harm disclosure instead of deferring to real emergency
resources, regardless of how narrow the app's stated purpose is. I checked
this against `python/hearttwin/agents/intake_agent.py:289-350` myself
(required reading item 4) and confirm Wave 2's claim: none of these phrases
match any of intake_agent.py's own emergency regexes today, so this is real,
correctly-scoped additive coverage, not a restatement.

### 2. Treatment supplement — `"can I take"`

**Verdict: NEEDS NARROWING — implemented.**

Wave 2's own agent flagged this as "the single most likely false-positive
source in this file," and the concern is legitimate: DualBeat's actual
domain vocabulary uses "take" non-medically all the time — "take this
simulation further," "take a closer look at the PV loop," "take the median
twin from this ensemble." A bare `\bcan i take\b` substring match blocks all
of these. Unlike judgment call #1, this is a case where the false-positive
surface directly overlaps DualBeat's own core vocabulary (simulations,
ensembles, exploration language), not just generic conversation — a demo
presenter asking "can I take this recovery scenario further?" getting hard-
blocked as a "treatment request" is a real, plausible, embarrassing failure
mode in exactly the kind of live demo AGENTS.md SS0 says this whole
repository is built backwards from.

Implemented as `narrow_can_i_take_check(text: str) -> bool` in
`language_integrity.py`: returns `True` only when `"can i take"` is followed
(within an 8-word window) by a medication/dose-adjacent word — a small fixed
list of common OTC/prescription drug names and generic medication nouns
(`medication`, `dose`, `dosage`, `pill`, `over-the-counter`, ...), or a
dose-shaped token (`\d+\s*(mg|mcg|ml|units)`). Verified against the exact
three benign phrasings Wave 2 and this task cite, plus three
medication-adjacent positives, in
`test_language_integrity.py::test_can_i_take_*` (all passing — see Test
output below).

**Integration note (not yet done, deliberately, per file-ownership
constraints):** `safety_validator.py`'s `_SUPPLEMENTAL_TREATMENT_PATTERNS`
(line ~141) currently has a bare `r"\bcan i take\b"` entry. A future
integration step should remove that literal from the regex list and instead
have `_supplemental_category` call `narrow_can_i_take_check(normalized)` as
a separate boolean check ORed into the treatment-category decision alongside
the remaining `_contains_any(normalized, _SUPPLEMENTAL_TREATMENT_PATTERNS)`
check (with `"can i take"` removed from that list, since it would otherwise
double-cover the bare-substring case that `narrow_can_i_take_check` is
supposed to replace, not just supplement). This module does not implement
that edit itself since `safety_validator.py` is Wave 2's owned file per this
task's constraints; it only builds and proves out the replacement logic in
an additive layer.

### 3. Treatment supplement — bare `"pills?"`, `"skip/double a dose"`, `"is it safe to take"`, `"over-the-counter"`

**Verdict: KEEP AS-IS.**

These don't share "can I take"'s problem: none of them are plausible
sentence fragments in DualBeat's own simulation/twin/ensemble vocabulary.
"Is it safe to take [this medication]" and "skip a dose" are unambiguously
medication-shaped phrasings with essentially no legitimate non-medical
reading in this app's context. Bare `pills?` is the closest thing to a risk
(e.g. "the pillar of this analysis" would not match due to the `\b` word
boundary, so that specific false-positive doesn't actually occur), and I
could not construct a plausible cardiac-twin-context sentence containing
"pill(s)" that isn't itself medication-adjacent. No change proposed.

### 4. Diagnosis supplement — `"what's wrong with me"`, `"am I sick"`, `"what condition do I have"`, `"do you think I have"`

**Verdict: KEEP AS-IS**, matching Wave 2's own "no concerns flagged" call.

I independently tried to construct DualBeat-vocabulary false positives for
each phrase (e.g. anything in the "twin," "simulation," "ensemble," "PV
loop," "report" register) and could not find one — these are all
first-person distress/diagnosis-seeking phrasings with no natural reading in
this app's actual query surface. Agreeing with Wave 2 here is itself a
finding worth stating explicitly per this task's instruction not to
manufacture problems: this judgment call was fine as shipped.

### 5. `requires_tool_grounding` scope (five intents, not "every non-blocked intent")

This one wasn't phrased as uncertain in Wave 2's writeup ("no concerns
flagged" isn't even said — it's presented as a settled design choice), but
since it's the last judgment call in that section:

**Verdict: KEEP AS-IS.**

Defaulting every non-blocked intent (including `unclear`) to
tool-grounded-required would force intents with no real deterministic tool
behind them through a grounding gate they structurally cannot satisfy,
producing spurious `INSUFFICIENT_EVIDENCE` results for ordinary
conversation. The five-intent allowlist is conservative in the correct
direction (under-claim tool-backing rather than over-claim it), which is the
safer failure mode for a provenance gate.

### 6. Numeric claim gate gaps (connector-word requirement, no unit-mismatch detection, no de-dup across phrasing, limited QTc alias coverage)

Not phrased as "flagged for human review" in the same section, but called
out as "known gaps" later in the same document. These are out of this
task's actual scope (Part A only asks for verdicts on the "Judgment calls
flagged for human review" list, and this is a numeric-fidelity gate, not a
clinical-language/tone question), so no verdict is rendered here — noted for
completeness so a reader of this doc doesn't assume they were silently
reviewed and cleared.

## Part A (continued) — scan of other Wave 3 agents' generated text

At the time of this review, `python/hearttwin/assistant/` contained (beyond
Wave 2's `safety_validator.py` and pre-existing `router.py`, `schemas.py`,
`tool_registry.py`, `model_pool.py`, `laya_adapter.py`) two files from
other, concurrently-running Wave 3 agents: `physician_tools.py` and
`provenance_mapping.py`. Neither `physician_brief.py` nor `orchestrator.py`
(the files this task's brief anticipated from Agents 14/11) existed in
`python/hearttwin/assistant/` as of this review — noting this explicitly per
the task's instruction to state what wasn't reviewable yet. (A separate,
pre-existing `python/hearttwin/orchestrator.py` and
`python/hearttwin/careguard/orchestrator.py` do exist, but neither is the
assistant-package orchestrator the brief describes, and reviewing them was
out of this task's stated scope — the assistant package specifically.)

Both `physician_tools.py` and `provenance_mapping.py` were scanned two ways:
`scan_assistant_module_for_violations()` (see run output below) and a manual
`grep -i` pass for "you should", "i recommend", "the patient needs", "you
must", "start taking", "stop taking", "your diagnosis", "this indicates you
have". **Both checks found nothing** — zero automated flags, zero grep hits.

## Part B — the guard: design summary

`python/hearttwin/assistant/language_integrity.py` (new file) provides:

- `scan_for_prescriptive_language(text) -> LanguageIntegrityResult` — three
  pattern families (`imperative_treatment`, `clinical_authority_claim`,
  `unsupported_diagnostic_certainty`), each independently checked; the
  diagnostic-certainty family is sentence-scoped with a hedge-word guard
  (`may`, `might`, `consistent with`, `evidence supports`, `insufficient`,
  ...) so BeatIT's required hedged house style never trips it. `category`
  picks by severity order (imperative > authority > diagnostic-certainty)
  when a text somehow trips more than one family; `matched_patterns` reports
  every hit regardless.
- `narrow_can_i_take_check(text) -> bool` — the "can I take" fix described
  in Part A SS2, plus the integration note for folding it into
  `safety_validator.py` later.
- `scan_assistant_module_for_violations(root_dir="python/hearttwin/assistant") -> list[tuple[str, str]]`
  — walks `.py` files via `ast`, extracts string-literal and f-string
  content that looks like end-user prose (`_looks_like_prose`: length >= 8,
  contains a space, contains no backslash — the last condition is what keeps
  this module's own regex-pattern source strings from self-flagging without
  needing a special case for every pattern), and runs
  `scan_for_prescriptive_language` on each. It explicitly skips its own
  source file and any `test_*.py` file. This is a heuristic, not a real
  static analyzer — documented limitations are in the function's own
  docstring in `language_integrity.py` (an f-string's interpolated
  `{expr}` segments are included verbatim in the scanned text since
  `ast.get_source_segment` returns the original source for a `JoinedStr`;
  not observed to cause any false positive on the current codebase, but
  noted as a real limitation of the approach).

This module does not import from or modify `safety_validator.py`. It is
meant to run in addition to `check_output_safety`, not instead of it — a
future integration step could call both from whatever unifies them, but that
wiring decision belongs to whichever wave owns the actual pipeline
assembly, not this audit task.

## Actual `scan_assistant_module_for_violations()` output (real codebase, pasted verbatim)

Run against `python/hearttwin/assistant/` as it existed at the end of this
review (includes `router.py`, `schemas.py`, `tool_registry.py`,
`model_pool.py`, `laya_adapter.py`, `safety_validator.py`,
`physician_tools.py`, `provenance_mapping.py` — `language_integrity.py`
itself and `test_*.py` are excluded by design):

```
$ python3 -c "
from python.hearttwin.assistant.language_integrity import scan_assistant_module_for_violations
result = scan_assistant_module_for_violations()
print('violations found:', len(result))
for r in result:
    print(r)
"
violations found: 0
```

Zero violations. This is a genuinely good sign, stated honestly rather than
tuned to produce it: the scanner was written and its patterns finalized
*before* this final run (the test suite below locks in the same patterns
against synthetic positive/negative examples), and it was run against the
real files as-is with no adjustment afterward to suppress a hit.

## Test output (actual, pasted)

```
$ python -m pytest python/hearttwin/tests/test_language_integrity.py -v
============================= test session starts ==============================
platform linux -- Python 3.13.12, pytest-9.0.3, pluggy-1.5.0
collected 19 items

python/hearttwin/tests/test_language_integrity.py::test_flags_imperative_treatment_take_with_dose PASSED [  5%]
python/hearttwin/tests/test_language_integrity.py::test_flags_imperative_treatment_stop_medication PASSED [ 10%]
python/hearttwin/tests/test_language_integrity.py::test_flags_clinical_authority_claim PASSED [ 15%]
python/hearttwin/tests/test_language_integrity.py::test_flags_you_must_as_authority_claim PASSED [ 21%]
python/hearttwin/tests/test_language_integrity.py::test_flags_unsupported_diagnostic_certainty PASSED [ 26%]
python/hearttwin/tests/test_language_integrity.py::test_flags_you_have_condition_without_hedge PASSED [ 31%]
python/hearttwin/tests/test_language_integrity.py::test_does_not_flag_available_evidence_supports_phrasing PASSED [ 36%]
python/hearttwin/tests/test_language_integrity.py::test_does_not_flag_simulation_produces_phrasing PASSED [ 42%]
python/hearttwin/tests/test_language_integrity.py::test_does_not_flag_evidence_insufficient_phrasing PASSED [ 47%]
python/hearttwin/tests/test_language_integrity.py::test_does_not_flag_hedged_diagnostic_language PASSED [ 52%]
python/hearttwin/tests/test_language_integrity.py::test_does_not_flag_you_have_non_medical_sense PASSED [ 57%]
python/hearttwin/tests/test_language_integrity.py::test_can_i_take_simulation_further_is_not_flagged PASSED [ 63%]
python/hearttwin/tests/test_language_integrity.py::test_can_i_take_closer_look_is_not_flagged PASSED [ 68%]
python/hearttwin/tests/test_language_integrity.py::test_can_i_take_median_twin_is_not_flagged PASSED [ 73%]
python/hearttwin/tests/test_language_integrity.py::test_can_i_take_ibuprofen_is_flagged PASSED [ 78%]
python/hearttwin/tests/test_language_integrity.py::test_can_i_take_with_dose_shape_is_flagged PASSED [ 84%]
python/hearttwin/tests/test_language_integrity.py::test_can_i_take_over_the_counter_is_flagged PASSED [ 89%]
python/hearttwin/tests/test_language_integrity.py::test_can_i_take_with_no_med_word_at_all_is_not_flagged PASSED [ 94%]
python/hearttwin/tests/test_language_integrity.py::test_scan_assistant_module_returns_a_result_for_real_codebase PASSED [100%]

============================== 19 passed in 0.08s ==============================
```

Full repo suite re-run after adding these files (`pnpm test:py` equivalent,
`python -m pytest python/hearttwin/tests`): **929 passed, 1 skipped** —
matches Wave 2's own reported baseline growth pattern (they reported 899
passed/1 skipped after their addition; this task added 19 more without
touching any existing test), confirming nothing existing regressed.

## Files touched

New only, per this task's file-ownership constraint:

- `python/hearttwin/assistant/language_integrity.py`
- `python/hearttwin/tests/test_language_integrity.py`
- `docs/assistant/wave3/clinical-language-integrity.md` (this file)

`python/hearttwin/assistant/safety_validator.py` was read only, never
modified. No file under `python/hearttwin/tools/cardiac_state.py`,
`hemodynamics.py`, `recovery_sim.py`, `python/hearttwin/shadow_trial_*.py`,
`api.py`, `copilot.py`, or `careguard/*` was touched.
