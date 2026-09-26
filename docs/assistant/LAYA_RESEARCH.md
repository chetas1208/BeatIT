# Laya Research Report (Wave 1, Agent 2 — "Laya Researcher")

Researched 2026-09-26 from primary sources (GitHub repo, GitHub profile, docs site,
BENCHMARKS.md) plus secondary press coverage used only for corroboration, never as
sole evidence. Where a fetch failed or a claim could not be independently confirmed,
this is stated explicitly rather than inferred.

## Summary & Verdict

Laya (`NandhaKishorM/laya`, Apache-2.0) is a real, actively documented open-source
project: a small (322M–421M param), non-autoregressive encoder model that answers
typed `choice`/`score`/`noul` (yes/no) questions over text in a single forward pass,
with a router that auto-selects a checkpoint per language and an HTTP server that
speaks a Jev-compatible wire protocol. It is a plausible candidate for BeatIT's
"System-1" fast-decision layer **for non-clinical, internal routing/software
decisions only** (e.g., "does this upload look like a DICOM file," "should this
support ticket route to billing vs. tech," UI intent classification) — it is fast
(~33ms/request claimed), cheap to self-host, and has a real (if unpolished)
calibration story. It is **not suitable, and must never be used, as a source of
authoritative cardiac diagnosis, treatment, or emergency-triage output** — its own
published benchmark shows non-trivial calibration error (ECE 0.213 on its
specialized checkpoint) even after fine-tuning, and its zero-shot/base-checkpoint
accuracy is weak (~0.35–0.36 on its own typed-decisions eval, ~0.23–0.37 macro
across 51 languages). Before any production threshold is trusted, BeatIT would need
its own calibration campaign on BeatIT-specific decision types (see last section) —
Laya's published numbers are on its own benchmark suite, not on cardiac-domain data.

## Verified Facts

- **License: Apache License 2.0.** Confirmed both from the repo README footer and
  by fetching the raw `LICENSE` file, which is the standard Apache-2.0 template text
  (no filled-in copyright line — this is normal/expected for a GitHub-added
  Apache-2.0 LICENSE file, not a red flag).
  Source: https://github.com/NandhaKishorM/laya , https://raw.githubusercontent.com/NandhaKishorM/laya/main/LICENSE
- **Architecture: non-autoregressive, encoder-based, with typed decision heads.**
  Laya does not generate text; it runs a single forward pass through an encoder
  (ModernBERT-large for the base `laya` checkpoint, 421M params, 512-token context;
  mmBERT-base for `laya-multilingual`, 322M params, up to 8,192 tokens) and reads
  structured decision-head outputs (per-option probabilities). Trained via
  reinforcement learning against strictly proper scoring rules (the project calls
  this "RLCD"). A `Router` component performs sub-millisecond script/language
  detection and dispatches to the right checkpoint automatically.
  Source: https://github.com/NandhaKishorM/laya
- **Three decision types confirmed: `choice`, `score`, `noul`.** "Noul" is Laya's
  (and the wider Jev-alternative ecosystem's) term for a yes/no probability
  decision. Source: https://nandhakishorm.github.io/laya , https://github.com/NandhaKishorM/laya
- **API shape (Python):** `Router(preload=True)` then
  `router.predict(state, questions)`, where `state` is a dict of raw text/context
  and `questions` is a dict mapping a decision name to
  `{"type": "choice"|"score"|"noul", "instructions": ..., "criteria": {...}}`.
  Returns `result["answers"][<name>][<type>]`. Also supports `predict_batch()`
  (packs multiple states into shared forward passes) and `predict_long()`
  (overlapping-window scan + aggregation for long documents). Direct checkpoint
  loading via `laya.load("convaiinnovations/laya")` is also shown.
  Source: https://github.com/NandhaKishorM/laya
- **HTTP server: real and Jev-wire-compatible.** `pip install "laya[serve]"` then
  `laya-serve` (configurable via `LAYA_DEVICE`, `LAYA_PRELOAD` env vars) exposes
  `POST /v1/systemone`, described as matching "TypeSafe Jev's API" wire protocol.
  Source: https://github.com/NandhaKishorM/laya
- **Prediction hooks / schema-driven decisions:** documented as a middleware
  mechanism to "log, redact, cache or gate every decision without forking" the
  library — i.e., hook points around each `predict()` call rather than a fork of
  the core code. The docs site also describes retrieving structured values via
  JSON Schema or Pydantic models. The exact hook API surface was not visible in
  the fetched excerpt — treat the mechanism as directionally confirmed but not
  fully specified; read the actual hooks module/docs page before relying on it.
  Source: https://nandhakishorm.github.io/laya
- **Docker: official, multiple compose files exist in the repo.** `compose.yaml`
  (default), `compose.cuda.yaml` (GPU), `compose.http.yaml` (HTTP server mode),
  `compose.spark.yaml` (Spark integration). The docs site additionally mentions
  ARM64 and DGX Spark container builds. Source: https://github.com/NandhaKishorM/laya ,
  https://nandhakishorm.github.io/laya
- **LangChain/LangGraph integration: a real code module exists, not just docs.**
  The README shows `from laya.integrations.langchain import LayaRouter,
  LayaGuardrail` with working-looking constructor args
  (`criteria=...`, `confidence_threshold=0.80`, `action="raise"`). A follow-up
  directory-listing fetch of `github.com/NandhaKishorM/laya/tree/main/laya/integrations`
  confirmed the directory exists and contains `__init__.py` and `langchain.py`.
  **Caveat:** the file's *contents* were not readable through the fetch tool (GitHub's
  rendered tree view doesn't show file bodies), so the classes' actual behavior is
  unverified — only their existence as a real module is confirmed. Separately, the
  docs-site page `nandhakishorm.github.io/laya/langchain.html` returned **HTTP 404**
  (unreachable) at fetch time, and a general docs-site summary described the
  LangChain integration as "documentation-based" with "no separate adapter package
  mentioned" — that summary appears to be wrong or based on a stale/incomplete
  crawl of the docs site; the GitHub source is the stronger, more direct evidence
  here. Source: https://github.com/NandhaKishorM/laya ,
  https://github.com/NandhaKishorM/laya/tree/main/laya/integrations (module exists,
  contents unread) — docs.md page 404: https://nandhakishorm.github.io/laya/langchain.html
- **Fine-tuning path:** a Kaggle notebook,
  `notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb`, trains on custom
  domain data using RLCD-style rewards, sized for 2×T4 GPUs (i.e., runnable on
  Kaggle's free GPU tier — a real, low-compute-barrier path). A separate
  fine-tuning notebook for "browser-agent" specialization is also referenced by the
  docs site. Exact data format for training examples was not visible in the
  fetched excerpts — read the notebook itself before attempting a BeatIT-specific
  fine-tune. Source: https://github.com/NandhaKishorM/laya , https://nandhakishorm.github.io/laya
- **Benchmark methodology (`BENCHMARKS.md`):** typed-decisions eval uses 400 cases
  / 2,000 decisions, scored on accuracy, soft accuracy, Brier score, ECE
  (expected calibration error), and score MAE. Separately, all 51 MASSIVE-corpus
  languages are tested on 20-option intent classification (random-chance baseline
  = 0.050). Latency is measured on Tesla T4 GPU across 1–50 questions/call, plus
  CPU/other-hardware variants (GB10, Ryzen 9, Intel Arc, AMD EPYC). Calibration is
  reported both "as shipped" and after a temperature-refit on held-out data.
  Source: https://raw.githubusercontent.com/NandhaKishorM/laya/main/BENCHMARKS.md
- **Calibration/accuracy numbers actually published (quote/paraphrase, see caveat
  below):** on the typed-decisions checkpoint: accuracy **0.766**, Brier **0.061**,
  ECE **0.213** — compared to a stated Jev baseline of accuracy **0.727**, ECE
  **0.144** on the same eval. Base (non-fine-tuned) checkpoints scored much lower
  on this same typed-decisions eval: **0.362** and **0.352** zero-shot. On the
  51-language macro intent eval: **0.2269** (base `laya`) vs **0.3661**
  (`laya-multilingual`), with 45/51 languages clearing 3× the random baseline for
  the multilingual checkpoint. Reported ECE-before/after-temperature-refit:
  `laya` 0.466 → 0.081; `laya-multilingual` 0.314 → 0.106. Speed: ~32.8 ms for 1
  question and ~337.4 ms for 50 questions on T4 (laya-multilingual); claimed
  "6–7× faster" than Jev. **Notable nuance worth flagging to the team:** the
  fine-tuned checkpoint has *higher accuracy* than the stated Jev baseline (0.766
  vs 0.727) but *worse* calibration error (ECE 0.213 vs 0.144) — i.e., "more
  accurate" and "better calibrated" are not the same claim here, and Laya's own
  numbers show a real calibration gap even on its own home-turf benchmark.
  Source: https://raw.githubusercontent.com/NandhaKishorM/laya/main/BENCHMARKS.md
  **Caveat:** these figures were retrieved via an automated fetch/summarization
  tool (not a raw-text diff/grep), so treat exact digits as "as reported by the
  tool" pending a direct read of the raw file before anyone codes a hard threshold
  against them.

## Unverified / Could-Not-Confirm Claims

- **The prior report's claim that Laya was "created by Ananda Kishore, a
  mathematician" is FALSE / NOT SUPPORTED and should be dropped, not merely
  flagged as unverified.** Independently checked three sources:
  - The GitHub profile for the repo's owner/author
    (https://github.com/NandhaKishorM) gives the name **Nandakishor Mukkunnoth**,
    bio: "Building explainable, privacy-preserving, and ultra-low-latency AI
    models for healthcare, edge systems, and calibrated decision-making," role
    Founder & CEO at Convai Innovations. Neither "mathematician" nor "Ananda
    Kishore" appears anywhere on the profile.
  - The repo README attributes the project to "Convai Innovations," maintained by
    NandhaKishorM. Source: https://github.com/NandhaKishorM/laya
  - Secondary press coverage (not primary, used only for corroboration): an
    AnalyticsIndiaMag feature
    (https://analyticsindiamag.com/ai-features/this-kerala-engineer-built-open-source-jev-alternative-a-year-before-the-hype)
    describes him as a Kerala-based engineer with an **electrical engineering**
    degree from Government Engineering College, Kannur, and a former Principal
    Investigator at IIT Palakkad Technology IHUB — an engineering/AI-research
    background, not a mathematics one.
  - **Conclusion: the correct attribution is Nandakishor Mukkunnoth / Convai
    Innovations. The "Ananda Kishore, mathematician" claim appears to be either a
    hallucination or confusion with an unrelated person and must not be repeated
    anywhere in BeatIT docs or code comments.**
- **Exact contents of `laya/integrations/langchain.py`** — confirmed to exist as a
  file, but its implementation was not readable via the tools available in this
  research pass (GitHub's tree view doesn't render file bodies through the fetch
  tool used). Before wiring BeatIT to it, read the raw file directly
  (`raw.githubusercontent.com/.../laya/integrations/langchain.py`) or via `gh`/git
  clone.
- **Exact schema/format of the "prediction hooks" API** and the exact JSON
  request/response wire format of `POST /v1/systemone` — described at a high
  level in the docs, but the literal request/response JSON body was not present in
  the fetched excerpts. Read `nandhakishorm.github.io/laya`'s HTTP-server page
  directly (with a working URL — the `langchain.html` path 404'd, other subpages
  may differ) before implementing a client.
- **Whether Laya's "Jev-compatible" wire protocol claim has ever been validated
  against a real Jev endpoint** (as opposed to just documented as intended) — no
  evidence either way was found; treat as an unverified compatibility claim, not a
  tested one.
- **`nandhakishorm.github.io/laya/langchain.html` is unreachable (404 at fetch
  time)** — noted here explicitly per instructions rather than guessed around.

## Comparison Notes

- **OpenJev** (`github.com/lookski/openjev`, MIT license) — a different design
  philosophy from Laya: instead of a purpose-trained encoder, it takes an
  off-the-shelf small open LLM (Qwen3-0.6B, Llama, Phi, etc.) and reads the raw
  first-token logits, applying a masked softmax to get calibrated-looking
  probabilities without any decoding or fine-tuning. Also exposes a Jev-wire-
  compatible HTTP server and the same `Choice`/`Score`/`Noul` vocabulary. Claims
  0.1–3s latency (an order of magnitude slower than Laya's claimed ~33ms, since
  it's running general-purpose LLM backbones rather than Laya's compact,
  purpose-trained heads) and 100% offline operation.
  Source: https://github.com/lookski/openjev (fetched directly, exists as
  described). Note: a broader web search surfaced *many* other "open Jev" clones
  under different names/orgs (e.g. `zhangcy122/OpenJev`, `openjevai/DecisionEngine`,
  `kyegomez/open-jev`, `Heman10x-NGU/Verdict-open-jev`) — these are separate,
  unrelated projects also inspired by Jev; do not conflate them with the
  `lookski/openjev` repo named in this task.
- **Kev** (`github.com/jaredpalmer/kev`, Apache-2.0) — LoRA (rank-16) adapters on
  top of Qwen base models at four sizes (0.8B–27B), with a "question isolation"
  design so multiple questions asked about the same input can't leak into each
  other's attention. Reports calibrated confidence by default and benchmarks
  itself directly against Jev: Kev-27B reaches 0.848 accuracy vs. Jev's 0.857
  (within ~1 point) on its eval, with smaller Kev sizes trailing by 3–4 points and
  underperforming specifically on knowledge-heavy questions; Jev is reported as
  better at ranking answers for automation-threshold use cases (0.70 vs. Kev's
  0.45–0.57). Source: https://github.com/jaredpalmer/kev (fetched directly, exists
  as described).
- **Bottom line for BeatIT:** all three (Laya, OpenJev, Kev) are independent,
  differently-architected reimplementations of the same "typed decision over
  text" idea popularized by Jev, none of them *are* Jev, and none should be
  presented as interchangeable — this report does not recommend integrating more
  than one, per the task's own framing; Laya remains the default candidate given
  it's the one BeatIT is scoping the System-1 layer against.

## Jev Terminology Correction

**Jev itself is a closed, commercial API — not open-source and not open-weight.**
TypeSafe AI serves Jev only from its own hosted API (launched 15 Sept 2026, priced
at $0.042 per million input tokens with output apparently unmetered) and publishes
docs, pricing, and rate limits — **not** model weights or a license to self-host
it. (Source: web search summary citing TypeSafe/Jev pricing pages and
`madewithjev.com/open-source-jev`, which is itself explicitly framed as "Is Jev
open source? No, but N open alternatives are" — corroborating, not primary,
evidence, but directly on-point and unambiguous.)

Therefore: **do not describe a Laya-based integration as "self-hosted Jev,"
"running Jev locally," or any phrasing implying BeatIT is running TypeSafe's
actual model.** That is factually wrong and could mislead judges/reviewers about
what's actually deployed. The correct terminology is one of:
- "a Jev-*compatible* decision engine" (accurate: Laya's HTTP server implements
  the same wire protocol/API shape as Jev's `/v1/systemone`, per its own docs)
- "an open-weight, independently-trained alternative to Jev" (accurate: Laya is
  its own model, trained by Convai Innovations, not a redistribution of Jev)
- "a Jev-*inspired* System-1 decision layer" (accurate, safest for prose/marketing)

Never state or imply Laya *is* Jev, contains Jev's weights, or is licensed by
TypeSafe — none of that is supported by any source found.

## Recommended Integration Boundaries

Per AGENTS.md §1 rule 3 and rule 4 (deterministic physics core is sacred; safety
disclaimers and diagnosis/treatment/emergency blocking must keep working), Laya
(or any System-1 decision layer) must be scoped strictly as **fast internal
routing/software glue**, never as a clinical decision-maker:

**Laya MAY decide (fast, low-stakes, reversible, software-only):**
- Which specialist agent/tool in the existing 8-agent pipeline should handle a
  given free-text input next (routing/dispatch, not the medical content of the
  decision).
- Whether an uploaded file/image looks well-formed enough to hand to the
  extraction step (a `noul`/format-sanity gate), not whether its *medical
  content* is valid.
- UI/UX intent classification (e.g., "is this chat message a question about the
  demo vs. a request to rerun a simulation") to route within the app.
- Cheap pre-filtering/triage of *non-clinical* support/ops text (e.g., internal
  logging, demo-mode branching) where a wrong answer costs nothing more than a
  retry.
- Caching/gating decisions about whether to re-run an expensive step (a software
  optimization, not a medical judgment).

**Laya MUST NEVER decide (per AGENTS.md's hard safety rule, non-negotiable):**
- Any cardiac diagnosis, differential, severity, or treatment recommendation.
- Any emergency/urgent-care triage determination (e.g., "is this an emergency,"
  "should the user call 911") — this is explicitly the intake agent's guarded
  responsibility today and must not be silently replaced or shadowed by a
  System-1 model with a documented ECE of 0.213 on its own best benchmark.
- Anything that would appear as authoritative medical output in an API response
  or on screen without going through the existing safety_disclaimer path.
- Any decision whose failure mode is a false negative on a safety-relevant
  question (Laya's calibration numbers, even post-fine-tune, are not proven
  strong enough on cardiac-domain data — see below — to bear that risk).

In short: Laya is a router/gate for *plumbing*, never a source of medical truth.

## Calibration Campaign Prerequisites

Before any BeatIT threshold is set against a Laya `score`/`noul`/`choice`
probability in production — even for the "MAY decide" routing use cases above —
the following should be measured, because Laya's own published numbers are on
its own general-purpose benchmark suite, not BeatIT's domain:

1. **Build a small labeled BeatIT-specific eval set** (analogous to Laya's own
   "400 cases / 2,000 decisions" methodology) covering the actual routing/gating
   decisions BeatIT wants Laya to make — not cardiac diagnosis content, but the
   software-routing decisions themselves (e.g., "is this upload a valid case
   file," "which specialist agent should this go to").
2. **Measure accuracy, Brier score, and ECE on that BeatIT-specific set**, not
   just trust Laya's self-reported 0.766/0.061/0.213 from its own typed-decisions
   benchmark — those numbers do not transfer to a new domain without
   re-measurement, and Laya's own docs show a large gap between base-checkpoint
   accuracy (~0.35) and fine-tuned accuracy (0.766), meaning out-of-the-box
   performance on an unseen domain like cardiac-software routing could land
   anywhere in that range.
3. **Run (or re-run) a temperature-refit / calibration pass on held-out
   BeatIT data**, mirroring the improvement Laya's own docs show
   (ECE 0.466→0.081 and 0.314→0.106 after refit) — an uncalibrated confidence
   score should never be used to set an automation threshold.
4. **Decide and document an explicit confidence threshold + fallback path**
   (e.g., "below 0.80 confidence, fall back to a human/LLM-reasoning step") for
   every Laya-backed decision, and log every Laya call (input, output,
   confidence) so mis-routes are auditable — this is a natural fit for the
   existing `trace_sink` instrumentation seam in
   `python/hearttwin/tools/weave_trace.py` (per AGENTS.md §2), giving free
   observability into whether the calibration campaign's assumptions hold in
   production.
5. **Re-verify the exact `POST /v1/systemone` request/response schema and the
   `laya/integrations/langchain.py` adapter's real implementation** directly from
   source (clone or `gh api`) before writing integration code — this report
   confirms these exist but could not read their full contents through the
   fetch tooling available in this research pass.
6. **Never let step 1–5 block or bypass the existing safety_disclaimer /
   diagnosis-blocking logic** — the calibration campaign only qualifies Laya for
   the non-clinical "MAY decide" list above; it can never qualify it to touch the
   "MUST NEVER decide" list, no matter how good the numbers look.
