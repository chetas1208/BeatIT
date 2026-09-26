# GLOBAL SUPPORT ARCHITECTURE
## THIS APPLIES TO EVERY WAVE AND EVERY SUB-AGENT

> Campaign invariant, not a wave deliverable. Every Wave 1–8 sub-agent in the
> BeatIT unified-assistant campaign must read this file before starting work,
> in addition to `AGENTS.md`, `Decisions.md`, `Progress.md`, and the most
> recent `docs/assistant/WAVE_*_HANDOFF.md`. No agent may invent a competing
> architecture merely because its local task could be finished faster that way.

---

## SYSTEM GOAL

BeatIT must expose:

- ONE assistant
- ONE conversation
- ONE physician-support system
- ONE tool layer
- ONE decision-control plane
- ONE context architecture
- ONE artifact model
- ONE provenance system

The implementation may contain multiple deterministic engines, models,
decision systems, safety checks, background services, and tool handlers —
but ordinary users experience **ONE BeatIT Copilot.**

---

## TOP-LEVEL ARCHITECTURE

```text
                           USER
                             │
                             ▼
                    BEATIT COPILOT UI
                             │
                             ▼
                   CONVERSATION SESSION
                             │
               context + message + audience
                             │
                             ▼
                  REQUEST CONTROL PLANE
                             │
              ┌──────────────┼───────────────┐
              │              │               │
              ▼              ▼               ▼
          INPUT          CONTEXT         SAFETY /
        VALIDATION       RESOLUTION       POLICY
              │              │               │
              └──────────────┼───────────────┘
                             ▼
                  SYSTEM-1 DECISION LAYER
                             │
                           LAYA
                             │
                             ▼
                     EXECUTION POLICY
                             │
          ┌──────────────────┼────────────────────┐
          │                  │                    │
          ▼                  ▼                    ▼
    DETERMINISTIC         TOOL CALL            SYSTEM-2
       ANSWER                │                    LLM
                             │
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
           TWIN          EVIDENCE       SIMULATION
             │               │               │
             ├───────────────┼───────────────┤
             ▼               ▼               ▼
          COMPARE          REPORT        MISSING PIECE
             │               │               │
             └───────────────┼───────────────┘
                             ▼
                   CANONICAL DOMAIN DATA
                             │
                             ▼
                    RESPONSE ASSEMBLER
                             │
                 ┌───────────┼───────────┐
                 ▼           ▼           ▼
             NUMERIC      PROVENANCE    SAFETY
             VALIDATOR    VALIDATOR     VALIDATOR
                 │           │           │
                 └───────────┼───────────┘
                             ▼
                       ARTIFACT LAYER
                             │
                             ▼
                      BEATIT COPILOT
```

---

## TWO PLANES

**CONTROL PLANE** — intent, routing, context, permissions, model selection,
tool selection, safety, validation, orchestration. Components: Laya,
deterministic router, NVIDIA LLM router, guardrails, conversation orchestrator.

**DATA / COMPUTATION PLANE** — truth. CardiacTwinState, TwinSnapshot,
TwinTimeline, deterministic physiology, PV calculations, ECG-derived
canonical metrics, causal propagation, probabilistic ensemble, Shadow Trial,
sensitivity, Missing Piece, provenance, persisted evidence.

**THE CONTROL PLANE MUST NEVER BECOME THE SOURCE OF CARDIAC TRUTH.**

---

## SYSTEM-1 (Laya) VS SYSTEM-2 (NVIDIA LLM)

**System 1 — Laya**: fast typed decisions only — intent, tool family, needs
evidence?, needs deterministic calculation?, needs simulation?, needs
clarification?, needs physician-review framing?, needs provenance?, simple
vs complex reasoning? Laya does not produce the final medical explanation,
does not calculate physiology, does not prescribe treatment.

**System 2 — NVIDIA LLM**: explanation, synthesis, summarization,
contextual Q&A, physician brief, report narrative, interpreting deterministic
results, multi-source evidence synthesis. Receives canonical data; does not
replace it.

Laya's own benchmark docs show its specialized typed-decision checkpoint
substantially outperforming the base checkpoint — evaluate/calibrate before
trusting any zero-shot routing threshold (see Wave 5 in the main campaign).

---

## EXECUTION CLASSES

Every request should resolve to one of:

```text
DIRECT_STATE_READ
EVIDENCE_RETRIEVAL
DETERMINISTIC_COMPUTATION
SIMULATION
ARTIFACT_GENERATION
GENERATIVE_EXPLANATION
COMPLEX_SYNTHESIS
CLARIFICATION_REQUIRED
INSUFFICIENT_EVIDENCE
HUMAN_DECISION_REQUIRED
UNSUPPORTED
```

