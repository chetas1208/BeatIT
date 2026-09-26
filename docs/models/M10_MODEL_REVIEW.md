# M10 model inventory, runtime, and fallback review

**Date:** 2026-09-26 UTC  
**Scope:** language, VISTA-3D, and provider-neutral model runtime semantics.  
**Safety boundary:** metadata and configuration inspection only for this review;
no large language model or VISTA checkpoint was loaded and no remote inference
was attempted.

## Executive disposition

The model layer is optional and does not block the deterministic cardiac twin.
The current environment is safe for a deterministic/local fallback demo, but it
is **not evidence of a configured live language provider or live VISTA service**.
The local VISTA checkpoint is available to the lazy registry, while its service
adapter is disabled because no explicit VISTA endpoint is configured.

## Evidence captured

The following checks were run from the repository root:

```text
stat model.pt metadata.json
  model.pt: 871,970,895 bytes; regular file
  metadata.json: 8,975 bytes; regular file

ModelRegistry.status()  # metadata/filesystem inspection; no load()
  medical-segmentation: configured=true, available=true, loaded=false,
                        required=false, runtime=monai, error=null
  language:             configured=false, available=false, loaded=false,
                        required=false, runtime=provider-neutral, error=null
  embedding:            configured=false, available=false, loaded=false,
                        required=false, runtime=provider-neutral, error=null

configured_provider_or_disabled()
  provider=disabled, protocol=none, enabled=false

is_configured() for VISTA-3D service
  false
```

The existing local inventory records the VISTA checkpoint as a PyTorch/MONAI
bundle and records a prior structural CPU load validation. This review did not
repeat that load or run segmentation. See
[`LOCAL_MODEL_INVENTORY.md`](./LOCAL_MODEL_INVENTORY.md) for the inventory
record and its framework-version caveat.

## Inventory and availability

| Capability | Runtime contract | Observed artifact/configuration | Current status | Safe interpretation |
|---|---|---|---|---|
| Deterministic twin | Built-in Python tools | Repository code and golden fixtures | Available | Authoritative source for cardiac calculations; independent of an LLM |
| Medical segmentation | MONAI/VISTA-3D, lazy local registry | `/usr/data/models/vista-3d-host/models/vista3d/models/model.pt` | Available, not loaded | A checkpoint exists; this does not prove request-serving inference |
| VISTA-3D service adapter | Explicit `VISTA3D_ENABLED` plus `VISTA3D_API_BASE` | No configured endpoint in the audited environment | Disabled | CT segmentation is skipped and must not produce invented measurements |
| Language | Provider-neutral local path via `BEATIT_LANGUAGE_MODEL`, or configured provider | No local language path; no active provider | Unavailable, fallback active | Explanations are optional; deterministic tools remain usable |
| Embedding | Provider-neutral local path via `BEATIT_EMBEDDING_MODEL` | No local embedding path | Unavailable, optional | No semantic retrieval should be inferred from model inventory |
| Provider-neutral remote language | Generic OpenAI-compatible or first-party OpenAI factory | Required credentials/model/base URL are not all configured | Disabled | No network call is made by the provider factory |
| Model-key pool | Bounded provider-neutral OpenAI-compatible client | Key slots are environment-driven and secret-free in status output | Not exercised in this audit | A configured provider may fail over by slot; raw keys are never status data |

The larger MedGemma, Llama, Qwen, and Mistral artifacts listed in the existing
inventory are outside the repository's active runtime contract. Their presence
on the host is not treated as BeatIT model availability, and they were not
loaded.

## Runtime semantics

### Language

`python/hearttwin/intelligence/factory.py` selects an explicit provider only
when its configuration is complete. The generic provider requires real values
for `MODEL_API_KEY`, `MODEL_BASE_URL`, and `MODEL_NAME`; the OpenAI provider
requires `OPENAI_ENABLED=true` and a non-placeholder key/model. Missing or
invalid configuration is converted by `configured_provider_or_disabled()` to a
disabled provider rather than failing API startup.

The provider contract is transport/narrative only. It does not own cardiac
math. The assistant orchestrator catches typed model-client failures (including
no healthy key, HTTP failure, timeout, and malformed response) and returns its
deterministic response path. Returned model text is also passed through the
output-safety and numeric-claim gates before it can be shown as an answer.

Model IDs returned by `python/hearttwin/tools/model_config.py` are configuration
defaults, not proof that a model is reachable or that credentials exist. The
status endpoints therefore report provider/model state separately from those
labels.

### VISTA-3D

`python/hearttwin/tools/vista3d_client.py` is explicitly environment-gated. It
requires both the enable flag and an API base, performs a health check before
submission, returns a queued job without blocking on completion, and converts
disabled/unavailable/failed states into warning-carrying results. It does not
derive chamber volumes itself and does not turn a missing segmentation result
into a cardiac value.

The local manifest marks medical segmentation as optional and lazy. Registry
availability means only that the configured path exists as a file (or a model
directory with `config.json`); `loaded=false` is the honest current lifecycle
state. No startup path should allocate model memory.

VISTA label limitations remain material: the documented heart label is a single
heart mask rather than separate chamber/myocardium masks, and the pulmonary
artery mapping is a labelled proxy. Those outputs must remain visibly qualified
if the service is enabled.

## Fallback evidence

The following existing tests/contracts support the release behavior:

- `python/hearttwin/tests/test_intelligence_runtime.py` covers disabled-provider
  selection, incomplete generic configuration, placeholder configuration, and
  provider-factory behavior.
- `python/hearttwin/tests/test_model_client.py` covers no configured key,
  typed total failure, 429 quarantine, failover, malformed responses, and the
  invariant that raw keys do not appear in returned result representations.
- `python/hearttwin/tests/test_orchestrator_model_routing.py` covers model-call
  failure falling back to the deterministic response rather than returning an
  empty or fabricated answer.
- `python/hearttwin/tests/test_vista3d_client.py` covers disabled/missing
  endpoint behavior, endpoint failure without raising, metadata-only result
  shape, and verified label mappings.
- `/api/v1/models/status` reports registry metadata without loading checkpoints;
  `/api/v1/intelligence/status` reports safe provider health without credentials;
  `/api/health/ready` marks language and VISTA as optional/degraded when absent.

## Release decision

**Model gate: PASS for deterministic fallback; NOT READY for live model claims.**

M10 may demonstrate the deterministic twin with language and VISTA explicitly
labelled unavailable/optional. A release claiming live language explanations or
live VISTA segmentation still requires, at minimum:

1. a deployment-specific provider/endpoint configuration;
2. a health check showing reachability and the selected model identity without
   exposing credentials;
3. a bounded smoke test with a synthetic fixture; and
4. evidence that the deterministic output and safety rails remain authoritative
   when the provider is removed or fails.

No model weights were downloaded, moved, or loaded for this review.
