# Campaign Agent 01 — Capability and Model-Requirement Audit

**Audit date:** 2026-09-26 UTC  
**Scope:** actual BeatIT source and documentation; model-dependent versus
deterministic capability boundaries; required/optional/not-required status;
executable local checks.  
**Change boundary:** documentation only. No production code, fixtures, model
weights, credentials, or external data were changed or downloaded.

## Plan

1. Inspect the repository instructions, capability/model manifests, runtime
   configuration, pipeline stages, and model call sites.
2. Trace each user-facing capability to its implementation authority and
   separate model input/prose from deterministic numeric or safety logic.
3. Run isolated local checks with provider credentials and external endpoints
   removed from the process environment.
4. Record exact source references, executable checks, limitations, and a final
   disposition without treating configuration or checkpoint presence as live
   inference proof.

## Status vocabulary

The status below is about the dependency being audited, not whether the
feature exists:

- **Required:** required for the named capability in its stated mode.
- **Optional:** enhances the product, but the deterministic/local core has a
  supported path without it.
- **Not required:** no model, model weight, or remote model service is needed
  for the capability.

## Executive result

BeatIT's canonical physiology and safety spine is deterministic. Model-backed
components supply candidate extraction, intent/routing, scenario proposal, or
plain-language explanation; they do not own cardiac arithmetic. The local
deterministic path is executable without an OpenAI-compatible provider, Weave,
Redis, or VISTA service.

The model manifest marks `medical-segmentation`, `language`, and `embedding` as
`required: false` ([`models/manifest.json`](../../../models/manifest.json)). The
audited environment reported the local VISTA checkpoint as metadata-available
but unloaded; language and embedding were unavailable. This is not evidence of
live model serving or clinical validation.

**Final disposition: PASS for the documented local deterministic capability
boundary; OPEN for live provider/model capability claims.**

## Capability map

