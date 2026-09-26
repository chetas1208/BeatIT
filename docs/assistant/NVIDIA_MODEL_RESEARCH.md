# NVIDIA Build Model Research — Shortlist for BeatIT LLM Routing

**Status: research/shortlist only — no model is locked. Wave 6 must run empirical
benchmarks against real BeatIT tasks before any production decision.**

## Summary

NVIDIA Build (build.nvidia.com) currently hosts the **Nemotron 3 / 3.5 family**,
which maps cleanly onto BeatIT's three-tier routing plan: **Nemotron 3.5 Lightning
30B-A3B** as the fast/low-latency agentic candidate, **Nemotron 3 Super 120B-A12B**
(with **Nemotron 3 Ultra 550B-A55B** as a heavier alternative) as the deep-reasoning
candidate, and **Nemotron 3.5 Content Safety** (a Gemma-3-4B-based multimodal/
multilingual guard model) as the safety/moderation candidate. All three are hybrid
Mamba-Transformer MoE designs positioned explicitly for "agentic" workloads with
very large (up to 1M token) context windows, and all are exposed through NVIDIA's
OpenAI-compatible REST API at `https://integrate.api.nvidia.com/v1` using a bearer
`nvapi-` key. Free-tier access exists for prototyping but is rate-limited (~40
RPM, forum-reported, not an official SLA) and explicitly not intended for
production traffic — relevant to the key-pool/failover design planned for later
waves. NVIDIA's own **Ambient Healthcare Agents** blueprint is a useful reference
architecture: it cleanly separates provider-facing vs. patient-facing agents,
reasoning LLMs, speech (ASR/TTS) NIMs, and guardrail NIMs as independently
swappable microservices — a pattern worth mirroring (not copying) in BeatIT's own
agent split. Nothing here has been benchmarked against BeatIT's actual tasks
(cardiac-state explanation, longitudinal summaries, PV-loop narration, physician
briefs, tool-planning); that is explicitly deferred to Wave 6.

## Current Model Catalog Snapshot

*As observed on 2026-09-26. NVIDIA's catalog changes frequently — re-verify
before Wave 6 locks anything.* Fetched from `https://build.nvidia.com/models`.
The catalog lists 100+ models across categories (agentic/coding/tool-calling,
safety/guardrails, multimodal vision-language, OCR, embedding, speech). Nemotron-
family entries observed:

| Model | Positioning | Specs |
|---|---|---|
| `nemotron-3-embed-1b` | Embeddings for RAG/retrieval | 1B params |
| `nemotron-3-nano-omni-30b-a3b-reasoning` | Omni-modal reasoning (image/video/speech/text) | 30B total / 3B active MoE |
| `nemotron-3-super-120b-a12b` | Hybrid Mamba-Transformer MoE, agentic reasoning + coding | 120B total / 12B active; 1M context |
| `nemotron-3-ultra-550b-a55b` | Same architecture family, larger scale | 550B total / 55B active; 1M context |
| `nemotron-3.5-content-safety` | Multilingual, multimodal unsafe/toxic content detector | Gemma-3-4B base; guardrail |
| `nemotron-3.5-lightning-30b-a3b` | "Fastest 30B A3B MoE... specialized agentic tasks" | 30B total / 3B active |
| `nemotron-asr-streaming`, `nemotron-ocr-v1/v2`, `nemotron-parse(-2.0)`, `nemotron-voicechat` | Speech/OCR/vision-language utilities | n/a to routing decision |