No arbitrary agent chains when one category solves the request.

### Fast path
`"What is the current EF?"` → Laya/router → DIRECT_STATE_READ →
CardiacTwinState → 43% → response. No LLM needed.

### Grounded explanation path
`"Why did stroke volume fall in the experiment?"` → System-1 →
GENERATIVE_EXPLANATION + requires causal trace → ScenarioResult +
CausalTrace → NVIDIA LLM → numeric validator → grounded explanation.

### Complex physician path
`"Summarize what changed over the last month and explain which findings are
directly observed versus model-derived."` → System-1 → COMPLEX_SYNTHESIS →
Timeline + Snapshots + Evidence + Provenance → deep reasoning model → claim
validator → physician response.

**Tool-first rule:** if a deterministic tool can answer the factual part,
use it. LLM may explain the output; it must never regenerate the answer
independently.

---

## SINGLE TOOL REGISTRY

All assistant tools live behind ONE logical registry (`BeatITToolRegistry`
or equivalent). No wave may create competing registries
(`physician_tools_v2`, `chat_tools`, `copilot_tools`, `laya_tools`,
`page_tools`, ...).

Categories: **TWIN** (get_current_twin, get_snapshot, get_timeline,
get_component, get_component_report) · **EVIDENCE** (get_evidence,
get_provenance, get_source, get_evidence_completeness) · **PHYSIOLOGY**
(get_pv_loop, get_ecg_state, get_causal_trace) · **EXPERIMENT**
(create_scenario, update_scenario, run_scenario, run_ensemble,
run_shadow_trial) · **COMPARE** (get_pair, get_comparison,
get_component_comparison) · **UNCERTAINTY** (run_missing_piece,
get_uncertainty_drivers, get_evidence_priority) · **REPORT**
(generate_component_report, generate_physician_brief,
generate_computational_report).

### Tool safety levels

- **T0 — read only** (get_twin, get_evidence, get_provenance): may execute automatically.
- **T1 — computational** (run_ensemble, run_shadow_trial, run_missing_piece): auto-execute when clearly requested; must be visibly labeled simulation/computation.
- **T2 — application state action** (change_selected_snapshot, open_compare, focus_component, create_scenario): allowed when clearly aligned with user intent.
- **T3 — high-stakes clinical action** (prescribe medication, change dosage, place medical order, diagnose autonomously, determine emergency disposition): **NOT ordinary BeatIT tools.** Never executed autonomously — support human decision-making instead.

---

## PHYSICIAN SUPPORT ARCHITECTURE

Physician support is **not** another application or chatbot — it's a
policy/audience mode within BeatIT Copilot:

```text
BeatIT Copilot
     ├── general presentation policy
     └── physician presentation policy
```

Same conversation, tools, provenance, models, decision layer, context.
Different terminology, information density, evidence detail, artifact
defaults, assumptions shown, provenance depth.

Physician Mode should increase evidence density, provenance, raw
measurements, assumptions, methodology, uncertainty. It must **not**
increase autonomous treatment authority or unsupported diagnostic certainty.

### Decision support object (no `recommended_treatment` field, ever)

```text
DecisionSupportBundle
  question
  clinical_context
  observed_evidence[]
  derived_evidence[]
  simulated_results[]
  uncertainty[]
  missing_evidence[]
  conflicts[]
  assumptions[]
  provenance[]
  limitations[]
  possible_interpretations[]
```

Laya can decide: does this need evidence retrieval? simulation? is evidence
insufficient? should uncertainty/physician-review framing apply? which
capability should answer? Laya **cannot** decide which therapy a patient
should receive.

---

## GUARDRAIL LAYERS

Reference pattern (NVIDIA NeMo Guardrails' rail separation is useful
prior art — evaluate it as an implementation reference, but BeatIT's own
deterministic validators remain required; do not depend exclusively on a
probabilistic guardrails framework):

- **Input rail** — malformed request, high-stakes intent, injection attempts, invalid context.
- **Retrieval rail** — retrieved context belongs to correct patient, provenance exists, unrelated evidence excluded.
- **Execution rail** — tool arguments, patient identity, snapshot identity, simulation boundaries, tool result schema.
- **Output rail** — numerical claims, provenance, simulation labeling, unsupported recommendations, observed/derived/simulated distinction.

### Numerical claim gate

Any generated response containing canonical numbers (EF, SV, CO, MAP, HR,
EDV, ESV, QTc, ...) must have those numbers extracted and diffed against the
canonical tool payload. Mismatch → reject/regenerate/fallback. No exceptions.

### Provenance gate

Factual physician claims carry internal provenance references; UI may keep
them visually compact (e.g. `EF 43%  [source]`).

---

