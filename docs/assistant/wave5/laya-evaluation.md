# Laya Evaluation (Wave 5, Agent 22 — "Laya Evaluation Engineer", retry)

> This is a retry of a run that failed before producing any output (account
> rate limit; see `docs/assistant/WAVE_5_HANDOFF.md`). No orphaned Docker
> container existed from that attempt. This run went further than a Docker
> attempt: it found and reused an orphaned **bare Python venv** left by that
> same prior attempt (see "What was already there" below), which meant a
> real Laya server could be stood up and benchmarked, not just the
> deterministic fallback.

## Bottom line

**Path taken: REAL Laya was successfully deployed and benchmarked**, head to
head against the deterministic fallback, on **Agent 21's real 160-fixture
labeled set** (`python/hearttwin/tests/fixtures/laya_decision_fixtures.py`).
This is the ideal outcome described in the task (item 2), not the fallback.

- **Deterministic fallback overall accuracy: 129/160 = 80.6%**
- **Real Laya (zero-shot base checkpoint, `convaiinnovations/laya`, CPU)
  overall accuracy: 104/160 = 65.0%**
- The fallback beats real zero-shot Laya on this narrow, keyword-friendly
  BeatIT-specific domain, on every one of the 7 decision types except
  `classify_intent` (Laya 75.9% vs. fallback 58.6%). This is consistent with
  `docs/assistant/LAYA_RESEARCH.md`'s own prediction that the base checkpoint
  (~0.35 accuracy on Laya's own general benchmark) would perform "noticeably
  worse" than Laya's fine-tuned-checkpoint marketing numbers (0.766 accuracy)
  — though on this specific, narrow, single-domain task the gap to the
  fallback is smaller than that headline number might suggest, and Laya
  genuinely wins on the hardest, most open-ended decision type
  (`classify_intent`, 11 possible labels).
- **A real, previously-undiscovered integration bug was found and is
  documented below**: `laya_adapter.py`'s wire format for `choice`-type
  decisions (`classify_intent`, `select_tool_family`) does not match what a
  real Laya server expects. If `LAYA_ENABLED=true` were ever turned on
  against a real server today, both choice-type decisions would **always**
  silently fall through to the deterministic fallback — even on a fully
  healthy server — while the 5 `noul`-type decisions would work correctly.
  This was not something LAYA_RESEARCH.md could have caught (it flagged the
  exact wire format as unverified), and no prior wave's tests exercise a
  real server, so this evaluation is the first time it's been observed. Not
  fixed here per this task's "new files only" constraint — see
  "Recommendation" below.

## What was already there (why this went faster than expected)

Before starting, `docker ps -a | grep -i laya` was confirmed empty per the
retry brief. However `/tmp/laya_eval_venv` (a bare Python 3.13 venv, 5.6GB,
containing `laya[serve]` 0.3.20 + torch 2.14 + a fully-populated
`~/.cache/huggingface/hub/models--convaiinnovations--laya` checkpoint cache,
~8.1GB) already existed on disk, timestamped 2026-09-26 11:09 — clearly left
behind by the prior interrupted attempt (installing `laya[serve]` and
downloading its checkpoint, which together take several minutes, before the
rate limit hit). This is not a Docker container so the retry brief's
"no orphaned container" check didn't (and couldn't) surface it. It was
inspected, found to be exactly what item 1 of this task calls for, and
reused rather than re-downloaded from scratch — this is why the real-Laya
path took only a few minutes of the ~15-20 minute budget instead of the full
budget.

## Methodology

### 1. Real Laya deployment (no Docker needed)

```
python3 -m venv /tmp/laya_eval_venv        # already existed; verified functional
/tmp/laya_eval_venv/bin/pip install "laya[serve]"   # already satisfied (0.3.20) — see
                                                      # docs/assistant/wave5/artifacts/laya_pip_install.log
```

`docker ps` at task start showed `ghostrange-postgres-dev` (5432),
`ghostrange-valkey-dev` (6379), and one stopped `echo-db-1` — all left
untouched. Port 8000 was also found in use by an unrelated process, so the
server was bound to **127.0.0.1:8931** instead (confirmed free first via
`ss -ltn`). Started with:

