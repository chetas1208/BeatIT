# Report Consistency Validator — design notes (Wave 6.5)

> Deliverable of the "Report Consistency Validator Engineer" role.
> `docs/assistant/PHYSICIAN_HELPER_HARDENING.md` SS102 does not name a specific
> doc for this deliverable (only `ReportConsistencyValidator`'s implementation
> is listed as scoped work in that file's own "Scheduled scope" SS3) — this
> file is that engineer's design note, filed under `docs/assistant/wave6.5/`
> per the task instruction, alongside whatever the other four Wave 6.5 roles
> file there.

## What this is

`python/hearttwin/assistant/report_consistency.py` extends
`safety_validator.py`'s existing output-rail gates
(`validate_numeric_claims`, `check_output_safety`) with five report-specific
consistency checks neither of those functions performs today:

1. `validate_unit_consistency` — unit-token mismatch (EF in "mL", CO in "%").
2. `detect_negation_reversal` — a source negation whose subject reappears
   asserted positively in generated text.
3. `detect_uncertainty_loss` — a source hedge whose subject reappears in
   generated text as flat fact.
4. `validate_observed_derived_simulated_boundary` — generated text's claim
   about a datum's nature vs. the bundle's real `CanonicalProvenanceKind`.
5. `detect_number_before_label_claims` — a composition-based fix for
   `validate_numeric_claims`'s own documented "45% EF" gap.

`validate_report_consistency(report_text, bundle, source_texts=None)`
combines all five plus live calls into `validate_numeric_claims` and
`check_output_safety`, returning one `ReportConsistencyResult`. Nothing in
`safety_validator.py`, `physician_brief.py`, or `schemas.py` was modified —
every reused piece is a live import.

## Per-check approach and honest limitations

### 1. Unit consistency

**Approach:** for each of the 8 metrics `safety_validator.py` already tracks
(EF/SV/CO/MAP/HR/EDV/ESV/QTc), a regex checks both label-first ("EF was
45 mL") and number-first ("45 mL EF") orderings for an explicit, recognized
unit token immediately adjacent to the number, and compares its normalized
form against an expected-unit table (`DEFAULT_EXPECTED_UNITS`).

**Limitations (real, documented in-code):**
- Only fires when an explicit unit token is present. A bare "EF is 45" is not
  checked — this is a deliberate fail-safe (no unit stated == nothing to
  contradict), not a missed case.
- The unit token must be directly adjacent to the number (same
  precision-over-recall tradeoff `safety_validator.py`'s own numeric-claim
  gate makes for its connector-word list) — "the result, expressed in
  milliliters, was 45" is not caught.
- The recognized-unit alias table is small and hand-picked (`%`, `mL`,
  `L/min`, `mmHg`, `bpm`, `ms` and their common spelled-out variants). A unit
  written in an unlisted form ("beats per minute" spelled out fully rather
  than "bpm") is silently not checked, not flagged as anything.

### 2. Negation reversal

**Approach:** a bounded cue-phrase + substring match. Source sentences are
scanned for 7 negation cues ("no evidence of", "denies", "without", "no
sign(s) of", "absence of", "ruled out", "negative for"); the words
immediately following the cue (capped at 6, further trimmed at the first
filler/verb-like word — a word-list heuristic, not real clause-boundary
detection) become the "subject." Each generated sentence containing that
subject phrase verbatim, with NO negation marker anywhere in that sentence,
is a reversal.

**Limitations (stated honestly, not hidden):** this is pattern matching, not
a negation-scope parser, matching the "bounded, not perfect" standard the
task set and the precedent `language_integrity.py`'s
`narrow_can_i_take_check` and `safety_validator.py`'s numeric-claim regex
already establish in this codebase:
- **No synonym/paraphrase matching.** "pericardial effusion" vs. "fluid
  around the heart" are different strings; the second is missed entirely.
- **No adjective robustness.** A subject captured with a leading modifier
  ("significant pericardial effusion") will not substring-match a generated
  sentence that drops the modifier ("pericardial effusion is present").
- **No double-negation handling.** "not able to rule out X" is not
  specially recognized — a generated sentence with a subject match still
  needs a single explicit negation marker in it to count as consistent, so a
  double-negated correct statement would either accidentally pass (if it
  contains a negation word) or false-flag (if it happens not to).
- **Coordinated lists** ("no chest pain or dyspnea") are split at the "and"/
  "or" stop-words, treating each item as a separate subject — a real but
  crude improvement over treating the whole coordinated phrase as one
  subject.

### 3. Uncertainty loss

**Approach:** source sentences are scanned for 13 hedge phrases ("possible",
"suspected", "cannot exclude", "unlikely", "inconclusive", etc.). For each
hedged source sentence, its content words (4+ letters, minus a stopword list
that also excludes the hedge vocabulary itself) are compared against every
generated sentence that itself contains NO hedge language; a match requires
>=2 shared content words AND >=50% overlap of the source sentence's content
words.

**Limitations:** keyword-overlap is a real, useful substitute for semantic
similarity here, not semantic similarity itself. A generated sentence that
correctly retains the hedge just elsewhere in different wording, or drops
it while discussing something the overlap threshold doesn't recognize as
"the same subject" (long paraphrases, low lexical overlap), can go either
undetected or, in principle, over-triggered on a coincidental high-overlap
unrelated sentence. The 50%-of-source / >=2-words thresholds were tuned
against the test cases in `test_report_consistency.py`, not against a larger
corpus — a real production hardening pass would want a bigger test set
before trusting these exact numbers.

### 4. Observed / derived / simulated boundary

**Approach:** `CanonicalProvenanceKind` (imported from `schemas.py`, not
redefined) is narrowed to the 3-way `{observed, derived, simulated}` split
this check covers — `MODEL_PRIOR`, `EXTERNAL_REFERENCE`, `USER_ASSERTED`
don't map onto that split without guessing, so they yield **no verdict**
(fail-safely, per the spec's explicit ask) rather than being force-mapped
into one bucket. The function takes an explicit `claimed_kind` from the
caller when available; when not, it falls back to scanning `generated_text`
for kind-language itself, but ONLY acts on that fallback when exactly one
kind is unambiguously detected in the text — ambiguous or silent text yields
no verdict.

**Limitations — the most consequential one in this file:**
`validate_report_consistency`'s own use of this check (looping over
`bundle.provenance`) is coarse: it checks the **whole report's** kind
language against each tracked provenance kind, because `DecisionSupportBundle`
(`physician_brief.py`) carries a flat `list[ProvenanceRef]`, not a
per-sentence or per-finding provenance map. A report that correctly
describes one finding as derived and a different finding as simulated will
not be checked at this granularity — and a report that happens to use both
"observed" and "simulated" language anywhere (even correctly, about two
different things) will get **no verdict at all** at the aggregate level
(demonstrated directly in `test_boundary_violation_fails_safely_on_ambiguous_text_fallback`
and exercised through the aggregate path in
`test_validate_report_consistency_flags_a_combined_bad_report`'s design,
which deliberately avoids a second "simulated"-flavored phrase elsewhere in
the same report text specifically to avoid tripping this ambiguity guard).
This is fail-safe (never a false accusation from aggregate ambiguity) at the
cost of recall. The real fix needs per-finding provenance association — see
"Sibling-file integration" below.

### 5. Number-before-label numeric gate fix

**Decision made, not silently skipped, per the task's explicit instruction:**
`safety_validator.py`'s `validate_numeric_claims` requires the metric label
before the number (`_metric_pattern`'s own docstring names this as a known
gap, trading recall for precision against bare 2-3 letter abbreviations like
"CO"/"HR" false-positiving inside unrelated text). Verified live before
writing anything:

```
validate_numeric_claims("The ventricle showed 45% EF on this study.", {"ejection_fraction_pct": 60.0})
-> valid=True, mismatches=[]   # misses a real 45-vs-60 mismatch
```

Every existing case in `test_safety_validator.py` was re-run (all pass,
unmodified) before and after writing `report_consistency.py`, confirming
nothing there needed to change. **Fixed via composition, not by editing the
owned file:** `detect_number_before_label_claims` finds the reversed-order
phrasing with its own regex (a deliberate, documented, small duplication of
metric label synonyms — not of the comparison logic), rewrites the match
into label-first order ("EF is 45"), and calls the REAL
`validate_numeric_claims` on that synthetic snippet — so the actual
value-vs-canonical comparison and +/-0.5 tolerance are never reimplemented,
only the label ordering is worked around.

**Limitation:** the reversed-order pattern requires tight adjacency (number,
then only "%"/"percent"/"of", then the label) so it deliberately does not
match a unit word or other filler between the number and the label ("48 mL
EF" is caught by `validate_unit_consistency`'s own reversed-order pattern,
not by this numeric check — the two checks are complementary, not
overlapping, by design).

## Fail-safely on incomplete data (spec's own requirement)

`ReportConsistencyResult.skipped_checks` is a non-empty explanation list,
not a silent gap, whenever:
- The bundle exposes no numeric metric:value pairs at all (numeric checks
  then run against an empty canonical payload, meaning every claimed number
  is reported "unsupported" — `validate_numeric_claims`'s own designed
  behavior, not a new failure mode).
- `source_texts` is `None` (negation/uncertainty checks are inherently
  relative and cannot run against `report_text` alone).
- The bundle carries any provenance at all (the boundary check's aggregate
  granularity limitation above is always surfaced, not just on failure).

This mirrors `DecisionSupportBundle`'s own precedent
(`missing_evidence`/`conflicts` being intentionally empty with a stated
reason, not silently read as "verified clean").

## Sibling-file integration (case_context.py / report_personalization.py)

**Status check performed twice, as instructed:** at the start of this task,
`python/hearttwin/assistant/case_context.py` and
`python/hearttwin/assistant/report_personalization.py` did **not** exist
(`git status` and `ls` both confirmed it) — so this validator was built
against `DecisionSupportBundle` alone, per the task's own fallback
instruction. Both files landed in the workspace (from the concurrent Case
Context Hardening / Report Personalization engineers) before this task
finished. They were **not** integrated into `report_consistency.py` in this
pass — that would mean building against a moving, concurrently-written
contract mid-task, and this task's constraints explicitly forbid modifying
those two files or expanding scope beyond the three named new files. Real,
concrete extension points identified for a follow-up integration pass:

- `report_personalization.py`'s `DeltaFinding` (fields: `metric_id`,
  `prior_value`, `current_value`, `change_kind`) is exactly the structured
  data a real "historical/current value confusion" check needs — e.g.
  flagging generated text that states a `DeltaFinding.prior_value` as if it
  were the current one, or vice versa. Today, `detect_negation_reversal`/
  `detect_uncertainty_loss` only compare `report_text` against caller-
  supplied `source_texts` strings; they have no concept of "prior snapshot"
  vs. "current snapshot" at all.
- `case_context.py`'s `resolve_historical_reference` /
  `ResolvedReference.resolution_kind` (and `CaseContext.snapshot_history`)
  is the real, already-tracked signal for whether a phrase like "before" or
  "now" resolved to a specific prior snapshot — a future
  `detect_historical_current_confusion` check could take a
  `list[ResolvedReference]` (or the raw `CaseContext`) instead of trying to
  infer temporal confusion from text pattern-matching alone, which would be
  both more accurate and better-grounded than adding yet another regex
  heuristic to this file.
- Neither integration was attempted here because it would require either
  modifying those two owned files (out of scope) or importing from them
  while their contracts were still being written concurrently in the same
  wave (risk of building against an interface that changes under this task
  before the wave integrates) — a real, stated tradeoff, not an oversight.

## Test results

`python -m pytest python/hearttwin/tests/test_report_consistency.py -v`:

```
25 passed in 2.99s
```

25 tests: 4 unit-consistency (2 genuine mismatches, 1 clean pass, 1
no-unit-stated fail-safe pass), 4 negation-reversal (2 genuine reversals via
different cues, 2 false-positive-avoidance), 4 uncertainty-loss (2 genuine
losses, 2 false-positive-avoidance), 5 observed/derived/simulated boundary
(1 genuine violation via explicit claim, 1 via text fallback, 1 clean pass,
2 fail-safe "no verdict" cases), 4 number-before-label (1 documenting the
existing gate's gap directly, 1 catching it, 1 clean pass, 1 sentence-
boundary false-positive-avoidance), 4 aggregate `validate_report_consistency`
(1 combined-failure case, 1 full clean pass across every check, 1
skipped-checks-on-empty-bundle, 1 source-texts-driven negation detection).

Full repo suite after adding these files (confirms zero regressions and that
nothing outside the three new files was touched):

```
python -m pytest python/hearttwin/tests -q
1258 passed, 5 skipped, 6 xfailed, 494 warnings in 12.93s
```

(`test_safety_validator.py`, `test_physician_brief.py`, and
`test_language_integrity.py` specifically re-verified passing unmodified,
since this module imports live from all three.)
