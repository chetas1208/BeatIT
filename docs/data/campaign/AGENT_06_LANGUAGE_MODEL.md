# Agent 06 — Language-model runtime audit

**Date:** 2026-09-26 UTC

**Scope:** configured local language-model path and BeatIT generic/OpenAI
provider behavior.

**Safety boundary:** offline, metadata-only, disabled-provider, and fake-client
checks only. No secret values were printed or read for content, no model weights
were loaded, and no remote or local inference request was made.

## Plan

1. Read the repository operating rules and the model/provider seams.
2. Inspect the manifest, environment-variable presence, local model metadata,
   and lazy registry status without loading weights.
3. Exercise provider construction and fallback behavior with an isolated empty
   environment and fake transports only.
4. Run the focused registry, provider, API-status, and deterministic-fallback
   tests.
5. Record the evidence and a conservative release disposition.

## Evidence

### Configuration and local model path

The shell audit found all of the following unset: `BEATIT_LANGUAGE_MODEL`,
`BEATIT_EMBEDDING_MODEL`, `BEATIT_MODEL_ROOT`, `MODEL_API_KEY`,
`MODEL_BASE_URL`, `MODEL_NAME`, `INTELLIGENCE_PROVIDER`, `OPENAI_ENABLED`,
`OPENAI_API_KEY`, and `OPENAI_MODEL`. Values were not printed.

`models/manifest.json:12-16` declares language as an optional,
provider-neutral capability with `BEATIT_LANGUAGE_MODEL` as its path variable,
but supplies no `default_path`. The registry only reads metadata and checks
file/directory existence (`python/hearttwin/models/registry.py:58-84`); loading
is explicit and delegated to an adapter (`registry.py:86-103`).

The current metadata-only registry result was:

```text
medical-segmentation: configured=true, available=true, loaded=false
language:             configured=false, available=false, loaded=false, path=null
embedding:            configured=false, available=false, loaded=false, path=null
```

The host does contain model directories, including:

| Host artifact | Metadata-only observation | BeatIT status |
|---|---|---|
| `/usr/data/models/fetchhealth/Models/hpc-model-backend/models_cache/medgemma` | 8.1G directory; `Gemma3ForConditionalGeneration`; sharded safetensors and config present | Not configured or selected by BeatIT |
| `/usr/data/models/skillllm-v2/models/llama-3.1-8b-instruct` | 30G directory; `LlamaForCausalLM`; sharded safetensors and config present | Not configured or selected by BeatIT |
| `/usr/data/models/skillllm-v2/models/qwen3-14b` | 28G directory; `Qwen3ForCausalLM`; sharded safetensors and config present | Not configured or selected by BeatIT |
| `/usr/data/models/skillllm-v2/models/mistral-small-3.1-24b-instruct-2503` | 90G directory; `Mistral3ForConditionalGeneration`; safetensors and config present | Not configured or selected by BeatIT |

These are host artifacts, not usable BeatIT language providers. There is no
language default path in the BeatIT manifest, no language loader/serving
adapter wired to the registry, and no process name matching a common local
model server was observed. No listener was contacted.

### Generic/OpenAI provider behavior

The factory behavior is explicit and safe:

- `MODEL_ENABLED=false` or provider `disabled` returns the disabled provider
  (`factory.py:90-93`).
- The generic provider requires non-placeholder `MODEL_API_KEY`,
  `MODEL_BASE_URL`, and `MODEL_NAME`, and requires the exact
  `openai-compatible` protocol (`factory.py:105-116`). This means a local
  OpenAI-compatible server still needs a nonempty configured key under the
  current contract; `BEATIT_LANGUAGE_MODEL` alone does not activate it.
- The first-party OpenAI provider requires `OPENAI_ENABLED=true` plus a real
  `OPENAI_API_KEY` and `OPENAI_MODEL` (`factory.py:94-104`). Its completion and
  health paths use the OpenAI SDK and therefore were not live-tested
  (`openai_provider.py:34-110`).
- `configured_provider_or_disabled()` converts missing/invalid configuration
  into a disabled provider without failing startup (`factory.py:120-125`).
- `complete_text()` passes the deployment-selected `MODEL_NAME` to the generic
  provider rather than legacy per-agent model labels (`factory.py:132-157`).

For the generic transport, the fake-client tests confirmed the expected
`/chat/completions` URL, bearer-header construction, OpenAI-compatible message
shape, retry handling, response parsing, and conversion of legacy
`max_completion_tokens` to `max_tokens`. The implementation is in
`python/hearttwin/intelligence/generic_openai.py:54-117`; no real HTTP client
was used.

### Checks run

All checks below were run from the repository root with the repository’s
`/opt/miniconda/bin/python` environment:

```text
env -i ... python - <<'PY' ...
  empty environment: disabled provider
  complete generic configuration: provider constructed, no request issued
  enabled OpenAI configuration: provider constructed, no request issued
  OpenAI provider fake-SDK complete/health: pass; no network

python -m pytest -q \
  python/hearttwin/tests/test_api_routes.py::test_intelligence_status_is_safe \
  python/hearttwin/tests/test_api_routes.py::test_liveness_and_readiness_are_distinct \
  python/hearttwin/tests/test_api_routes.py::test_system_status_is_non_secret \
  python/hearttwin/tests/test_models.py \
  python/hearttwin/tests/test_intelligence_runtime.py \
  python/hearttwin/tests/test_openai_fallbacks.py
  24 passed, 22 warnings in 3.45s
```

The passing fallback suite confirms that the deterministic pipeline continues
to produce outputs without an OpenAI key and does not report a live model in
its trace metadata. The warnings are existing Python/Pydantic deprecation
warnings; no test failure was observed.

## Result

**A usable local language model is not configured for BeatIT.** Large local
language-model artifacts exist on the host, but BeatIT reports no configured or
available language capability and has no adapter that turns those directories
into an inference provider. Artifact presence must not be advertised as live
model availability.

The generic provider contract is structurally usable when a complete
OpenAI-compatible endpoint configuration is supplied, but endpoint reachability
was intentionally not tested. The OpenAI provider is correctly disabled in the
audited environment; its live reachability and model identity remain
unverified.

The deterministic fallback is usable and passed the focused offline checks.
The API status surfaces language as optional/degraded rather than blocking the
deterministic twin (`python/hearttwin/api.py:185-207`), while provider status
does not expose authorization data (`api.py:231-249`).

## Risks and limitations

- The model directories were inspected only through filesystem/config
  metadata. No tokenizer load, framework compatibility check, memory check, or
  inference was performed.
- Setting `BEATIT_LANGUAGE_MODEL` would affect registry metadata only; it would
  not, by itself, wire a local language runtime into the generic/OpenAI
  factory.
- The generic provider requires an API key even for a loopback endpoint. A
  local server integration must document whether a non-secret placeholder is
  accepted or the contract must be changed deliberately.
- Provider health for a configured generic or OpenAI provider performs a
  network request (`GET /models` or SDK model listing). That path was not run
  under this offline audit.
- The default model IDs returned by `model_config.py` are labels/configuration
  defaults, not evidence that credentials, reachability, or inference are
  available.

## Final disposition

**PASS — deterministic/offline fallback and safe disabled behavior.**
**NOT READY — live local, generic, or first-party OpenAI language-model
claims.**

Before a live language-model claim, an authorized follow-up must select one
approved model, provide a documented local loader or OpenAI-compatible serving
endpoint, configure secrets privately, run a bounded synthetic smoke test, and
reconfirm that deterministic outputs and safety gates remain authoritative when
the provider is absent or fails.
