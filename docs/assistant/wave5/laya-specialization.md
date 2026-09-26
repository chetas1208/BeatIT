# Laya / Fallback Specialization Decision — Wave 5, Agent 23 ("Laya Specialization Engineer")

> Read first: `docs/assistant/GLOBAL_ARCHITECTURE.md` ("LAYA EVALUATION
> REQUIREMENT", "SYSTEM-1 (Laya) VS SYSTEM-2", "Decision support object"),
> `docs/assistant/LAYA_RESEARCH.md` ("Calibration Campaign Prerequisites",
> "Fine-tuning path"), `python/hearttwin/assistant/laya_adapter.py`,
> `docs/assistant/wave2/laya-integration.md`.

## Status of the required input: Agent 22's baseline evaluation was NOT available

This analysis was scoped to be grounded entirely in Agent 22's ("Laya
Evaluation Engineer") measured baseline numbers from
`docs/assistant/wave5/laya-evaluation.md`. **That file does not exist as of
this writing.** I checked for it repeatedly over this task (an initial read,
then a background poll of the exact path every 15s for up to 10 minutes),
and separately searched the whole repo for any newer eval/fixture artifact
(`find … -iname "*eval*"`, `-iname "*fixture*"`, `-iname "*wave5*"`) that
might be Agent 22's output under a different name. Nothing was found. The
`docs/assistant/wave5/` directory itself did not exist at any point I
checked.

Per this task's own instructions, I am **not** inventing numbers to react
to. Everything below is either (a) a structural/code-inspection observation
made by reading `laya_adapter.py` directly — clearly labeled as such, not
presented as a measured failure — or (b) a conditional decision rule of the
form "if Agent 22's measured accuracy for decision X is below/above
threshold T, then verdict V, because reasoning R." **If Agent 22's
evaluation lands later, whoever reads it next should apply the rules in the
table below directly rather than re-deriving them.**

## The one verdict that does NOT depend on Agent 22's numbers: no fine-tuning qualifies right now

This can be stated with confidence regardless of what Agent 22 measures,
because it turns on data availability, not on accuracy:

- `LAYA_RESEARCH.md`'s own "Fine-tuning path" section documents exactly one
  concrete recipe: `notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb`,
  RLCD-style reward training, sized for 2×T4 GPUs. That report explicitly
  flags that **the exact data format for training examples was not visible
  in the fetched excerpts** — i.e., even the input schema for a real
  fine-tune has never been directly confirmed, only inferred to exist.
- Laya's own published benchmark methodology (`BENCHMARKS.md`, cited in
  `LAYA_RESEARCH.md`) uses **400 cases / 2,000 decisions** for its own
  typed-decisions eval — that is the order of magnitude Laya's own team
  considers sufficient to *evaluate* a checkpoint, before even discussing
  how much more is needed to *train* one. RLCD/RL-style fine-tunes of an
  encoder checkpoint this size (322M–421M params) are not one-shot/few-shot
  processes; hundreds-to-thousands of labeled examples per decision type is
  the realistic floor for a fine-tune to move the needle without overfitting
  to a handful of fixtures, consistent with this task's own framing.
- The only labeled data BeatIT has for these seven routing decisions is
  whatever Agent 21/22 assembled as fixtures for the baseline eval. Given
  the campaign's own scale (a hackathon-style, single-wave exercise) and
  Wave 2's adapter tests (`test_laya_adapter.py`) — which are a handful of
  *unit-test* examples (mocked single-call assertions per behavior, not a
  labeled corpus) — any realistic fixture set produced in this wave is
  almost certainly in the tens, not hundreds-to-thousands, per decision
  type. **This is true whether Agent 22's measured accuracy turns out to be
  30% or 90%** — a small fixture set can tell you baseline accuracy is poor,
  but it cannot supply enough labeled data to fine-tune on, and no amount of
  re-reading Agent 22's numbers changes that arithmetic.