```
LAYA_HOST=127.0.0.1 LAYA_PORT=8931 LAYA_DEVICE=cpu LAYA_PRELOAD=1 LAYA_LOG_LEVEL=info \
  /tmp/laya_eval_venv/bin/laya-serve
```

Full startup log (including the checkpoint's own calibration warning,
verbatim, unedited):
`docs/assistant/wave5/artifacts/laya_serve_startup_v2.log`. Relevant excerpt:

```
laya/router.py:260: RuntimeWarning: laya: this checkpoint ships invalid
temperatures or values outside [0.5, 5]; using choice:11+=0.10058280825614929
-> 0.5. Treat confidence from the affected entries as uncalibrated.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8931 (Press CTRL+C to quit)
```

This warning is Laya's **own** code, printed at startup, independently
corroborating LAYA_RESEARCH.md's calibration-caveat findings — not something
this evaluation asserted, something the real model self-reports.

A basic request to `POST /v1/systemone` was confirmed working (real model
inference, not a stub) before proceeding — see
`docs/assistant/wave5/artifacts/laya_real_server_raw.json` for the first
successful raw exchange, and the wire-format discovery below.

**No Docker container was ever created for this task** — the pip package +
bare `laya-serve` process was faster and simpler than building the repo's
compose files, and fully satisfies "an actual Laya instance" per the task's
own item 1 framing ("real Laya facts: pip package `laya[serve]` →
`laya-serve` command").

### 2. Discovering the real wire format (a genuine, unplanned finding)

`laya_adapter.py`'s own docstring (LAYA_RESEARCH.md's caveat, repeated
verbatim in the adapter) says the exact `POST /v1/systemone` request/response
JSON body "could not be read from source" in Wave 1. With a real server now
running, the actual shape was determined empirically:

- A first test request, built exactly as `laya_adapter._call_systemone`
  constructs it (`criteria: {"options": [<list of option strings>]}` for a
  `choice` question), returned `"choice": "options"` — i.e., the server
  read the criteria dict's single key literally as **one option named
  "options"**, and duly "chose" it with 100% probability. This is because
  the real server's choice-question parser
  (`laya/shortlist.py::_criteria_items`, read directly from the installed
  package source) treats `criteria` as `{label: description}` pairs via
  `.items()` — a **list** value under a single `"options"` key becomes one
  giant description string for one option confusingly named `"options"`,
  not a list of N options.