Source: [build.nvidia.com/models](https://build.nvidia.com/models). Note: the
live build.nvidia.com pages are a JS-rendered SPA; direct fetches of model-card
subpages (e.g. `/nvidia/nemotron-3-super-120b-a12b/modelcard`) returned only
navigation chrome, not model content, when fetched programmatically in this
session — specs below were cross-verified via NVIDIA's own developer blog,
`docs.api.nvidia.com` reference pages, and Hugging Face model cards instead.

## Fast-Model Candidates

| Model / ID | Params | Context | Positioning | Source |
|---|---|---|---|---|
| **Nemotron 3.5 Lightning** — `nvidia/nemotron-3.5-lightning-30b-a3b` | 30B total / 3B active (hybrid Mamba-2 + MoE + select Attention layers, multi-token prediction) | Up to 1M tokens (pretrained on 20T+ tokens) | Explicitly branded "delivers fast, accurate specialized task execution for **long-running agents**"; general-purpose reasoning/chat + coding; English + coding languages primary, ES/FR/DE/IT/JA supported | [NVIDIA dev blog](https://developer.nvidia.com/blog/nvidia-nemotron-3-5-lightning-delivers-fast-accurate-specialized-task-execution-for-long-running-agents/), [build.nvidia.com modelcard](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard), [HF model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4) |
| Nemotron 3 Nano (family: Nano/Super/Ultra) — `nvidia/nemotron-3-nano-...` | 30B total / 3B active MoE variants | Up to 1M tokens | Prior-gen fast tier; "4x higher throughput than Nemotron 2 Nano," built for agentic/reasoning/tool-use/chat; useful as a fallback if Lightning proves unstable | [NVIDIA blog](https://blogs.nvidia.com/blog/nemotron-3-nano-omni-multimodal-ai-agents/), [HF blog](https://huggingface.co/blog/nvidia/nemotron-3-nano-efficient-open-intelligent-models) |

Confirms original hypothesis: the exact current name is **"Nemotron 3.5
Lightning"** (30B-A3B), not "3.5 Lightning" as a standalone brand disconnected
from the Nemotron 3 line — it is the fast tier of the Nemotron 3.x generation.

## Deep-Model Candidates

| Model / ID | Params | Context | Positioning | Source |
|---|---|---|---|---|
| **Nemotron 3 Super** — `nvidia/nemotron-3-super-120b-a12b` | 120B total / 12B active (hybrid Mamba-Transformer + latent MoE + multi-token prediction, native NVFP4 pretraining) | 1M tokens native; NVIDIA notes 262,144 is the practical/default ceiling on modest hardware (1M can OOM) | "Open, efficient hybrid Mamba-Transformer MoE... excelling in agentic reasoning, coding"; configurable "thinking budget" to bound chain-of-thought latency/cost; 5x throughput vs. previous Super gen | [NVIDIA dev blog](https://developer.nvidia.com/blog/introducing-nemotron-3-super-an-open-hybrid-mamba-transformer-moe-for-agentic-reasoning/), [NVIDIA blog](https://blogs.nvidia.com/blog/nemotron-3-super-agentic-ai/), [docs.api.nvidia.com](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-super-120b-a12b), [HF](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16) |
| Nemotron 3 Ultra — `nvidia/nemotron-3-ultra-550b-a55b` | 550B total / 55B active | 1M tokens | Same architecture family scaled up; heavier/higher-quality alternative to Super if Wave 6 benchmarks show Super insufficient for the hardest reasoning tasks (e.g. full physician briefs) | [build.nvidia.com/models catalog](https://build.nvidia.com/models) |
| (Reference only, older gen) Llama-3.3-Nemotron-Super-49B-Instruct | 49B | Standard Llama context | Used in NVIDIA's own Ambient Healthcare Agents blueprint for clinical note generation ("highest accuracy and lowest latency" per NVIDIA) — evidence that a Nemotron-Super-class model is already validated by NVIDIA for a clinical documentation use case adjacent to BeatIT's physician-brief task | [build.nvidia.com/nvidia/ambient-healthcare-agents](https://build.nvidia.com/nvidia/ambient-healthcare-agents) |

Confirms original hypothesis: **"Nemotron 3 Super"** is current and real, at
120B/12B-active with a genuine 1M-token context ceiling (practical default much
lower). Ultra is the untested larger sibling worth keeping on the shortlist.

## Safety-Model Candidates

| Model / ID | Params | Context | Positioning | Source |
|---|---|---|---|---|
| **Nemotron 3.5 Content Safety** — `nvidia/nemotron-3.5-content-safety` | ~4B (fine-tuned on Google Gemma-3-4B-it base) | 128K tokens | Multimodal (text + optional image) + multilingual (12 languages explicitly trained: EN, AR, DE, ES, FR, HI, JA, TH, NL, IT, KO, Mandarin; ~140-language zero-shot claimed) moderator; classifies across **23 safety categories** (violence, hate, sexual content, criminal planning, self-harm, fraud, malware, PII, etc.); evaluates prompt + optional response together in one call; optional "THINK mode" emits an auditable reasoning trace and a list of violated categories | [HF blog](https://huggingface.co/blog/nvidia/nemotron-3-5-content-safety), [build.nvidia.com modelcard](https://build.nvidia.com/nvidia/nemotron-3.5-content-safety/modelcard), [NGC catalog](https://catalog.ngc.nvidia.com/orgs/nim/teams/nvidia/models/nemotron-3.5-content-safety) |
| (Reference/older gen) Llama-3.1-NemoGuard-8B-ContentSafety + Llama-3.1-NemoGuard-8B-TopicControl | 8B each | Standard | Two-model guardrail pair used together in NVIDIA's Ambient Healthcare Agents blueprint — one for content safety, one for keeping the agent on-topic. Evidence for a **pattern** (safety + topic-control as separate concerns) even if BeatIT ends up using the newer unified 3.5 model | [build.nvidia.com/nvidia/ambient-healthcare-agents](https://build.nvidia.com/nvidia/ambient-healthcare-agents) |

Confirms/refines original hypothesis: the current name is **"Nemotron 3.5
Content Safety"**, not "Nemotron Safety Guard 8B" — the 8B NemoGuard naming is
the *previous* generation (Llama-3.1-based, still live and used in NVIDIA's own
healthcare blueprint). The invocation pattern in both generations is the same:
call it as a **wrapping guard** — pass the user prompt (and, for 3.5, optionally
the assistant's response and/or an image) and get back a safe/unsafe label plus
violated-category list, before or after the primary model runs. Exact
request/response JSON schema and system-prompt template were not independently
retrievable in this session (build.nvidia.com's modelcard SPA didn't render via
programmatic fetch); pull the exact schema from the HF/NGC model card or a live
`docs.api.nvidia.com` call before wiring it up in a later wave.

## API Access Pattern

- **Base URL:** `https://integrate.api.nvidia.com/v1` — OpenAI-compatible.
  Source: [ai-sdk.dev NIM provider docs](https://ai-sdk.dev/providers/openai-compatible-providers/nim), [Promptfoo NVIDIA NIM docs](https://www.promptfoo.dev/docs/providers/nvidia/), corroborated by multiple third-party integration guides.
- **Auth header:** `Authorization: Bearer $NVIDIA_API_KEY`, where the key is
  obtained from build.nvidia.com (sign in → open a model → "Get API Key") and is
  shown once, prefixed `nvapi-`.
- **OpenAI compatibility:** Because it mirrors the OpenAI Chat Completions
  contract, existing OpenAI-SDK client code needs only `base_url` and `api_key`
  changed — same `model`, `messages`, `temperature`, `max_tokens` fields. Verified
  example (community/local-NIM curl, structurally identical to the hosted
  endpoint):
  ```bash
  curl https://integrate.api.nvidia.com/v1/chat/completions \
    -H "Authorization: Bearer $NVIDIA_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model": "nvidia/nemotron-3-super-120b-a12b",
         "messages": [{"role": "user", "content": "..."}]}'
  ```
- **Model ID string format:** Third-party providers that mirror NVIDIA's own
  catalog naming (OpenRouter, AI/ML API, docs.api.nvidia.com reference pages)
  consistently use `nvidia/<catalog-slug>`, e.g. `nvidia/nemotron-3-super-120b-a12b`,
  `nvidia/nemotron-3.5-lightning-30b-a3b`, `nvidia/nemotron-3.5-content-safety` —
  matching the URL slugs on build.nvidia.com model-card pages
  (`build.nvidia.com/nvidia/<slug>/modelcard`). **This has not been independently
  confirmed by fetching NVIDIA's own first-party curl snippet** (the build.nvidia.com
  modelcard SPA did not render via programmatic fetch in this session) — verify the
  exact string against the live "Get API Key" / "View Code" panel on
  build.nvidia.com before wiring real calls.
- **Local/self-hosted NIM parity:** the same `model` string and request schema
  apply to a self-hosted NIM container on `localhost:8000/v1/chat/completions`,
  per [NVIDIA NIM docs](https://docs.nvidia.com/nim/large-language-models/2.0.4/turbo/get-started-nemotron-3-super-120b-a12b.html) — useful if BeatIT ever needs an offline fallback.

## Ambient Healthcare Agents Architecture Notes

Reference: [build.nvidia.com/nvidia/ambient-healthcare-agents](https://build.nvidia.com/nvidia/ambient-healthcare-agents).
This is NVIDIA's own healthcare multi-agent blueprint — reference architecture
only, not something to copy wholesale into BeatIT. The modularity pattern worth
extracting:

- **Two agents split by audience, not by function:** an *Ambient Provider Agent*
  (clinician-facing, transcribes conversations → generates SOAP-format clinical
  notes) and an *Ambient Patient Agent* (patient-facing, handles intake/surveys/
  scheduling) — each independently deployable and independently model-tuned.
- **Reasoning tier is itself split by workload weight**, echoing BeatIT's
  fast/deep split: the provider agent (higher-stakes clinical documentation) uses
  **Llama-3.3-Nemotron-Super-49B-Instruct** for "highest accuracy and lowest
  latency," while the patient agent (higher-volume, lower-stakes) uses the
  smaller/cheaper **Llama-3.3-70B-Instruct** for tool-calling and general
  reasoning.
- **Speech is a fully separate NIM tier**, not folded into the LLM: ASR via
  **Parakeet-CTC 1.1B** (Riva NIM, low-latency, speaker diarization, medical-
  term lexicon boosting) and TTS via **Magpie** (multilingual). This is a strict
  separation of concerns — LLMs never touch raw audio directly.
- **Safety is its own independent NIM tier, composed of two single-purpose
  guardrail models** rather than one do-everything filter: **Llama-3.1-
  NemoGuard-8B-Content-Safety** (blocks unsafe content) and **Llama-3.1-
  NemoGuard-8B-Topic-Control** (keeps responses on-topic) — both configurable/
  customizable independently of the reasoning models they wrap.
- **Orchestration is microservice-style**: each function (ASR, TTS, reasoning,
  guardrails) is its own NIM, wired together by an orchestration layer (NVIDIA
  names "ACE Controller" for the patient agent), and every component supports
  both self-hosted GPU deployment and cloud API-endpoint access — i.e., the same
  logical agent can run against build.nvidia.com hosted endpoints during
  prototyping and against self-hosted NIMs in production without changing the
  orchestration code, only the endpoint config.
- **Takeaway for BeatIT:** the pattern of (a) separating reasoning weight by
  stakes/latency, (b) treating safety as an independent wrapping tier rather
  than a prompt-engineered afterthought, and (c) keeping every tier swappable
  via endpoint config rather than hardcoded model calls — maps directly onto
  BeatIT's planned fast/deep/safety three-key routing design. It does **not**
  suggest BeatIT needs speech NIMs or a two-agent audience split; that part is
  specific to NVIDIA's ambient-scribe use case and is out of scope here.

## Open Questions For Benchmarking (Wave 6 input)

None of the following has been empirically tested against BeatIT's actual
tasks in this research pass — all require real benchmarking before any model is
locked for production:

1. **Cardiac-state explanation quality**: does Lightning (fast, 3B active) give
   physiologically coherent, safety-compliant explanations of deterministic
   cardiac-state outputs at acceptable latency, or does it need Super/Ultra?
2. **Longitudinal summaries**: how well does each candidate track/compare state
   across multiple recovery-sim time points without hallucinating trend claims
   the physics core didn't produce?
3. **PV-loop explanations**: this requires grounded numeric/graphical reasoning
   over hemodynamics output — untested whether Lightning's smaller active
   parameter count is sufficient, or whether this specifically needs Super.
4. **Physician-brief generation**: NVIDIA's own use of a Nemotron-Super-class
   model for clinical note generation is suggestive but not a substitute for
   testing BeatIT's own physician-brief format/tone/safety requirements.
5. **Tool-planning / orchestration**: BeatIT's orchestrator needs reliable
   function/tool-call selection across 8 specialist agents — needs a head-to-
   head of Lightning vs. Super on tool-call accuracy and latency, since
   "agentic" positioning is marketing language until tested on BeatIT's actual
   tool schema.
6. **Safety-model integration point**: should Nemotron 3.5 Content Safety wrap
   every request/response pair (cost/latency overhead per turn), or run
   sampled/async, and does its 23-category taxonomy overlap or conflict with
   BeatIT's existing `safety_disclaimer` / diagnosis-blocking logic in the
   intake agent (must not regress golden rule #4)?
7. **Rate-limit reality under 3-key routing**: the ~40 RPM figure is forum-
   reported, not an official documented SLA — needs live verification per-key
   and per-model once real BeatIT keys exist, especially if fast+deep+safety
   calls fan out per user turn (3x the naive request count).
8. **Context-window practicality**: Super's 1M-token ceiling reportedly needs
   >256K-capable hardware or it can OOM in self-hosted NIM deployments; confirm
   whether the hosted build.nvidia.com endpoint enforces a lower practical
   ceiling and what BeatIT actually needs (likely far under 1M for single-case
   digital-twin sessions).
9. **Exact `model=` string and safety-model request schema**: confirm directly
   from the "View Code" panel on each build.nvidia.com model page (not
   reconstructed from third-party mirrors as done here) before writing any
   integration code.
10. **Pricing at BeatIT's actual volume**: figures gathered here ($0.05–$0.88/1M
    input tokens across variants) come from third-party aggregators
    (DeepInfra, PricePerToken), not NVIDIA's own published rate card — get
    NVIDIA's authoritative pricing once paid keys are provisioned.

## Source Links

- [build.nvidia.com/models](https://build.nvidia.com/models)
- [build.nvidia.com/nvidia/ambient-healthcare-agents](https://build.nvidia.com/nvidia/ambient-healthcare-agents)
- [build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard)
- [build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/modelcard](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/modelcard)
- [build.nvidia.com/nvidia/nemotron-3.5-content-safety/modelcard](https://build.nvidia.com/nvidia/nemotron-3.5-content-safety/modelcard)
- [NVIDIA Debuts Nemotron 3 Family of Open Models (Newsroom)](https://nvidianews.nvidia.com/news/nvidia-debuts-nemotron-3-family-of-open-models)
- [Inside NVIDIA Nemotron 3 (dev blog)](https://developer.nvidia.com/blog/inside-nvidia-nemotron-3-techniques-tools-and-data-that-make-it-efficient-and-accurate/)
- [Introducing Nemotron 3 Super (dev blog)](https://developer.nvidia.com/blog/introducing-nemotron-3-super-an-open-hybrid-mamba-transformer-moe-for-agentic-reasoning/)
- [New Nemotron 3 Super Delivers 5x Higher Throughput (NVIDIA blog)](https://blogs.nvidia.com/blog/nemotron-3-super-agentic-ai/)
- [NVIDIA Nemotron 3.5 Lightning dev blog](https://developer.nvidia.com/blog/nvidia-nemotron-3-5-lightning-delivers-fast-accurate-specialized-task-execution-for-long-running-agents/)
- [NVIDIA Nemotron 3 Nano Omni Blog](https://blogs.nvidia.com/blog/nemotron-3-nano-omni-multimodal-ai-agents/)
- [Nemotron 3 Nano HF blog](https://huggingface.co/blog/nvidia/nemotron-3-nano-efficient-open-intelligent-models)
- [Nemotron 3.5 Content Safety HF blog](https://huggingface.co/blog/nvidia/nemotron-3-5-content-safety)
- [Nemotron-3.5-Content-Safety NGC catalog](https://catalog.ngc.nvidia.com/orgs/nim/teams/nvidia/models/nemotron-3.5-content-safety)
- [docs.api.nvidia.com — nemotron-3.5-lightning-30b-a3b](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-5-lightning-30b-a3b)
- [docs.api.nvidia.com — nemotron-3-super-120b-a12b](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-super-120b-a12b)
- [docs.api.nvidia.com — nemotron-3.5-content-safety](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-5-content-safety)
- [NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4 HF card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4)
- [NVIDIA-Nemotron-3-Super-120B-A12B-BF16 HF card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16)
- [NVIDIA NIM Get Started — Nemotron 3 Super 120B](https://docs.nvidia.com/nim/large-language-models/2.0.4/turbo/get-started-nemotron-3-super-120b-a12b.html)
- [ai-sdk.dev — NIM OpenAI-compatible provider docs](https://ai-sdk.dev/providers/openai-compatible-providers/nim)
- [Promptfoo — NVIDIA NIM provider docs](https://www.promptfoo.dev/docs/providers/nvidia/)
- [NVIDIA Developer Forums — free-tier rate-limit clarity thread](https://forums.developer.nvidia.com/t/clarity-on-nim-api-free-tier-rate-limit-increases/369624)
- [NVIDIA Developer Forums — API rate-limit increase thread](https://forums.developer.nvidia.com/t/api-rate-limit-increase-for-nvidia-nim/366043)
- [DeepInfra — NVIDIA Nemotron API pricing guide 2026](https://deepinfra.com/blog/nvidia-nemotron-api-pricing-guide-2026)
- [PricePerToken — Nemotron 3 Super 120B A12B pricing](https://pricepertoken.com/pricing-page/model/nvidia-nvidia-nemotron-3-super-120b-a12b)
- [OpenRouter — nemotron-3-super-120b-a12b:free](https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b:free)
- [OpenRouter — nemotron-3.5-content-safety:free](https://openrouter.ai/nvidia/nemotron-3.5-content-safety:free)