| Capability | Actual authority and model boundary | Status | Result |
|---|---|---:|---|
| Canonical cardiac state metrics: SV, EF, CO, MAP, BSA, RR, QTc and bounded indices | Pure functions in [`cardiac_state.py:1-5`](../../../python/hearttwin/tools/cardiac_state.py#L1-L5) and [`cardiac_state.py:13-130`](../../../python/hearttwin/tools/cardiac_state.py#L13-L130). No provider call. | Not required | **Deterministic and required for the core twin.** Input evidence may be model-extracted, but the formulas are not. |
| Hemodynamics, cardiac cycle, and PV loop | [`hemodynamics.py:1-6`](../../../python/hearttwin/tools/hemodynamics.py#L1-L6) and [`hemodynamics.py:64-78`](../../../python/hearttwin/tools/hemodynamics.py#L64-L78) define deterministic time-varying-elastance calculations; the agent calls formula tools at [`hemodynamics_agent.py:467-527`](../../../python/hearttwin/agents/hemodynamics_agent.py#L467-L527). | Not required | **Deterministic and required for operation.** The optional model only narrates already-computed metrics ([`hemodynamics_agent.py:250-298`](../../../python/hearttwin/agents/hemodynamics_agent.py#L250-L298)). |
| ECG waveform features | The Pan-Tompkins-style detector and derived RR/HR/QTc/rhythm descriptors are local code in [`ecg_features.py:76-175`](../../../python/hearttwin/tools/ecg_features.py#L76-L175) and [`ecg_features.py:178-242`](../../../python/hearttwin/tools/ecg_features.py#L178-L242). | Not required | **Deterministic for waveform/CSV input.** A model may only normalize an already-reported rhythm label; it never estimates numeric ECG features ([`electrophysiology_agent.py:256-276`](../../../python/hearttwin/agents/electrophysiology_agent.py#L256-L276), [`electrophysiology_agent.py:599-637`](../../../python/hearttwin/agents/electrophysiology_agent.py#L599-L637)). |
| PDF, CSV, and manual-vital ingestion | PDF values come from local `pypdf` plus regexes ([`pdf_extract.py:94-168`](../../../python/hearttwin/tools/pdf_extract.py#L94-L168)); CSV/manual extraction is local in [`extraction_agent.py:62-115`](../../../python/hearttwin/agents/extraction_agent.py#L62-L115) and [`extraction_agent.py:216-293`](../../../python/hearttwin/agents/extraction_agent.py#L216-L293). | Not required | **Deterministic; no language/vision model needed.** |
| Image/ECG-still extraction | [`image_extract.py:61-79`](../../../python/hearttwin/tools/image_extract.py#L61-L79) requires an available provider and returns empty extraction with a warning when unavailable; accepted fields are confidence-filtered at [`image_extract.py:81-145`](../../../python/hearttwin/tools/image_extract.py#L81-L145). | Optional | **Model-dependent for image values.** It is not required for structured vitals, PDF, CSV, or the deterministic core. |
| Echo-video frame extraction | The extraction agent uses optional `imageio`/Pillow decoding and then the image model path ([`extraction_agent.py:180-213`](../../../python/hearttwin/agents/extraction_agent.py#L180-L213)). | Optional | **Optional codec + model path.** Missing codecs or provider produce a labelled warning and no invented values. |
| CT segmentation | The VISTA client is explicitly gated by `VISTA3D_ENABLED` and an API base, health-checks before submission, returns an asynchronous job, and never computes chamber values ([`vista3d_client.py:1-20`](../../../python/hearttwin/tools/vista3d_client.py#L1-L20), [`vista3d_client.py:147-253`](../../../python/hearttwin/tools/vista3d_client.py#L147-L253)). | Optional | **Model/service-dependent enhancement.** The single heart label cannot yield chamber EF or a separate myocardium mask. |
| CT mask volumetry and educational CT observations | NIfTI parsing, voxel-count volumetry, label mapping, and global proxy observations are local deterministic code ([`ct_volumetry.py:1-15`](../../../python/hearttwin/tools/ct_volumetry.py#L1-L15), [`ct_volumetry.py:73-151`](../../../python/hearttwin/tools/ct_volumetry.py#L73-L151), [`ct_volumetry.py:169-243`](../../../python/hearttwin/tools/ct_volumetry.py#L169-L243)). | Not required | **Deterministic once a mask exists.** A VISTA model is required only to create a new segmentation mask, not to calculate volumes from it. |
| Intake safety and intent gate | Rule-based PII redaction and intent classification run before the optional provider ([`intake_agent.py:119-153`](../../../python/hearttwin/agents/intake_agent.py#L119-L153)); blocked diagnosis/treatment/emergency classes are defined in [`intake_agent.py:416-424`](../../../python/hearttwin/agents/intake_agent.py#L416-L424). | Not required | **Deterministic safety path.** A model may enrich non-blocked intent classification; it is not required to enforce the block. |
| Evidence validation | Units, physiological bounds, source ranking, candidate selection, conflicts, missing fields, and quality scoring are local rules ([`validator_agent.py:78-180`](../../../python/hearttwin/agents/validator_agent.py#L78-L180), [`validator_agent.py:472-523`](../../../python/hearttwin/agents/validator_agent.py#L472-L523)). | Not required | **Deterministic authority.** An optional model only turns detected conflicts into prose ([`validator_agent.py:233-248`](../../../python/hearttwin/agents/validator_agent.py#L233-L248)). |
| Canonical state building and provenance | State mapping, derived metrics, priors, source map, and data-quality score are built locally at [`state_builder_agent.py:900-942`](../../../python/hearttwin/agents/state_builder_agent.py#L900-L942). | Not required | **Deterministic authority.** The optional model explains missing/prior mappings only ([`state_builder_agent.py:779-818`](../../../python/hearttwin/agents/state_builder_agent.py#L779-L818), [`state_builder_agent.py:945-1017`](../../../python/hearttwin/agents/state_builder_agent.py#L945-L1017)). |
| Bounded recovery trajectories | [`recovery_sim.py:1-6`](../../../python/hearttwin/tools/recovery_sim.py#L1-L6) and seeded `random.Random` use at [`recovery_sim.py:67-103`](../../../python/hearttwin/tools/recovery_sim.py#L67-L103) produce the numeric trajectory. | Not required | **Deterministic for a fixed input/seed.** The optional model proposes bounded parameter sets; fallback templates are explicit ([`recovery_agent.py:217-230`](../../../python/hearttwin/agents/recovery_agent.py#L217-L230), [`recovery_agent.py:814-860`](../../../python/hearttwin/agents/recovery_agent.py#L814-L860)). |
| Evaluator scores and safety/hallucination checks | Score functions are local in [`scoring.py:82-158`](../../../python/hearttwin/tools/scoring.py#L82-L158) and [`scoring.py:253-411`](../../../python/hearttwin/tools/scoring.py#L253-L411); critic findings and the overall score are generated before any model summary ([`evaluator_agent.py:401-470`](../../../python/hearttwin/agents/evaluator_agent.py#L401-L470)). | Not required | **Deterministic evaluation gate.** The model is optional critic-summary prose with a deterministic summary fallback ([`evaluator_agent.py:477-487`](../../../python/hearttwin/agents/evaluator_agent.py#L477-L487), [`evaluator_agent.py:1092-1170`](../../../python/hearttwin/agents/evaluator_agent.py#L1092-L1170)). |
| Seeded plausible-twin ensemble | [`ensemble.py:1-5`](../../../python/hearttwin/ensemble.py#L1-L5), [`ensemble.py:349-375`](../../../python/hearttwin/ensemble.py#L349-L375), and [`ensemble.py:416-468`](../../../python/hearttwin/ensemble.py#L416-L468) sample validated input proxies with a recorded seed and re-run deterministic formulas. | Not required | **Deterministic for the same request/seed;** no embedding or generative model is used. Percentiles are descriptive, not probabilities or confidence intervals. |
| Shadow Trial paired scenarios | [`shadow_trial_engine.py:169-224`](../../../python/hearttwin/shadow_trial_engine.py#L169-L224) applies one scenario to each persisted baseline sample without resampling. | Not required | **Deterministic and model-free.** Effects are hypothetical descriptive simulation outputs. |
| Missing Piece sensitivity/evidence priority | [`missing_piece/engine.py:192-276`](../../../python/hearttwin/missing_piece/engine.py#L192-L276) and [`missing_piece/engine.py:286-363`](../../../python/hearttwin/missing_piece/engine.py#L286-L363) use bounded finite differences and explicit heuristics. | Not required | **Deterministic;** no semantic model or learned uncertainty model is active. |
| AHA/coronary localized findings and procedural 3D twin | Findings are versioned deterministic logic ([`cardiac_findings.py:28-31`](../../../python/hearttwin/tools/cardiac_findings.py#L28-L31), [`cardiac_findings.py:129-269`](../../../python/hearttwin/tools/cardiac_findings.py#L129-L269)); the frontend renders a procedural scene ([`HeartScene.tsx:1-5`](../../../web/components/heart/HeartScene.tsx#L1-L5), [`HeartScene.tsx:113-180`](../../../web/components/heart/HeartScene.tsx#L113-L180)). | Not required | **Deterministic visualization projection.** VISTA segmentation is optional and does not provide the rendered mesh; README states this boundary at [`README.md:128-130`](../../../README.md#L128-L130). |
| Conversational assistant routing and prose | The assistant can call an optional Laya/model path, but every decision has a deterministic keyword fallback ([`laya_adapter.py:152-202`](../../../python/hearttwin/assistant/laya_adapter.py#L152-L202), [`laya_adapter.py:267-406`](../../../python/hearttwin/assistant/laya_adapter.py#L267-L406)). Generated responses are subject to safety and numeric-claim rails ([`assistant/orchestrator.py:190-275`](../../../python/hearttwin/assistant/orchestrator.py#L190-L275), [`assistant/orchestrator.py:428-499`](../../../python/hearttwin/assistant/orchestrator.py#L428-L499)). | Optional | **Model-dependent for richer routing/narrative;** canonical tool answers and safe fallback remain available without it. |
| Weave traces, Redis persistence, and external artifact storage | These are integration services, not model capabilities. Weave has a local JSON fallback ([`weave_trace.py:1-18`](../../../python/hearttwin/tools/weave_trace.py#L1-L18), [`weave_trace.py:282-299`](../../../python/hearttwin/tools/weave_trace.py#L282-L299)); Redis is optional with in-process fallback when `REDIS_URL` is unset ([`redis_client.py:1-12`](../../../python/hearttwin/tools/redis_client.py#L1-L12), [`redis_client.py:31-68`](../../../python/hearttwin/tools/redis_client.py#L31-L68)). | Optional | **Not model-dependent and not required for local deterministic computation.** Remote trace/persistence claims require separate live verification. |

## Provider and local-model contract

The provider factory selects a configured generic/OpenAI provider only when its
required settings are complete; otherwise it returns a disabled provider without
failing startup ([`factory.py:44-74`](../../../python/hearttwin/intelligence/factory.py#L44-L74), [`factory.py:90-129`](../../../python/hearttwin/intelligence/factory.py#L90-L129)). The
provider-neutral contract explicitly says the cardiac engine owns numerical
physiology and providers produce language or untrusted extraction candidates
only ([`base.py:1-5`](../../../python/hearttwin/intelligence/base.py#L1-L5)).

Per-agent model names are environment-resolved labels ([`model_config.py:1-5`](../../../python/hearttwin/tools/model_config.py#L1-L5), [`model_config.py:58-101`](../../../python/hearttwin/tools/model_config.py#L58-L101)); a configured/default model name is not reachability evidence. The lazy registry inspects metadata and filesystem presence without loading model memory ([`registry.py:1-6`](../../../python/hearttwin/models/registry.py#L1-L6), [`registry.py:63-103`](../../../python/hearttwin/models/registry.py#L63-L103)).

The checked-in manifest's actual requirement state is:

| Manifest capability | `required` | Audited process state | Interpretation |
|---|---:|---|---|
| `medical-segmentation` | `false` | configured/available metadata, `loaded=false` | A checkpoint path exists, but no request-serving segmentation inference was established. |
| `language` | `false` | not configured/unavailable | Optional provider-neutral local language path; deterministic operation remains available. |
| `embedding` | `false` | not configured/unavailable | Optional and not used by the current provenance lookup contract. |

Source: [`models/manifest.json`](../../../models/manifest.json). The local
inventory also records that the VISTA checkpoint was not loaded by this audit
and that larger language artifacts are outside the active runtime contract
([`LOCAL_MODEL_INVENTORY.md`](../../models/LOCAL_MODEL_INVENTORY.md)).

## Optional CareGuard boundary

CareGuard is an additive, feature-flagged module and is not required for the
BeatIT deterministic twin. Its Anthropic client returns unavailable when no key
or SDK exists ([`careguard/anthropic/client.py:1-7`](../../../python/hearttwin/careguard/anthropic/client.py#L1-L7), [`careguard/anthropic/client.py:35-42`](../../../python/hearttwin/careguard/anthropic/client.py#L35-L42)); its copilot falls back to deterministic analysis ([`careguard/copilot_agent.py:1-6`](../../../python/hearttwin/careguard/copilot_agent.py#L1-L6), [`careguard/copilot_agent.py:69-93`](../../../python/hearttwin/careguard/copilot_agent.py#L69-L93)). The backend feature flag defaults off ([`feature_flags.py:25-27`](../../../python/hearttwin/careguard/feature_flags.py#L25-L27)).

CareGuard's local evidence retrieval uses deterministic keyword/topic scoring
and abstains without approved evidence ([`evidence/retriever.py:1-5`](../../../python/hearttwin/careguard/evidence/retriever.py#L1-L5), [`evidence/retriever.py:17-46`](../../../python/hearttwin/careguard/evidence/retriever.py#L17-L46)); this is separate from the optional Anthropic prose path. External medication/guideline services are data/network dependencies, not local model requirements, and are not treated as available by this audit.

## Executable evidence

All checks below were run from `/home/923873155/BeatIT` on 2026-09-26 UTC.
Provider credentials, provider endpoints, Weave variables, Redis URL, VISTA
service variables, and Laya variables were removed from the probe process.
No secret values were printed.

### Focused deterministic/model-boundary tests

Command shape:

```bash
env -u OPENAI_API_KEY -u MODEL_API_KEY -u MODEL_BASE_URL -u MODEL_NAME \
  -u WANDB_API_KEY -u WANDB_ENTITY -u WANDB_PROJECT -u REDIS_URL \
  -u VISTA3D_ENABLED -u VISTA3D_API_BASE -u VISTA3D_API_KEY \
  -u LAYA_ENABLED -u LAYA_BASE_URL -u LAYA_API_KEY \
  PYTHONPATH=. .venv/bin/python -m pytest -q \
  python/hearttwin/tests/test_cardiac_formulas.py \
  python/hearttwin/tests/test_hemodynamics.py \
  python/hearttwin/tests/test_recovery_sim.py \
  python/hearttwin/tests/test_ensemble.py \
  python/hearttwin/tests/test_shadow_trial_engine.py \
  python/hearttwin/tests/test_missing_piece_engine.py \
  python/hearttwin/tests/test_models.py \
  python/hearttwin/tests/test_intelligence_runtime.py \
  python/hearttwin/tests/test_vista3d_client.py \
  python/hearttwin/tests/test_openai_fallbacks.py
```

Result: **189 passed, 22 warnings, 0 failures** in 0.89 seconds. The warnings
were existing Pydantic `datetime.utcnow()` deprecations; they did not affect
the capability assertions.

The full repository Python suite was then run with the same provider variables
removed via `pnpm test:py`: **1293 passed, 5 skipped, 6 xfailed, 0 failures** in
13.04 seconds. The run emitted 506 existing deprecation warnings. The skipped
and expected-failure cases were retained as reported by pytest; they were not
converted into passes.

### End-to-end local system check

The real FastAPI `system_check()` path was executed in-process with the same
provider variables removed. It returned:

```text
SYSTEM_CHECK status=ok checks=10 failed=0
INTEGRATIONS openai=fallback weave=local_fallback redis=memory_fallback vista3d=disabled
METRICS sv=60.0 ef=46.15 co=5.28 map=101.67 rr=681.82
SAFETY disclaimer_present=True
```

The route's implementation explicitly labels itself an end-to-end deterministic
health check and validates formula, pipeline, recovery, integration fallback,
and safety results ([`api.py:613-620`](../../../python/hearttwin/api.py#L613-L620), [`api.py:648-777`](../../../python/hearttwin/api.py#L648-L777)).

### Provider and registry status probe

The no-provider probe reported:

```text
INTELLIGENCE provider=disabled enabled=False reachable=False model_configured=False
REGISTRY capability=medical-segmentation required=False configured=True available=True loaded=False
REGISTRY capability=language required=False configured=False available=False loaded=False
REGISTRY capability=embedding required=False configured=False available=False loaded=False
```

This proves safe disabled-provider selection and metadata-only registry status;
it does not prove remote provider availability or VISTA inference.

## Evidence interpretation

- The local `system_check` proves deterministic operation with optional services
  absent. It does not prove a public deployment, external persistence,
  authenticated model access, or live Weave delivery.
- The focused tests prove the checked contracts, including same-seed replay,
  deterministic paired trials, bounded sensitivity, lazy registry behavior,
  disabled-provider behavior, and model-free fallbacks. They do not validate
  model quality or clinical performance.
- A VISTA checkpoint being `available=true` in the registry means the configured
  path exists. The registry explicitly reports `loaded=false`; no model was
  loaded or downloaded during this audit.
- The word “model” in `default_model_prior` refers to a deterministic population
  prior used when evidence is missing; it is not a neural model invocation.
- The current Weave implementation retains local traces and conditionally
  initializes Weave, but this audit does not claim nested `@weave.op` spans or a
  flushed remote trace. Those are separate integration claims.

## Risks and open checks

1. **Live provider claims remain open.** A future live check must use synthetic
   input, report only provider/model identity and reachability, and never print
   credentials or raw uploaded content.
2. **Image extraction is a capability gap when the provider is disabled.** The
   safe behavior is explicit empty extraction, not a deterministic substitute
   for visual reading.
3. **VISTA availability is not segmentation proof.** The active API adapter is
   asynchronous and optional; checkpoint compatibility, service reachability,
   inference completion, and returned-mask provenance require separate checks.
4. **Model-free fallbacks can be less expressive.** Rule-based routing and
   template scenario selection preserve safety and determinism but are not
   equivalent to validating a live language model's quality.
5. **External services are outside this result.** Redis durability, Weave UI
   traces, external medication/guideline retrieval, public TLS/proxy behavior,
   and browser/WebGL behavior were not asserted by this audit.
6. **Clinical claims are unsupported.** The repository and this audit support
   educational simulation and bounded software behavior only; they do not
   establish diagnosis, treatment value, patient probability, or clinical
   validation.

## Final disposition

**PASS — local deterministic capability boundary verified.** BeatIT can build
and evaluate its educational cardiac twin without a live model provider or
downloaded model weights, and the model-dependent paths are labelled optional
or unavailable rather than silently represented as successful.

**OPEN — live model capability verification.** Do not promote the repository
to a live-model, VISTA-inference, clinical, or externally persisted capability
claim until the corresponding provider/service smoke checks and safety-aware
E2E evidence are separately recorded.
