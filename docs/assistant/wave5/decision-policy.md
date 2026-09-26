# Wave 5 — Decision policy: when to trust a Laya/fallback decision

**Module:** `python/hearttwin/assistant/laya_policy.py`
**Tests:** `python/hearttwin/tests/test_laya_policy.py` (45 tests, all passing)
**Agent:** Agent 24, "Decision Policy Engineer"
**Status:** thresholds are PROVISIONAL — see "Verification of Agent 22's numbers" below.

---

## 1. Why this exists

`orchestrator.py` currently uses every `LayaAdapter` decision — whether it
came from a real Laya HTTP call or the deterministic keyword fallback in
`laya_adapter.py` — directly, with **no confidence gating at all**. This
module adds that gate as a standalone, unwired policy layer: for each of the
7 named decision types Laya/fallback can produce, it defines when the
orchestrator *should* trust the decision vs. when it should treat it as
uncertain and prefer a more conservative outcome (`CLARIFICATION_REQUIRED`,
or `INSUFFICIENT_EVIDENCE` in the tool-dispatch path).

Per the task brief and `AGENTS.md`/`GLOBAL_ARCHITECTURE.md`'s **LAYA
EVALUATION REQUIREMENT** ("Never deploy a routing threshold merely because
Laya outputs a probability"), this module does not invent thresholds from
first principles. It is built to be driven by Agent 22's real per-decision-
type accuracy measurements, and ships honest, explicitly-labeled provisional
defaults until those numbers exist.

## 2. Why a routing mistake is a UX problem, not a safety problem

This is the load-bearing argument for why it's acceptable to ship
provisional thresholds at all (rather than blocking this whole module on
Agent 22's numbers). It rests on the pipeline order in
`python/hearttwin/assistant/orchestrator.py`, not on anything Laya itself
guarantees:

- `orchestrator.handle_message` step (a) — `classify_request_safety` —
  **runs before context resolution and before any Laya call, unconditionally**
  (`orchestrator.py` lines 256–260). The module docstring is explicit about
  why: *"a request that must be blocked is blocked regardless of what 'this'
  refers to, and Laya (System-1) is explicitly barred from clinical-safety
  authority ... safety must never depend on, or be reachable only after, a
  routing decision."*
- That means every emergency/diagnosis/treatment block
  (`safety_validator.classify_request_safety`, which wraps
  `intake_agent.py`'s rule-based classifier) fires **regardless of what
  Laya or the fallback would have decided** for intent/tool-family/etc. A
  Laya decision this policy module gates can only ever run *after* that gate
  has already let the request through.
- Symmetrically, step (e) — `check_output_safety` + `validate_numeric_claims`
  — runs on every tool-grounded response before it's returned, independent
  of which tool family Laya/fallback picked to get there.
- So the *worst case* of a wrong Laya/fallback decision this module could
  ever gate is: the orchestrator tries the wrong tool family and returns
  `INSUFFICIENT_EVIDENCE`/`UNSUPPORTED` (a bad but honest answer), or asks
  an unnecessary clarifying question, or classifies intent into the wrong
  execution class. None of those paths can produce a diagnostic, treatment,
  medication, or emergency-triage claim — those are categorically blocked
  upstream, before Laya ever runs, by a system this module does not touch.

This is also why `laya_policy.py` is safe to leave **unwired** this wave
(see §5): its absence changes UX confidence, not safety posture. The
orchestrator today just always trusts the decision; that is already the
"maximally permissive" state this policy would only ever make *more*
conservative, never less.

## 3. The 7 decision types and their thresholds

Source: `python/hearttwin/assistant/laya_adapter.py`'s 7 public
`LayaAdapter` methods (verified identical in
`python/hearttwin/tests/test_laya_adapter.py::ALL_METHOD_NAMES` and this
module's own `DecisionType` enum).

| Decision type | Current accuracy | Defer threshold | Source | Reasoning |
|---|---|---|---|---|
| `classify_intent` | 0.70 | 0.70 | **provisional-default** | Highest-fanout decision (11 `ExecutionClass` options), fallback is keyword-only regex (`_fallback_classify_intent`). Most exposed to misroute risk of the 7 — kept at the floor, not given benefit of the doubt. |
| `select_tool_family` | 0.70 | 0.70 | **provisional-default** | 8-way choice (7 registry categories + `NONE`). Mistakes here are cheap in *this specific codebase* because `orchestrator._select_and_execute_tool` already falls back to `INSUFFICIENT_EVIDENCE`/`UNSUPPORTED` rather than fabricating a result when no candidate tool's required context fields resolve. |
| `needs_evidence_retrieval` | 0.70 | 0.70 | **provisional-default** | Binary. A false negative just costs a missed evidence lookup the user can re-ask for. |
| `needs_simulation` | 0.70 | 0.70 | **provisional-default** | Binary. Routes to, never computes inside, the deterministic simulation core — `cardiac_state.py`/`hemodynamics.py`/`recovery_sim.py` are untouched regardless of this decision's correctness. |
| `needs_clarification` | 0.70 | 0.70 | **provisional-default** | The task brief's own worked example names this exact decision type as a case where measured accuracy might come in low (its example: "55%"). Flagged specially — see §4. |
| `needs_physician_review_framing` | 0.70 | 0.70 | **provisional-default** | Binary, presentation-density only (`GLOBAL_ARCHITECTURE.md`'s physician-support policy) — never affects diagnostic/treatment authority either way. |
| `is_complex_reasoning_required` | 0.70 | 0.70 | **provisional-default** | Binary. Currently inert in production: `orchestrator.py`'s own docstring states "No LLM / model-router integration exists in this wave," so nothing reads this decision's routing output yet. |

**Every single threshold above is provisional**, all pinned to the same
0.70 floor taken directly from the task brief's own example ("always defer
to clarification below 70% fallback-observed accuracy for that decision
type — as a placeholder, explicitly marked provisional"). None are derived
from a measurement. `get_policy_summary()` reports `source:
"provisional-default"` and a `reference` string starting with `"PENDING:"`
for all 7 so this can never be mistaken for real data by a downstream
consumer.

Why one shared floor instead of 7 different guessed numbers: guessing 7
distinct plausible-sounding provisional values would create false precision
— it would look like per-type calibration had already happened when it
hasn't. One honest, uniform, clearly-labeled floor is more defensible than
7 fabricated ones.

### Why `decision_source` ("laya" vs "fallback") does not change the gate

`should_defer_to_clarification` accepts `decision_source` for forward
compatibility but currently treats "laya" and "fallback" identically for a
given decision type. This is intentional, not an oversight:

- A real Laya call's `raw_score` is documented in `laya_adapter.py` as
  **uncalibrated** (ECE 0.213) — not usable as a probability of correctness.
- The fallback path has no score at all — it's a regex match with no
  per-call notion of certainty.
- The only signal that's honest for *either* source today is measured,
  ex-post accuracy **for that decision type as a whole**, which is exactly
  what `DecisionAccuracy.accuracy` models. Once Laya's calibration campaign
  (referenced in `laya_adapter.py`) produces a trustworthy per-call score,
  `decision_source`-sensitive gating (e.g. trusting a well-calibrated Laya
  call at a lower type-level threshold than a same-type fallback call) is
  the natural next extension — the parameter is already there for it.

## 4. Verification of Agent 22's numbers

Checked for `docs/assistant/wave5/laya-evaluation.md` twice, ~20 seconds
apart, before writing this module and again immediately before writing this
doc:

```
$ find docs/assistant -iname "*laya-evaluation*"
$ find . -iname "*laya-evaluation*"
(no output — file does not exist in the tree)
```

`docs/assistant/wave5/` did not exist at all until this task created it.
**Agent 22's real numbers were not available at any point during this
task.** Per the task's own fallback instruction, `laya_policy.py` was
therefore built fully parameterized (`DecisionAccuracy`, `DecisionPolicy`,
`DEFAULT_POLICY`) so that once `laya-evaluation.md` lands, a future step can
produce a measured policy without touching `should_defer_to_clarification`
or any call site:

```python
from python.hearttwin.assistant.laya_policy import DEFAULT_POLICY, DecisionPolicy, DecisionType

measured_needs_clarification = DEFAULT_POLICY.get(DecisionType.NEEDS_CLARIFICATION).with_measured_accuracy(
    0.55,  # Agent 22's real number
    reference="docs/assistant/wave5/laya-evaluation.md#needs_clarification",
)
policy = DecisionPolicy(needs_clarification=measured_needs_clarification)
# ... repeat per decision type, then pass `policy=` at each call site.
```

### Special note on `needs_clarification`

If Agent 22's measurement for `needs_clarification` itself comes in low
(the task brief's own example: 55%), the correct fix is **not** to raise
this policy's `defer_threshold` for that type — a low-accuracy
`needs_clarification` decision means the *fallback's default answer itself*
is unreliable (it under- or over-asks), not that the confidence bar for
trusting it should move. The right response is to change
`laya_adapter._fallback_needs_clarification`'s default bias (e.g. toward
asking more often) — that is Agent 22/an adapter-owning agent's job, not
this policy module's; `laya_policy.py` only decides whether to trust
whatever `needs_clarification` currently answers, not what it should
answer.

## 5. Clinical-authority structural guard

`laya_policy.py` can never be asked to gate diagnosis, treatment,
medication, or emergency triage — those are not Laya decisions at all (they
are `intake_agent.py`'s rule-based blocks, run via
`safety_validator.classify_request_safety`, entirely untouched by this
module). Two layers of defense:

1. **Closed enum** — `DecisionType` lists exactly the 7 real
   `LayaAdapter` method names. A clinical term can't be added as a
   `DecisionType` member without literally editing this file's enum.
2. **Runtime substring guard** — `should_defer_to_clarification` calls
   `_reject_clinical_authority_misuse(decision_name)` first, before doing
   anything else (including before the `DecisionType(...)` lookup, so a
   clinical-sounding *and* unrecognized name still raises rather than
   falling through to the "unknown decision -> defer" path). It matches
   case-insensitive substrings (`diagnos`, `treatment`, `treat`, `medicat`,
   `dosage`, `dose`, `prescri`, `emergency`, `triage`) and raises
   `ClinicalAuthorityRefused`, a `RuntimeError` subclass, so a misuse
   attempt fails loudly instead of silently gating a clinical decision.

Verified in `test_laya_policy.py`:

- `test_clinical_authority_guard_raises_loudly_for_misuse` — parametrized
  over `diagnose_condition`, `recommend_treatment`, `select_medication`,
  `adjust_dosage`, `determine_emergency_disposition`, `triage_level`,
  `DIAGNOSE` (case-insensitivity), `should_treat_with_beta_blocker`
  (substring inside a longer name) — all raise `ClinicalAuthorityRefused`.
- `test_clinical_authority_guard_never_fires_on_a_real_decision_name` —
  none of the 7 real decision names false-positive.
- `test_clinical_authority_guard_checked_before_unknown_name_fallback` —
  confirms the guard fires even for a name that is *also* unrecognized,
  rather than being masked by the "unknown -> defer" fallback path.

```python
>>> from python.hearttwin.assistant.laya_policy import should_defer_to_clarification
>>> should_defer_to_clarification("recommend_treatment", "laya")
Traceback (most recent call last):
  ...
laya_policy.ClinicalAuthorityRefused: Refusing to gate 'recommend_treatment': this policy
module has no clinical authority. Diagnosis/treatment/medication/emergency-triage blocking
is handled by safety_validator.classify_request_safety (rule-based, runs before Laya) — it
is not, and must never become, a Laya decision type.
```

## 6. Integration point (NOT wired up this wave)

Per the task constraints, `orchestrator.py` was **not** modified. The
intended integration point for a follow-up wave, once this policy module has
been reviewed and ideally once Agent 22's real numbers exist, is in
`orchestrator.handle_message`, immediately after each of the two decision
calls it currently uses unconditionally:

```python
# python/hearttwin/assistant/orchestrator.py, step (c) — current code (lines 268-274):

intent_decision = await laya.classify_intent(request.message, request.context.model_dump())
if intent_decision.chosen == ExecutionClass.CLARIFICATION_REQUIRED.value:
    return _clarification_response()
family_decision = await laya.select_tool_family(request.message, request.context.model_dump())

# Proposed addition (this wave's follow-up, not this task):

from python.hearttwin.assistant.laya_policy import should_defer_to_clarification

intent_decision = await laya.classify_intent(request.message, request.context.model_dump())
if intent_decision.chosen == ExecutionClass.CLARIFICATION_REQUIRED.value:
    return _clarification_response()
if should_defer_to_clarification("classify_intent", intent_decision.source):
    return _clarification_response()

family_decision = await laya.select_tool_family(request.message, request.context.model_dump())
if should_defer_to_clarification("select_tool_family", family_decision.source):
    return _clarification_response()
```

Notes for whoever wires this in:

- Both `intent_decision` and `family_decision` are `ChoiceDecision` objects
  (`laya_adapter.py`), which already carry `.source: Literal["laya",
  "fallback"]` — no new plumbing needed to get the second argument.
- `should_defer_to_clarification` never raises for these two real decision
  names (`"classify_intent"`, `"select_tool_family"`) — the
  `ClinicalAuthorityRefused` path is unreachable from legitimate
  orchestrator usage; it exists purely as a guard against future misuse.
- The other 5 decision types (`needs_evidence_retrieval`,
  `needs_simulation`, `needs_clarification`,
  `needs_physician_review_framing`, `is_complex_reasoning_required`) are
  not currently called anywhere in `orchestrator.py` (confirmed by reading
  the full file — only `classify_intent` and `select_tool_family` are
  invoked). They have policy entries ready in `DEFAULT_POLICY` for whichever
  future wave wires them into a call site that uses them.
- This wave deliberately leaves `orchestrator.py` untouched per the task's
  file-ownership constraint; wiring the snippet above in is explicitly a
  "follow-up integration step once this policy module is reviewed."

## 7. `get_policy_summary()` for observability

Returns:

```python
{
  "decisions": {
    "classify_intent": {
      "accuracy": 0.7,
      "defer_threshold": 0.7,
      "is_trustworthy": true,
      "source": "provisional-default",
      "reference": "PENDING: docs/assistant/wave5/laya-evaluation.md not yet available",
      "note": "...",
    },
    # ... all 7 decision types
  },
  "all_measured": false,
  "pending_evaluation_doc": "docs/assistant/wave5/laya-evaluation.md",
}
```

`all_measured` lets a future dashboard or CI check assert "every threshold
is grounded in real data" without inspecting each of the 7 entries
individually — it is `False` today and should be treated as a signal that
this policy is still running on provisional defaults until Agent 22's
numbers land and a measured `DecisionPolicy` is built via
`DecisionAccuracy.with_measured_accuracy` (see §4).

## 8. Files touched this wave

New files only, per task constraint:

- `python/hearttwin/assistant/laya_policy.py`
- `python/hearttwin/tests/test_laya_policy.py`
- `docs/assistant/wave5/decision-policy.md` (this file)

No existing file was modified. `git status` was checked before starting;
several other files were already modified/untracked in the shared tree from
concurrent work (Codex / other wave agents) and were left untouched.