## ARTIFACT ARCHITECTURE

Chat text and structured artifacts are separate. Prefer a short
conversational summary + `[ Open artifact ]` over dumping large structured
output into chat.

### Artifact contract

```text
id
type
title
conversation_id
patient_id
snapshot_id (if relevant)
source_tool_ids[]
provenance[]
payload
created_at
version
```

Artifacts are views over canonical results — never a second source of truth.

---

## CONTEXT ARCHITECTURE

ONE canonical assistant context, no page-specific second context system:

```text
ConversationContext
  conversation_id
  audience
  patient_id
  snapshot_id
  component_id
  product_space
  scenario_id
  ensemble_id
  shadow_trial_id
  pair_id
  target_metric
  synthetic_status
```

Context updates from user language, UI interaction, tool results, and
product navigation (click LV → component_id=LV; scrub timeline →
snapshot_id updates; open paired Twin #284 → pair_id=284). The assistant
must resolve "this"/"here"/"why did it change?" from this context without
the user restating it.

### UI command architecture

Assistant may propose/trigger safe application actions —
`focus_component(LV)`, `open_evidence(EF)`, `open_compare(pair_284)`,
`set_target_metric(delta_sv)` — that manipulate UI context only, never
canonical patient evidence.

**No UI complexity leak:** ordinary users never see "Laya chose route 4",
"Nemotron Super selected", "Safety Guard running", "Agent graph node 9".
Normal UI shows only "BeatIT Copilot" (developer diagnostics may exist
behind an explicit flag).

---

## MODEL ROUTER

```text
Can deterministic tool answer completely?
  YES → no LLM
  NO  → simple explanation?
          YES → FAST MODEL
          NO  → complex synthesis/reasoning?
                  YES → DEEP MODEL
```

Current research hypotheses (benchmark before locking — see
`docs/assistant/NVIDIA_MODEL_RESEARCH.md` and Wave 6):
FAST/agentic ≈ Nemotron 3.5 Lightning class; DEEP ≈ Nemotron 3 Super class;
SAFETY ≈ Nemotron Safety Guard class. Model availability changes — always
benchmark actual live endpoints before locking a routing table.

Three NVIDIA keys are a **reliability pool**, not three personalities:
health-aware rotation, rate-limit failover, temporary quarantine, retry
policy. Never expose key values, anywhere, ever.

---

## OBSERVABILITY

Every assistant request produces a safe internal trace: request_id,
conversation_id, System-1 decision (+ confidence metadata if applicable),
execution class, tools invoked, model selected, latencies, validation
status, artifact IDs, fallbacks. Never store hidden reasoning — store
decisions and operational metadata only.

## LAYA EVALUATION REQUIREMENT

Never deploy a routing threshold merely because Laya outputs a probability.
Required metrics on BeatIT-specific fixtures: accuracy, confusion matrix,
Brier score, ECE, abstention, false-high-confidence rate.

## FALLBACK TREE

```text
Laya unavailable        → deterministic router
Fast model unavailable  → deep model / deterministic result
Deep model unavailable  → fast model where sufficient / deterministic result
All NVIDIA unavailable  → canonical BeatIT tools still work
Safety model unavailable → deterministic BeatIT safety rules
```

---

## INTER-WAVE CONTRACT

**Start of every wave** — agents must read: this file, the previous wave's
handoff, shared contracts (schemas, registry, context object), and the
actual implementation (not just docs).

**End of every wave** — the lead must ask: did this wave create a second
router? context? tool registry? safety layer? conversation store? artifact
format? provider abstraction? physician assistant? **If yes: consolidate
before continuing.**

Every `WAVE_X_HANDOFF.md` must include: What Was Implemented, Shared
Contracts Changed, Files Added, Files Modified, Architecture Decisions,
Tests, Known Failures, Security/Medical Risks, Next-Wave Dependencies, and
**Global Architecture Compliance: YES/NO**. If NO, do not spawn the next
wave until repaired.

---

## FINAL ARCHITECTURAL INVARIANTS

At the end of all waves there must be exactly:

```text
1 user-facing chat
1 conversation backend
1 conversation context
1 tool registry
1 model router
1 Laya decision layer
1 deterministic routing fallback
1 artifact system
1 physician-support policy
1 provenance architecture
1 numerical validation boundary
```

Multiple implementations of any of these require explicit documented
justification in the relevant wave handoff.

---

## THE SIMPLE MENTAL MODEL

```text
Laya decides WHAT PATH.
BeatIT tools determine WHAT IS TRUE.
NVIDIA models explain WHAT IT MEANS.
Guardrails determine WHAT IS ALLOWED.
Provenance shows WHERE IT CAME FROM.
The physician decides WHAT TO DO.
```