- Separately: `laya_adapter.py`'s own docstring states **"Laya is not
  reachable from this environment"** and `is_configured()` requires an
  explicit `LAYA_ENABLED=true` + `LAYA_BASE_URL` that nothing in this repo
  sets. There is no live Laya checkpoint in this environment to fine-tune in
  the first place — the Kaggle notebook path would need to run externally,
  against a real `laya` package install, entirely outside this campaign's
  current infrastructure.

**Conclusion: real fine-tuning is not justified for any of the seven
decision types right now, independent of Agent 22's results, because the
labeled-data and live-checkpoint prerequisites are both absent.** This
confirms the task brief's own expectation ("very likely 'no, sample size
insufficient'"). See "Full fine-tuning recipe (for future reference)" below
for what would actually be required if this changes.

## Per-decision-type table

All seven decision types are `LayaAdapter`'s named public methods
(`python/hearttwin/assistant/laya_adapter.py`). "Current mechanism" reflects
that Laya itself is unreachable in this environment (per the adapter's own
docstring), so **every real request in this campaign is served by the
deterministic fallback today**, not by live Laya — "fine-tune Laya" and
"improve the fallback" are therefore not really alternatives for the same
underlying model; they are two different systems, and the fallback is the
one actually running.

| Decision (method) | Current mechanism | Baseline evidence | Verdict | Reasoning |
|---|---|---|---|---|
| `classify_intent` | Fallback keyword router over `ExecutionClass` (7-way, ordered regex cascade) | **Not measured** — Agent 22 pending | **Conditional** — see rule below | Highest-cardinality decision (7+ options), most likely to show real accuracy gaps in a keyword cascade; also the one most worth fixing cheaply since the fix is "add a missing keyword to a bucket," not infrastructure |
| `select_tool_family` | Fallback keyword router, 8-way (7 registry categories + `NONE`) | **Not measured** | **Conditional** — see rule below | Same structural shape as `classify_intent`; shares the same class of fix |
| `needs_evidence_retrieval` | Fallback binary regex (`evidence`/`source`/`provenance`/`cite`/...) | **Not measured** | **Likely defer, conditionally improve** | Binary decisions with a narrow, well-defined trigger vocabulary (evidence/citation language) are the easiest case for a keyword heuristic to do well on already; low expected payoff from tuning unless Agent 22 shows a specific miss |
| `needs_simulation` | Fallback binary regex (`what if`/`scenario`/`simulat`/`recovery`/...) | **Not measured** | **Likely defer, conditionally improve** | Same reasoning as `needs_evidence_retrieval` |
| `needs_clarification` | Fallback binary rule (length + bare-referent + context-key resolution) | **Not measured** | **Defer** | This is not a pure keyword match — it already encodes real logic (referent resolution against `_CONTEXT_REFERENT_KEYS`) mirroring `intake_agent.py`'s own rule; a routing miss here means one extra clarifying turn, the cheapest possible failure mode in the whole set |
| `needs_physician_review_framing` | Fallback rule: `audience=="physician"` short-circuits True, else keyword regex | **Not measured** | **Defer** | The audience short-circuit is deterministic and correct by construction (it is an exact context-field check, not a heuristic); only the non-physician-audience keyword branch is heuristic, and per `GLOBAL_ARCHITECTURE.md`'s "Decision support object" section this only controls *framing density*, never whether something IS risky — a miss here is a UX/tone difference, not a safety gap |
| `is_complex_reasoning_required` | Fallback rule: word-count > 18 OR comparison/synthesis keywords | **Not measured** | **Defer** | A false answer either way only changes which model depth is used (per the adapter's own docstring: "a false 'True' only costs an unnecessarily deep model call, never a safety failure"); the cost of tuning this further is not obviously justified without evidence it is actually wrong often |

### The conditional rule for `classify_intent` and `select_tool_family`

These are the two decisions I'd expect Agent 22's numbers to most plausibly
justify action on, because they are the highest-cardinality (most ways to be
wrong) and most likely to have visible per-class confusion patterns. Apply
this rule once real numbers exist:

- **If measured per-class accuracy for a specific `ExecutionClass` or tool
  family is low AND Agent 22's confusion matrix / worst-failure-case list
  shows a *specific, nameable keyword gap*** (e.g., "requests containing
  word W are consistently misrouted from class A to class B because W only
  appears in class B's bucket and A has no matching pattern") — **verdict:
  improve fallback heuristic now.** This is cheap (a regex list edit, no
  training infra, no GPU), fast to verify (re-run the existing
  `test_laya_adapter.py` plus new fixture-derived tests), and does not
  require Laya to be reachable at all.
- **If measured accuracy is low but the failures are *semantically*
  ambiguous** (e.g., a request that is genuinely dual-intent, or requires
  understanding negation/context that no realistic keyword list could
  capture) — **verdict: defer.** A keyword-list patch cannot fix a
  fundamentally semantic ambiguity, and per `GLOBAL_ARCHITECTURE.md`'s
  "Decision support object" section, a wrong `classify_intent`/
  `select_tool_family` guess is recoverable: the orchestrator still runs the
  same safety validator regardless, and the user can always ask a follow-up.
  Do not chase heuristic accuracy on cases where the heuristic approach is
  structurally the wrong tool — that is the actual signal that a real
  learned model (Laya, once reachable) would help, but per the "no
  fine-tuning qualifies right now" section above, that path is blocked on
  data volume today regardless.
- **If measured accuracy is already adequate (no threshold is prescribed
  campaign-wide, but by analogy to Laya's own zero-shot baseline of
  ~0.35–0.36 on its own typed-decisions eval per `LAYA_RESEARCH.md`, a
  fallback clearing roughly that bar or better, on BeatIT's own routing
  vocabulary which is narrower and more predictable than Laya's general-
  purpose benchmark, would already be a reasonable result for a routing
  layer)** — **verdict: defer**, on the explicit reasoning in this task's
  brief: Laya/fallback routing mistakes degrade UX (wrong tool family tried
  first, one extra retry), they do not create a safety gap, because
  `GLOBAL_ARCHITECTURE.md`'s guardrail layers (numerical claim gate,
  provenance gate, `safety_validator.py`'s diagnosis/treatment/emergency
  blocking) run unconditionally downstream of whatever `classify_intent`
  or `select_tool_family` decided.

## Specific fallback-heuristic fixes: NONE proposed this wave, and why

The task asks for specific, evidenced fixes "from Agent 22's actual failure
cases (e.g. 'the fixture X fails because keyword Y is missing from bucket
Z')." **I am not proposing any such fix, because Agent 22's failure-case
data does not exist yet to cite.** Proposing a fix without a cited fixture
would violate this task's explicit constraint ("do NOT invent a number to
react to") in spirit — the same applies to inventing a *failure case*.

What I can offer instead, from direct code inspection of
`laya_adapter.py` (labeled explicitly as code-review observations, not
measured failures, so a future integrator knows these are hypotheses to
test against real fixtures, not confirmed bugs):

1. **Regex-cascade ordering risk in `_fallback_classify_intent` /
   `_fallback_select_tool_family`** (lines ~276–329): both functions use an
   `if/elif` cascade over overlapping vocabularies. For example,
   `_fallback_classify_intent` checks `SIMULATION` cues (`\brecovery\b`)
   before `COMPLEX_SYNTHESIS` cues, and `_fallback_select_tool_family`
   checks `TWIN` last, after `REPORT` — so a request like "compare the
   current twin's EF to last week's report" would hit the `COMPARE` branch
   in `select_tool_family` (correct) but the `COMPLEX_SYNTHESIS` branch in
   `classify_intent` before ever reaching `TWIN`-flavored cues, since
   `\bcompare\b` is checked early. This is a plausible source of
   misclassification on multi-clause requests, but **whether it actually
   fires on real user phrasing is exactly what Agent 22's fixtures would
   show** — flagging it here as a hypothesis to check against Agent 22's
   confusion matrix once available, not as a confirmed defect.
2. **`select_tool_family`'s `TWIN` bucket is the broadest catch-most-things
   bucket, checked second-to-last** (line 318): it fires on `\bcurrent\b`,
   which is a very common word in state-read questions generally. If Agent
   22's fixtures show `NONE` or `DIRECT_STATE_READ`-shaped requests being
   over-routed to `TWIN`, the fix would be to narrow `\bcurrent\b` to
   require co-occurrence with a twin/patient-state noun, or move the `TWIN`
   check earlier with a tighter pattern — again, only worth doing if real
   fixtures confirm this actually happens.
3. **No test coverage of the `needs_*` binary methods against ambiguous
   inputs that legitimately trigger more than one bucket** (e.g., "compare
   what the simulation predicts against the evidence for last month" would
   plausibly trip both `needs_simulation` and `needs_evidence_retrieval`,
   which is fine since they're independent booleans, but nothing today
   verifies BeatIT's orchestrator handles "both true" gracefully rather than
   assuming exactly one applies) — this is a downstream orchestrator
   question, not this adapter's, but worth flagging since a specialization
   pass might otherwise "fix" one flag at the expense of breaking an
   implicit both-true assumption elsewhere.

None of these three observations should be applied to `laya_adapter.py`
without first checking them against Agent 21/22's real fixtures — per this
task's own constraint, and because a keyword-list edit made to satisfy a
hypothetical is exactly the kind of unverified change `AGENTS.md`-style
campaigns are trying to avoid.

## Full fine-tuning recipe (for future reference only — not attempted, not currently justified)

Documented per `LAYA_RESEARCH.md`'s "Fine-tuning path" and "Calibration
Campaign Prerequisites" sections, for whoever revisits this decision later:

- **Recipe**: `notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb`
  (Kaggle, free-tier 2×T4 GPU), RLCD-style reward training (Laya's own term
  for its "reinforcement learning against strictly proper scoring rules"
  training approach, per `LAYA_RESEARCH.md`'s architecture section).
- **Data format**: **unverified.** `LAYA_RESEARCH.md` explicitly states the
  exact training-example format was not visible in the fetched excerpts.
  Before any real attempt, the notebook itself (or the `laya` repo's
  training-data loader code) must be read directly — this was flagged as
  unread source in Wave 1 and remains unread now; this wave did not attempt
  to read it either, since no fine-tune was in scope regardless of format.
- **Minimum labeled examples**: not documented by Laya itself for a
  domain-specialization fine-tune specifically, but by analogy to its own
  *evaluation* methodology (400 cases / 2,000 decisions for a benchmark) and
  standard practice for encoder fine-tunes at this scale, realistically
  **hundreds to thousands of labeled examples per decision type** — this
  task's own framing calls this the expected floor, and I have no evidence
  to contradict it. BeatIT's current fixture volume for these seven
  decisions (Wave 2's unit tests plus whatever Agent 21 assembled for the
  Wave 5 eval) is almost certainly one to two orders of magnitude below
  that, based on the unit-test file's scale (a handful of mocked examples
  per behavior, not a labeled corpus) — this is the central reason
  fine-tuning does not qualify today regardless of measured accuracy.
- **Compute**: 2×T4 (Kaggle free tier) per the notebook's own filename —
  low barrier if data existed, not the blocking constraint.
- **Live checkpoint access**: none today. `LAYA_ENABLED`/`LAYA_BASE_URL` are
  unset in this environment; `laya_adapter.py`'s docstring states Laya is
  not reachable from this environment at all. A fine-tune would need to run
  entirely outside BeatIT's current infra (e.g., in a separate Kaggle
  notebook against a cloned `laya` checkpoint), then the resulting weights
  would need to be hosted somewhere `LAYA_BASE_URL` could reach — that
  hosting/serving step is undesigned and out of this wave's scope too.
- **Estimated effort if all prerequisites were met**: rough order-of-
  magnitude estimate only (not a measured figure) — data collection/
  labeling (hundreds-to-thousands of examples across 7 decision types, with
  inter-annotator agreement checked) is almost certainly the dominant cost,
  likely multiple person-days to weeks depending on how "labeled example"
  is operationalized (single-annotator quick pass vs. multi-annotator
  agreement-checked set); the actual Kaggle training run itself, per the
  notebook's framing as a free-tier-sized job, is plausibly hours, not days.

## What would need to be true before revisiting fine-tune-vs-not

1. **Agent 22's `docs/assistant/wave5/laya-evaluation.md` must exist** with
   real per-decision accuracy, confusion matrices, Brier score, ECE,
   abstention rate, and false-high-confidence rate, per
   `GLOBAL_ARCHITECTURE.md`'s "LAYA EVALUATION REQUIREMENT" — this is the
   single hard blocker for even starting the conditional rules above.
2. **A labeled BeatIT-specific routing corpus of roughly 300–1,000+ examples
   per decision type** (not the current handful-of-fixtures scale), ideally
   with **inter-annotator agreement measured and reported** (a concrete,
   checkable bar — e.g., two independent labelers agreeing on ≥85–90% of
   examples before a single "ground truth" label is accepted) — this task's
   own framing calls for exactly this kind of explicit, falsifiable
   threshold rather than a vague "enough data" claim.
3. **A reachable live Laya endpoint** (`LAYA_ENABLED=true` +
   `LAYA_BASE_URL` pointing at a real `laya-serve` instance) so that (a) a
   real zero-shot Laya baseline can be measured on BeatIT's own routing
   vocabulary (distinct from its own general-purpose benchmark numbers,
   which `LAYA_RESEARCH.md` explicitly says do not transfer), and (b) a
   fine-tuned checkpoint would have somewhere to be served from.
4. **A demonstrated, evidenced fallback-heuristic ceiling** — i.e., Agent
   22's numbers (once available) show that even after applying the
   "improve fallback heuristic now" fixes this document's conditional rules
   would recommend, per-decision accuracy still plateaus below what the
   product needs, on failures that are genuinely semantic rather than
   keyword-list gaps. Only at that point does "fine-tune a real model"
   become the correct next lever rather than "write a better regex."
5. Regardless of 1–4, **the hard boundary in `laya_adapter.py` does not
   move**: no specialization outcome from this decision — fine-tune,
   fallback fix, or defer — ever expands Laya/fallback's scope beyond the
   seven named bounded routing questions, and `calibration_status` stays
   `"uncalibrated"` until an actual calibration campaign (ECE, Brier, on
   held-out BeatIT data) has run and is documented, per Wave 2's own
   "What Wave 5 must do before any of this changes" list.

## Preserved artifacts (referenced, not duplicated)

- `docs/assistant/wave5/laya-evaluation.md` — Agent 22's baseline
  measurement. **Did not exist at the time this document was written**;
  once it exists, its per-decision accuracy/confusion-matrix/Brier/ECE
  numbers should be dropped directly into the table above in place of "Not
  measured," and the conditional rules resolved into concrete verdicts.
- `python/hearttwin/tests/test_laya_adapter.py` — Wave 2's adapter unit
  tests (11 tests covering unconfigured/mocked-success/mocked-failure/
  structural-boundary behavior); these are correctness tests for the
  adapter's plumbing, not an accuracy benchmark, and are cited here rather
  than duplicated.
- `docs/assistant/wave2/laya-integration.md` — the adapter's own design
  rationale and its own "What Wave 5 must do" checklist, several items of
  which this document directly answers (item 6's non-negotiable boundary is
  restated above; items 1–5 remain Agent 22's/a live-Laya-integration
  task's responsibility, not this document's).
- `docs/assistant/LAYA_RESEARCH.md` — source of all fine-tuning-recipe and
  calibration-prerequisite claims cited above; not re-derived independently.

## Global Architecture Compliance

No competing router, decision layer, or vocabulary was created. This
document proposes no code change and modifies no existing file
(`laya_adapter.py` was read only). It does not move Laya/fallback's scope
beyond `GLOBAL_ARCHITECTURE.md`'s "Laya can decide" list, and it explicitly
declines to fabricate baseline numbers Agent 22 had not yet produced,
per this task's own grounding requirement.