- The correct shape, read from the same source
  (`laya/agent.py` docstring, lines ~855-858 of the installed package):
  `criteria: {"optA": "description of optA", "optB": "description of optB", ...}`
  — one dict entry per real option, each value a human-readable description.
  Using this shape, real answers came back correctly (see the worked example
  in `docs/assistant/wave5/artifacts/laya_real_server_raw.json`, e.g.
  `classify_intent` on "What if the patient goes on a beta blocker regimen,
  run the recovery scenario" → `"choice": "simulation"`, `probabilities:
  {simulation: 0.6349, generative_explanation: 0.1156, ...}`).
- `noul`-type questions (the adapter's 5 yes/no decisions) send
  `criteria: {}` (empty), which **is** an accepted, correct shape per the
  same source (`criteria` is documented as optional for `noul`) — these work
  correctly with the adapter's existing code, unmodified.

**Concrete proof this is a live, real bug in the shipped adapter, not just a
theoretical reading of source code:** `docs/assistant/wave5/artifacts/laya_adapter_bug_evidence.json`
captures the actual, unmodified `LayaAdapter` class (imported from
`python/hearttwin/assistant/laya_adapter.py`, no changes made) called with
`LAYA_ENABLED=true` and `LAYA_BASE_URL` pointed at the live server above:

| Method | Type | Result `source` field |
|---|---|---|
| `classify_intent` | choice | `"fallback"` — despite the server being fully healthy and answering (with `choice="options"`, then rejected by the adapter's own `chosen not in options` validity check, which correctly refuses the garbage answer and falls through) |
| `select_tool_family` | choice | `"fallback"` — same root cause |
| `needs_simulation` | noul | `"laya"` — genuine real-model answer, works as designed |
| `needs_clarification` | noul | `"laya"` — genuine real-model answer, works as designed |

This means: **today, if someone flips `LAYA_ENABLED=true` in production
against a real Laya server, `classify_intent` and `select_tool_family` will
never actually be answered by Laya** — they will silently and permanently
use the deterministic fallback (which, per this evaluation, is actually the
*better* choice for those two decisions on this domain anyway — see
metrics below — so this bug has accidentally been harmless so far, but it
means Laya has never been able to be evaluated end-to-end through the
adapter itself, only through a corrected direct call as done here). This is
a real, actionable, previously-undocumented finding for whoever next touches
`laya_adapter.py` — **not fixed in this task**, since `laya_adapter.py` is
out of scope (new-files-only constraint).

### 3. Fixture set

**Agent 21's real 160-fixture labeled set was used as the primary/only
evaluation set** (`python/hearttwin/tests/fixtures/laya_decision_fixtures.py`,
29/30/20/20/21/20/20 examples across the 7 decision types respectively).
Per this task's instructions ("if it exists, use its real labeled fixtures"),
this took priority over building a stopgap set.

**Timeline note, for transparency:** at the start of this task, Agent 21's
fixture file did not exist yet (only an empty
`python/hearttwin/tests/fixtures/__init__.py`, matching
`WAVE_5_HANDOFF.md`'s description). A 15-example stopgap fixture set was
built independently during the wait
(`python/hearttwin/tests/fixtures/laya_decision_fixtures_stopgap.py`,
clearly marked as superseded in its own docstring) and was validated against
the fallback code (100% of its hand-predicted "known weakness" cases matched
actual fallback behavior on first run — see that file's raw output in
`docs/assistant/wave5/artifacts/fallback_only_eval_raw.json` and
`laya_real_server_raw.json` / `metrics_summary.json` for the corresponding
real-Laya run on that smaller set, kept for reference). Partway through this
task, Agent 21's real fixture file appeared (initially with a syntax error —
a stray `)` — that resolved itself within about a minute, consistent with
Agent 21 still actively finishing its own write at that moment). Once
Agent 21's file parsed cleanly and its own 42-test suite
(`test_laya_decision_fixtures.py`) passed, this evaluation was re-run
against it in full and those numbers are what's reported below and in the
committed regression test. **The stopgap file is left in place but is not
used by anything else** — it is documentation of the wait, not a competing
source of truth.

### 4. Metrics computed

- **Accuracy** and **confusion matrix** (both sources, all 7 decision types).
- **Brier score** and **ECE** — **real Laya only**. For `choice` decisions,
  Brier score is the standard multiclass sum-of-squared-errors over all
  candidate labels (`sum((p_i - y_i)^2)`, range 0-2, not the mean); for
  `noul` decisions, the standard binary Brier score
  `(p - y)^2`. ECE uses 5 equal-width confidence buckets
  (`answer_confidence` from the real response), weighted by bucket size.
  **These are deliberately NOT computed for the deterministic fallback** —
  it returns no probability of any kind (`raw_score=None` on every fallback
  decision, by design, per `laya_adapter.py`'s own docstring), and fabricating
  a fake confidence value to force a Brier/ECE number would violate this
  campaign's explicit "do not fabricate benchmark numbers" rule. This is
  stated plainly rather than worked around.
- **Abstention rate**: real Laya's response includes an `action.act_probability`
  field (documented as the model's confidence it should act at all vs. defer).
  **Observed value: exactly `1.0` on every single one of the 160 real-Laya
  calls made in this evaluation** (see `act_probability_min`/`_max` columns
  below) — i.e., the zero-shot base checkpoint never signaled an abstention
  on this fixture set, at least via this field. Reported exactly as observed;
  no abstention behavior to report beyond that. For the fallback, the closest
  analogue is `classify_intent` predicting `clarification_required` (13.8%,
  4/29) and `needs_clarification` predicting `True` (52.4%, 11/21 — note this
  is the fixture set's *own* positive-label rate for that decision, since
  fallback got 20/21 correct on it) — these are the fallback's own explicit
  "ask a follow-up" signals, not a probability-threshold abstention, and are
  reported as such rather than invented.

## Full metrics tables

### Deterministic fallback (no Laya call attempted; `laya_adapter.py`'s `_fallback_*` functions)

| Decision type | Accuracy | Correct/Total | Brier | ECE | Abstention |
|---|---|---|---|---|---|
| `classify_intent` | 58.6% | 17/29 | N/A (no probability) | N/A | 13.8% predict `clarification_required` |
| `select_tool_family` | 73.3% | 22/30 | N/A | N/A | N/A (no abstain option in this vocabulary) |
| `needs_evidence_retrieval` | 85.0% | 17/20 | N/A | N/A | N/A |
| `needs_simulation` | 90.0% | 18/20 | N/A | N/A | N/A |
| `needs_clarification` | 95.2% | 20/21 | N/A | N/A | 52.4% predict `True` (own positive rate) |
| `needs_physician_review_framing` | 90.0% | 18/20 | N/A | N/A | N/A |
| `is_complex_reasoning_required` | 85.0% | 17/20 | N/A | N/A | N/A |
| **Overall** | **80.6%** | **129/160** | — | — | — |

### Real Laya (zero-shot base checkpoint, `convaiinnovations/laya`, CPU, no fine-tuning)

| Decision type | Accuracy | Correct/Total | Brier | ECE | act_probability | Mean latency |
|---|---|---|---|---|---|---|
| `classify_intent` | 75.9% | 22/29 | 0.4222 | 0.1508 | [1.0, 1.0] | 325.5ms |
| `select_tool_family` | 63.3% | 19/30 | 0.4845 | 0.1258 | [1.0, 1.0] | 292.6ms |
| `needs_evidence_retrieval` | 65.0% | 13/20 | 0.1785 | 0.1442 | [1.0, 1.0] | 126.0ms |
| `needs_simulation` | 70.0% | 14/20 | 0.1854 | 0.1773 | [1.0, 1.0] | 132.3ms |
| `needs_clarification` | 52.4% | 11/21 | 0.3046 | 0.3126 | [1.0, 1.0] | 127.4ms |
| `needs_physician_review_framing` | 75.0% | 15/20 | 0.1676 | 0.0589 | [1.0, 1.0] | 116.8ms |
| `is_complex_reasoning_required` | 50.0% | 10/20 | 0.2954 | 0.3253 | [1.0, 1.0] | 105.3ms |
| **Overall** | **65.0%** | **104/160** | — | — | — | — |

Latency note: measured wall-clock per HTTP call on CPU (no GPU available in
this environment), single-question-per-call, includes network round-trip
over loopback. Laya's own published benchmark (~33ms/question on a T4 GPU)
is not directly comparable to these CPU numbers; not claimed as a speed
finding, just reported for completeness.

Raw per-fixture predictions for both sources: `fallback_eval_v2_raw.json`,
`real_laya_eval_v2_raw.json`. Full summary JSON: `metrics_summary_v2.json`.

## Worst failure cases (with specifics)

### Fallback — systematic keyword-ordering weaknesses

**1. `classify_intent`, text: `"Compare recovery outcomes across the last three scenarios."`**
Expected: `complex_synthesis`. Fallback predicted: `simulation`. Root cause:
the fallback's SIMULATION bucket (checked 2nd in its if/elif cascade) has a
bare `\brecovery\b` trigger, which fires on the word "recovery" used here as
a noun describing already-completed data, not a request to run a new
recovery simulation. The COMPLEX_SYNTHESIS bucket's own `\bcompare\b` trigger
(checked 5th) never gets evaluated because the cascade already matched.
Recurs on at least 2 more fixtures in the set with the same "simulat"/
"recovery" substring collision (`"Rerun the ensemble..."`,
`"Explain the drop in cardiac output after the last scenario."`).

**2. `select_tool_family`, text: `"What's the current time in UTC?"`**
Expected: `NONE` (out-of-domain nonsense). Fallback predicted: `TWIN`. Root
cause: the bare `\bcurrent\b` keyword is meant to catch "what's the current
[cardiac value]" but has no domain guard, so it also fires on completely
unrelated uses of the word "current" (this exact failure mode was
specifically hypothesized and tested by Agent 21 across 3 fixtures — 2/3
were correctly predicted to fail this way, confirming it's a real, not
hypothetical, gap).

**3. `select_tool_family`, text: `"Get the component report for the LV free wall."`**
Expected: `TWIN` (GLOBAL_ARCHITECTURE.md's own tool registry lists
`get_component_report` under TWIN). Fallback predicted: `REPORT`. Root
cause: the REPORT bucket's bare `\breport\b` trigger is checked before the
TWIN bucket in the cascade, so any twin-scoped request containing the literal
word "report" is misrouted — a genuine ordering bug relative to the
project's own documented tool registry, not just a plausible-sounding label
disagreement.

**4. `needs_clarification`, text: `"that's helpful, thank you"`**
Expected: `False`. Fallback predicted: `True`. Root cause: the bare-referent
regex `\bthat\b` matches the substring "that" inside "that's" (the word
boundary falls on the apostrophe, not after the whole word), so an ordinary
pleasantry is flagged as needing clarification. A narrow but real
false-positive.

### Real Laya (zero-shot base checkpoint) — representative misses

**1. `is_complex_reasoning_required`: 10/20 correct, worse than a 50/50 coin
flip's expected value on this label mix (13 False / 7 True in the set).**
Inspecting `real_laya_eval_v2_raw.json`, the model's `noul` scores for the
7 genuinely-True cases (long, multi-part synthesis questions) cluster low
(mostly 0.15-0.40, i.e. confidently wrong), while its scores for several
False cases are pushed just over 0.5. This matches LAYA_RESEARCH.md's
warning that the un-fine-tuned base checkpoint's calibration and accuracy on
an unseen task/domain "could land anywhere in that range" between ~0.35 and
0.766 — here it landed at the low end for this specific binary gate.

**2. `needs_clarification`: 11/21 correct — the single worst real-Laya
decision type, and worse than the fallback's 20/21 by a wide margin.** The
zero-shot model appears to interpret "needs clarification" as closer to "is
this text hard to understand" (a text-difficulty read) rather than "is a
concrete referent unresolved," so it answers `False` on almost every case
regardless of ground truth (10/11 True cases were mispredicted `False`) —
consistent with a base checkpoint that has no exposure to BeatIT's specific
referent-resolution semantics, exactly the kind of narrow, task-specific
"typed decision" gap the RLCD fine-tuning process (which this environment
cannot run — no training data, no GPU budget for it) is meant to close.

**3. `classify_intent` is real Laya's one clear win over the fallback (75.9%
vs. 58.6%)** — e.g. it correctly classified `"Rerun the ensemble with
updated priors."` as `simulation` (a case the fallback's keyword cascade
misses, see failure #1 above) and correctly distinguished
`"unsupported"`/`"human_decision_required"` cases (out-of-domain or
therapy-choice questions) that the fallback's cascade is structurally
incapable of ever producing (those two labels don't appear anywhere in the
fallback's if/elif chain) — real semantic understanding beats a closed
keyword list on the genuinely open-ended, 11-way decision, even zero-shot.

## Recommendation for whoever next touches `laya_adapter.py` or `laya_policy.py`

1. **Fix the `choice`-type wire format bug** in `_call_systemone`'s
   `criteria` construction (send `{option: description, ...}`, not
   `{"options": [list]}`) before ever setting `LAYA_ENABLED=true` in any
   real environment — today it is silently a no-op for 2 of the 7 decision
   types.
2. **Do not conclude "fine-tune Laya" from these numbers alone** — Agent 23's
   `laya-specialization.md` conclusion (no fine-tuning justified, independent
   of accuracy, due to infra/data scarcity) still holds; these numbers now
   let `laya_policy.py`'s provisional 0.70 uniform threshold be replaced with
   real per-decision-type, per-source accuracy via its own
   `DecisionAccuracy.with_measured_accuracy` API, using the tables above.
3. **The fallback should stay the default/primary path for 6 of 7 decision
   types** on the evidence here (`classify_intent` is the one place a
   correctly-wired real Laya call would likely help even zero-shot) — this
   is a measured recommendation, not a guess.

## Docker / environment cleanup confirmation

- **No Docker container was ever created** by this task (a bare venv +
  `laya-serve` process was used instead, per item 1's own framing of the
  real pip-installable path). `docker ps -a` before and after this task is
  unchanged: `ghostrange-postgres-dev`, `ghostrange-valkey-dev` (both
  pre-existing, untouched), `echo-db-1` (pre-existing, stopped, untouched).
- The `laya-serve` background process this task started (PID tracked in
  `/tmp/laya_serve.pid` across two restarts, port 8931) was killed at the end
  of this task; confirmed via `ps -p <pid>` (no such process) and
  `ss -ltn | grep 8931` (port free).
- **A second, previously-undetected orphaned `laya-serve` process was found
  and also cleaned up.** After finishing the above, a final `pgrep -fa
  laya-serve` sweep (done as a last sanity check, not part of the planned
  steps) turned up a second server, PID 409501, bound to port 8971,
  `ps -o lstart,etime` showing it had been running since **11:13:17 the same
  day — 4h38m before this retry even started** and matching exactly the
  venv/checkpoint-cache creation timestamp (11:09). This is an orphaned
  process from the **prior interrupted Agent 22 attempt** referenced in
  `WAVE_5_HANDOFF.md` — that attempt evidently got far enough to start a
  real `laya-serve` server before the rate limit killed the agent process
  itself, leaving the server running headless. It was missed by this task's
  own required pre-check (`docker ps -a | grep -i laya`) because it is a bare
  process, not a Docker container — worth flagging for future retries of
  this task: **also run `pgrep -fa laya-serve` (or `ss -ltnp | grep -i
  python`) before concluding "no orphaned Laya instance exists."** It was
  killed (`kill 409501`) and confirmed stopped; port 8971 is free.
- The `/tmp/laya_eval_venv` (5.6GB) and `~/.cache/huggingface/hub/models--convaiinnovations--laya`
  (~8.1GB) were **left in place** (not deleted) — they were inherited from
  the prior interrupted attempt, are outside the git repo (`/tmp` and
  `~/.cache`, not tracked), cost nothing to leave, and mean any future agent
  that needs to re-verify or extend this real-Laya evaluation can restart the
  exact same server in seconds instead of re-downloading ~13.7GB. To reuse:
  `LAYA_HOST=127.0.0.1 LAYA_PORT=<free port> LAYA_DEVICE=cpu LAYA_PRELOAD=1 /tmp/laya_eval_venv/bin/laya-serve`.

## Artifacts preserved (this directory's `artifacts/` subfolder)

| File | Contents |
|---|---|
| `laya_pip_install.log` | Real `pip install "laya[serve]"` output (all "already satisfied" — confirms the prior attempt's install succeeded and was reused) |
| `laya_serve_startup_v2.log` | Real server startup log against the final fixture set's run, including the model's own calibration warning |
| `laya_real_server_raw.json` | Raw request/response pairs, correct wire format, 15-fixture stopgap set (kept for reference) |
| `laya_adapter_bug_evidence.json` | The unmodified `LayaAdapter` class's real output against the live server, proving the choice-type wire-format bug end to end |
| `fallback_eval_v2_raw.json` | Every one of the 160 fallback predictions vs. expected, with fixture text/context/category/notes |
| `real_laya_eval_v2_raw.json` | Every one of the 160 real-Laya predictions vs. expected, with the full raw server response (probabilities, confidence, latency) per case |
| `metrics_summary_v2.json` | The aggregated per-decision-type metrics tables above, machine-readable |
| `fallback_only_eval_raw.json`, `metrics_summary.json` | Corresponding raw output from the 15-example stopgap set (superseded, kept for the timeline record above) |
| `laya_serve_startup.log` | First server startup log (stopgap-set run) |
