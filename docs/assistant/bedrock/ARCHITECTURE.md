# Bedrock assistant architecture

BeatIT assistant and pipeline LLM calls use a single intelligence seam:

`complete_text()` → `IntelligenceProvider` → Bedrock OpenAI-compatible HTTP.

## Layers

| Layer | Module | Responsibility |
|-------|--------|------------------|
| Agents / orchestrator | `assistant/*`, `agents/*`, `copilot.py` | Domain prompts; never raw HTTP |
| Model roles | `intelligence/bedrock/models.py` | `MODEL_FAST/BALANCED/DEEP/SAFETY` |
| Factory | `intelligence/factory.py` | `INTELLIGENCE_PROVIDER=bedrock_openai` |
| Bedrock adapters | `intelligence/bedrock/{auth,chat_completions,responses,health}.py` | Bearer auth, protocol selection |
| Deterministic core | `tools/cardiac_state.py`, `hemodynamics.py`, `recovery_sim.py` | Sacred — LLMs do not compute physics |

## Routing

- **Laya** (System-1): intent / complexity typing — no cloud LLM required for routing.
- **Orchestrator**: FAST / BALANCED / DEEP via `get_model_id(ModelRole)`.
- **Pipeline agents**: per-agent `OPENAI_MODEL_*` env profile IDs (Bedrock inference profiles).

## Protocol

- Default: **Chat Completions** (`MODEL_API_PROTOCOL=openai-compatible`).
- Optional: **Responses API** for GPT-5.x; GPT-OSS and Safeguard remain on chat completions.

## Non-goals

- NVIDIA Build / Nemotron inference (removed from `python/`).
- CareGuard Anthropic path (separate product surface).
