# Decision Fixtures — Wave 5, Agent 21 ("Decision Fixture Engineer")

> Read first: `python/hearttwin/assistant/laya_adapter.py`,
> `python/hearttwin/tests/test_laya_adapter.py`, `docs/assistant/LAYA_RESEARCH.md`
> ("Calibration Campaign Prerequisites"), `docs/assistant/wave5/laya-specialization.md`
> (Agent 23's 3 unconfirmed fallback-ordering hypotheses), `docs/assistant/WAVE_5_HANDOFF.md`.

**Status: this is a retry.** The prior attempt at this exact task was
interrupted by an account rate limit before writing any fixture data —
`python/hearttwin/tests/fixtures/__init__.py` existed as an empty package
marker and nothing else. This document describes what actually landed this
time.

## What this delivers

1. `python/hearttwin/tests/fixtures/laya_decision_fixtures.py` — **160**
   labeled fixtures across the 7 real `LayaAdapter` decision methods, plus
   `FixtureCase`, `load_fixtures(decision_name)`, `load_all_fixtures()`,
   `valid_labels(decision_name)`, `total_fixture_count()`, `DECISION_NAMES`,
   and `TOOL_FAMILY_OPTIONS`.
2. `python/hearttwin/tests/test_laya_decision_fixtures.py` — 42 sanity tests
   (loading, minimum counts, label validity, category validity, label-space
   coverage, immutability of returned lists).
3. This document.

No existing file was modified. `laya_adapter.py` was read only, never
touched, per this task's constraints and AGENTS.md §7 ("stay in your lane").

## Exact fixture counts per decision type

| Decision | Count | Choice options / bool |
|---|---:|---|
| `classify_intent` | 29 | 11 `ExecutionClass` values, all 11 covered by >=1 fixture |
| `select_tool_family` | 30 | 8 tool-family values (`TWIN`/`EVIDENCE`/`PHYSIOLOGY`/`EXPERIMENT`/`COMPARE`/`UNCERTAINTY`/`REPORT`/`NONE`), all 8 covered |
| `needs_evidence_retrieval` | 20 | 10 True / 10 False |
| `needs_simulation` | 20 | 10 True / 10 False |
| `needs_clarification` | 21 | 11 True / 10 False |
| `needs_physician_review_framing` | 20 | 10 True / 10 False |
| `is_complex_reasoning_required` | 20 | 10 True / 10 False |
| **Total** | **160** | exceeds the task's 105–140+ floor |

`test_every_label_option_is_covered_by_at_least_one_fixture` in the test
file enforces the "every option covered" claim above as a real assertion,
not just a manual count.

## Data format and loader API for other Wave 5 agents

```python
from python.hearttwin.tests.fixtures.laya_decision_fixtures import (
    DECISION_NAMES,       # the 7 real LayaAdapter method names
    TOOL_FAMILY_OPTIONS,  # the 8 select_tool_family values, kept in sync via a test
    FixtureCase,           # dataclass: text, expected, context, category, notes
    load_fixtures,         # (decision_name: str) -> list[FixtureCase]
    load_all_fixtures,     # () -> dict[str, list[FixtureCase]]
    valid_labels,          # (decision_name: str) -> set — the real label space
    total_fixture_count,   # () -> int
)

for case in load_fixtures("classify_intent"):
    result = await adapter.classify_intent(case.text, case.context)
    is_correct = result.chosen == case.expected  # accuracy accumulation goes here
```

`FixtureCase` fields:

- `text: str` — the input request.
- `expected: str | bool` — ground truth. A real `ExecutionClass` value for
  `classify_intent`, a real `TOOL_FAMILY_OPTIONS` value for
  `select_tool_family`, `True`/`False` for the other 5.
- `context: dict[str, Any]` — mirrors the `context` param `LayaAdapter`
  methods accept (`component_id`, `snapshot_id`, `ensemble_id`,
  `scenario_id`, `pair_id`, `patient_id`, `audience`). Required to
  meaningfully exercise `needs_clarification` (referent resolution) and
  `needs_physician_review_framing` (`audience` short-circuit).
- `category: str` — one of `clear | ambiguous | jargon | shorthand |
  multi_intent | nonsense` (see below).
- `notes: str` — the labeling rationale, always populated for `ambiguous`
  cases; explains the specific judgment call or the specific hypothesized
  fallback disagreement.

This is a plain Python module (not JSON) by design: the repo's existing
fixture convention (`fixtures/hearttwin/*.json` + `conftest.py` loaders) fits
data-only fixtures well, but this set's whole point is close, per-example
reasoning about *why* a label is what it is, especially for the deliberately
hard cases — that reasoning belongs next to the data as a `notes` string a
JSON file would either have to duplicate awkwardly or drop. A future agent
wanting a JSON export can trivially get one via
`json.dumps({k: [vars(c) for c in v] for k, v in load_all_fixtures().items()})`.

## Category definitions

- **clear** — an unambiguous example a domain-agnostic reader would label
  the same way without hesitation.
- **ambiguous** — a deliberately hard or near-tie case; always carries a
  `notes` explanation of the judgment call and, where applicable, the
  specific reason the current fallback heuristic is expected to disagree.
- **jargon** — realistic physician/clinical-register phrasing (e.g.
  "provenance", "echo-derived", "interstitial fibrosis") rather than
  layperson phrasing, per `docs/assistant/wave3/clinical-language-integrity.md`'s
  emphasis on testing against real clinical register, not just plain English.
- **shorthand** — casual/abbreviated chat input (lowercase, missing
  punctuation, "pls", "whats the ef") — tests whether a decision layer is
  brittle to exact keyword casing/phrasing.
- **multi_intent** — text that plausibly satisfies more than one label at
  once (used for the `needs_simulation` + `needs_evidence_retrieval`
  both-True case below; not heavily used elsewhere since the 2 choice
  decisions are single-select by construction).
- **nonsense** — out-of-domain or vacuous input (weather, CI status, "huh?",
  a bare "current") — tests that a decision layer doesn't spuriously commit
  to a confident wrong answer on input that isn't really about the app at all.

## Labeling methodology

**Grounding source.** Every `expected` label was derived by reading
`docs/assistant/GLOBAL_ARCHITECTURE.md`'s own decision definitions directly —
"EXECUTION CLASSES" (with its 3 worked examples: the fast path, the grounded
explanation path, and the complex physician path), "SINGLE TOOL REGISTRY"
(which literally lists which tools belong to which of the 8 categories,
e.g. `get_component_report` under **TWIN**, not **REPORT**), and "SYSTEM-1
(Laya) VS SYSTEM-2" (what Laya may vs. may never decide) — not by running
`laya_adapter.py`'s fallback and copying its output. This was a hard
constraint from the task brief and is the entire reason this fixture set is
useful: if the labels merely encoded the fallback's current behavior, an
evaluation against them would just confirm the code agrees with itself.

**How the "ambiguous" cases were chosen.** Three sources fed the hard-case
selection, in order of how directly they're cited in each fixture's `notes`:

1. **Agent 23's 3 explicitly flagged hypotheses**
   (`docs/assistant/wave5/laya-specialization.md`, "Specific fallback-heuristic
   fixes" section), reproduced and targeted directly:
   - *Regex-cascade ordering risk*: `classify_intent` checks SIMULATION cues
     (e.g. `\brecovery\b`) before COMPLEX_SYNTHESIS cues (`\bcompare\b`), so a
     retrospective, already-run comparison across scenarios plausibly gets
     misrouted to SIMULATION. Tested directly by `"Compare recovery outcomes
     across the last three scenarios."` (labeled `complex_synthesis`).
   - *`TWIN`'s `\bcurrent\b` over-routing*: `select_tool_family`'s TWIN bucket
     fires on the bare word "current", which is common in non-twin state-read
     questions generally. Tested directly by 3 fixtures using "current" in
     out-of-domain or evidence-seeking (not twin-state) contexts — a medical
     guideline question, a UTC-clock question, and a CI-build question — all
     labeled `EVIDENCE`/`NONE`, not `TWIN`.
   - *No coverage of "both true" `needs_*` binaries*: tested directly with
     `"Compare what the simulation predicts against the evidence for last
     month."` used as a fixture in **both** `needs_simulation` (expected
     `True`) and `needs_evidence_retrieval` (expected `True`) — both are
     legitimately true simultaneously and independently; the corresponding
     `select_tool_family` fixture for the same text is labeled `COMPARE` (the
     dominant verb), with a note cross-referencing the two binaries.
2. **Structural gaps found by directly re-reading `laya_adapter.py`'s
   fallback source** (not hypothesized by anyone, found fresh this pass):
   the `classify_intent` fallback's `if/elif` cascade **never contains
   `INSUFFICIENT_EVIDENCE`, `HUMAN_DECISION_REQUIRED`, or `UNSUPPORTED`
   anywhere in its branches** — these 3 of the 11 `ExecutionClass` values are
   structurally unreachable by the current keyword heuristic, regardless of
   input. Every fixture labeled with one of these 3 classes (6 total, 2
   each) is therefore a guaranteed fallback miss by construction, not a
   probabilistic hypothesis — this is arguably the single most important
   finding in this fixture set for whoever runs the real evaluation next,
   since it's a 100%-reproducible gap rather than an input-dependent one.
3. **Independently constructed near-ties**, following the same method Wave 3's
   `clinical-language-integrity.md` used for its own audit (deliberately try
   to construct a natural sentence in BeatIT's own vocabulary that would trip
   a keyword match without matching the concept), e.g.: "what happens if" vs.
   the fallback's literal `\bwhat if\b`; "rerun the ensemble" (a real
   simulation action) missing from `classify_intent`'s SIMULATION keyword list
   even though it's present in `needs_simulation`'s own list (an inconsistency
   between the two fallbacks' vocabularies, both derived from the same
   underlying concept); "that's helpful" tripping `needs_clarification`'s bare
   `\bthat\b` referent check via the apostrophe-adjacent word boundary; a
   26-word but semantically trivial direct-state-read question tripping
   `is_complex_reasoning_required`'s word-count-only threshold; a short,
   simple two-way `"compare X to Y"` tripping the same decision's bare
   `\bcompare\b` keyword despite needing no multi-source synthesis at all.

**Specific judgment calls worth flagging explicitly** (beyond what's already
inline in each fixture's `notes`):

- **`INSUFFICIENT_EVIDENCE` labels required assuming `classify_intent` has
  access to the same `context` dict its own method signature accepts** (e.g.
  `available_history_days`, `has_biopsy_data`), even though nothing in
  `laya_adapter.py`'s own fallback logic for `classify_intent` currently reads
  context at all for that purpose. A stricter reading could argue these 2
  fixtures should instead be labeled `DIRECT_STATE_READ` (a request that only
  turns out to be unanswerable once the deterministic tool actually runs) —
  this fixture set takes the more generous reading (available context can and
  should inform the label) because otherwise `INSUFFICIENT_EVIDENCE` would be
  fundamentally unlabelable by any router working from text-plus-context, and
  the class would never be testable at all.
- **A single bare referent word ("this") stays `needs_clarification=True`
  even when a resolving `component_id` is present in context** — reasoned
  explicitly in the fixture's own note: referent resolution tells you *what
  thing* "this" points to, but a single word still doesn't specify *what the
  user wants to know* about it (EF? PV loop? a report?). This is the one case
  in the whole set that was drafted, caught as internally inconsistent with
  an earlier draft label, and explicitly corrected before being finalized —
  noted here per the task's instruction to surface judgment calls made
  mid-process, not just the ones that were clean on the first pass.
- **`"Compare the current PV loop directly observed versus the model-derived
  one."` is labeled `COMPARE` (not `PHYSIOLOGY`) for `select_tool_family`,
  but `COMPLEX_SYNTHESIS` (not `DETERMINISTIC_COMPUTATION`) for
  `classify_intent`.** Both labels lean on the same underlying reasoning
  (the sentence's dominant action is a cross-source *comparison*, not a
  single physiology read or a raw calculation) but land on different tool
  families vs. execution classes because those are different label spaces —
  documented explicitly so a reviewer doesn't read this as an inconsistency
  between the two fixtures.
- **Short, simple two-way compares (`"Compare this scenario to the
  baseline."`) are labeled `is_complex_reasoning_required=False`**, while
  longer compares that also ask for synthesis/attribution
  (`"...and identify which changes are clinically meaningful"`) are labeled
  `True`. The line drawn: a bare tool-backed comparison (the `COMPARE` tool
  family can answer it directly) is not "complex reasoning" in the sense
  `GLOBAL_ARCHITECTURE.md` means by routing to the NVIDIA System-2 path;
  requiring attribution/explanation across the compared values is.

## Known limitations of this fixture set

- **Single-annotator bias.** Every label in this set was produced by one
  agent (this one) reading `GLOBAL_ARCHITECTURE.md` once. `laya-specialization.md`
  itself calls for **inter-annotator agreement measured and reported** (e.g.
  two independent labelers agreeing on >=85–90% of examples) before treating
  a labeled corpus as real ground truth for anything beyond a first-pass
  sanity check — that has not happened here, and this set should not be
  cited as authoritative beyond "one careful reading."
- **Small sample size relative to what a real calibration campaign needs.**
  160 total examples across 7 decisions (~20–30 each) is enough to compute a
  rough accuracy/confusion picture and to exercise the specific fallback
  hypotheses this task was asked to target, but is far below the
  "300–1,000+ examples per decision type" `laya-specialization.md` names as
  the floor for anything resembling a real calibration campaign, and
  nowhere close to the "hundreds to thousands per decision type" it names as
  the realistic floor for a fine-tune.
- **No real Laya calls were made or attempted.** `LAYA_ENABLED` is unset in
  this environment (confirmed via `laya_adapter.is_configured()` and the
  adapter's own docstring), so this fixture set can only be used to evaluate
  the deterministic fallback today — exactly as Agent 23's writeup
  anticipated. Nothing here contradicts or extends that.
- **The `INSUFFICIENT_EVIDENCE`/`HUMAN_DECISION_REQUIRED`/`UNSUPPORTED`
  labels rest on a specific, stated interpretive choice** (see judgment
  calls above) about whether `classify_intent` may use context, not on a
  documented spec — flagged so nobody downstream treats those 6 fixtures as
  less debatable than they are.
- **Ambiguous-case hypotheses about fallback behavior were reasoned from
  reading the regex source, not measured against a running adapter call in
  this task.** Every "fallback likely misses this" note is a prediction to
  be *confirmed* by whoever runs `load_fixtures(...)` against a live
  `LayaAdapter` instance next (the "Laya Evaluation Engineer" task), not an
  already-measured fact. `test_laya_decision_fixtures.py` only validates the
  fixture set's own internal well-formedness — it does not call
  `LayaAdapter` at all, intentionally, to keep this task's scope to fixture
  construction rather than duplicating the evaluation task.
- **`select_tool_family`'s and `classify_intent`'s rare-class fixtures (2
  each for the classes the current fallback structurally cannot produce) are
  necessarily somewhat constructed/contrived** rather than drawn from
  observed real user phrasing, since no real user-query log exists for this
  app yet — flagged as a realism limitation, not a labeling-correctness one.

## Test output (actual, pasted)

```
$ python -m pytest python/hearttwin/tests/test_laya_decision_fixtures.py -v
============================= test session starts ==============================
platform linux -- Python 3.13.12, pytest-9.0.3, pluggy-1.5.0
collected 42 items

python/hearttwin/tests/test_laya_decision_fixtures.py::test_decision_names_match_the_real_laya_adapter_public_methods PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_tool_family_options_matches_the_real_adapter_vocabulary PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_load_fixtures_rejects_unknown_decision_name PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_valid_labels_rejects_unknown_decision_name PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_decision_has_the_minimum_required_fixture_count[classify_intent] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_decision_has_the_minimum_required_fixture_count[select_tool_family] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_decision_has_the_minimum_required_fixture_count[needs_evidence_retrieval] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_decision_has_the_minimum_required_fixture_count[needs_simulation] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_decision_has_the_minimum_required_fixture_count[needs_clarification] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_decision_has_the_minimum_required_fixture_count[needs_physician_review_framing] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_decision_has_the_minimum_required_fixture_count[is_complex_reasoning_required] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_total_fixture_count_meets_the_wave_5_task_floor PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_has_non_empty_text_and_a_dict_context[classify_intent] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_has_non_empty_text_and_a_dict_context[select_tool_family] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_has_non_empty_text_and_a_dict_context[needs_evidence_retrieval] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_has_non_empty_text_and_a_dict_context[needs_simulation] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_has_non_empty_text_and_a_dict_context[needs_clarification] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_has_non_empty_text_and_a_dict_context[needs_physician_review_framing] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_has_non_empty_text_and_a_dict_context[is_complex_reasoning_required] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_category_is_a_recognized_value[classify_intent] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_category_is_a_recognized_value[select_tool_family] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_category_is_a_recognized_value[needs_evidence_retrieval] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_category_is_a_recognized_value[needs_simulation] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_category_is_a_recognized_value[needs_clarification] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_category_is_a_recognized_value[needs_physician_review_framing] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_fixture_category_is_a_recognized_value[is_complex_reasoning_required] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_classify_intent_labels_are_real_execution_class_values PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_select_tool_family_labels_are_real_tool_family_values PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_yes_no_decision_labels_are_actual_booleans[needs_evidence_retrieval] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_yes_no_decision_labels_are_actual_booleans[needs_simulation] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_yes_no_decision_labels_are_actual_booleans[needs_clarification] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_yes_no_decision_labels_are_actual_booleans[needs_physician_review_framing] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_yes_no_decision_labels_are_actual_booleans[is_complex_reasoning_required] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_label_option_is_covered_by_at_least_one_fixture[classify_intent] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_label_option_is_covered_by_at_least_one_fixture[select_tool_family] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_label_option_is_covered_by_at_least_one_fixture[needs_evidence_retrieval] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_label_option_is_covered_by_at_least_one_fixture[needs_simulation] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_label_option_is_covered_by_at_least_one_fixture[needs_clarification] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_label_option_is_covered_by_at_least_one_fixture[needs_physician_review_framing] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_every_label_option_is_covered_by_at_least_one_fixture[is_complex_reasoning_required] PASSED
python/hearttwin/tests/test_laya_decision_fixtures.py::test_load_fixtures_returns_independent_copies PASSED
python/hearttwin/tests/test_at_least_one_ambiguous_hard_case_exists_per_decision PASSED

============================== 42 passed in 0.07s ==============================
```

Full repo suite re-run after adding these files
(`python -m pytest python/hearttwin/tests`): **1152 passed, 1 skipped, 10
xfailed** — confirms nothing existing regressed (this task's 3 new files are
additive only; `laya_adapter.py` and every other existing file were read,
never modified).

## Files touched

New only, per this task's file-ownership constraint:

- `python/hearttwin/tests/fixtures/laya_decision_fixtures.py`
- `python/hearttwin/tests/test_laya_decision_fixtures.py`
- `docs/assistant/wave5/decision-fixtures.md` (this file)

`python/hearttwin/tests/fixtures/__init__.py` (the pre-existing empty package
marker from the interrupted prior attempt) was left as-is — it already
contained a correct one-line docstring, so no change was needed.

`python/hearttwin/assistant/laya_adapter.py` was read only, never modified.
No file under `python/hearttwin/tools/cardiac_state.py`, `hemodynamics.py`,
`recovery_sim.py`, `python/hearttwin/shadow_trial_*.py`, `api.py`,
`copilot.py`, or `careguard/*` was touched.

## Global Architecture Compliance

No competing router, decision layer, fixture convention, or vocabulary was
created. `TOOL_FAMILY_OPTIONS` is a second copy of `laya_adapter.py`'s own
private `_TOOL_FAMILY_OPTIONS` list (not a new/competing vocabulary), pinned
against drift by `test_tool_family_options_matches_the_real_adapter_vocabulary`.
`classify_intent`'s label space is imported directly from
`python.hearttwin.assistant.schemas.ExecutionClass`, the one canonical
execution-class enum, rather than a re-declared copy. This document proposes
no code change to `laya_adapter.py` and modifies no existing file.
