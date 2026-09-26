# Wave 1 — Bedrock migration forensics (2026-09-26)

## IMPLEMENTED

- Repository audit for NVIDIA inference vs GPU/imaging references.
- Live Bedrock capability check in `us-east-1` (12 OpenAI foundation models, 16 inference profiles).
- Provider architecture map and migration seam identification.
- Assistant agent / model-client inventory.
- Environment & secret boundary audit (no secret values printed).

## ARCHITECTURE CHANGES

- **Decision locked:** NVIDIA Build / Nemotron / `nvapi` inference is **removed** from the active assistant path.
- **Replacement:** AWS Bedrock OpenAI-compatible Chat Completions on `bedrock-runtime` (bearer or IAM).
- **New module:** `python/hearttwin/intelligence/bedrock/` (`models.py`, `health.py`).
- **Wave 2 started:** `model_pool.py` → Bedrock role registry only; `model_client.py` → `complete_text`; orchestrator FAST/BALANCED/DEEP routing.

## NVIDIA REMOVAL MATRIX

| Area | Classification | Action |
|------|----------------|--------|
| `assistant/model_pool.py` (key pool) | ACTIVE | **Removed** — registry only |
| `assistant/model_client.py` (NVIDIA HTTP) | ACTIVE | **Rewired** to intelligence provider |
| `.env` `MODEL_API_KEY_*`, `integrate.api.nvidia.com` | ACTIVE | **Removed** from `.env` |
| Pipeline agents via `complete_text` | ACTIVE | Already Bedrock-capable; keep OPENAI_MODEL_* as profile IDs |
| `test_model_pool.py`, `test_model_client.py` | ACTIVE | **Rewritten** |
| `docs/assistant/NVIDIA_*.md`, wave handoffs | DOCUMENTATION | Mark historical; Wave 3+ benchmarks on Bedrock |
| VISTA-3D / CUDA / PyTorch / MONAI docs | UNRELATED GPU | **Keep** |
| `HeartScene` `AnimatePresence` (motion/react) | UNRELATED | **Keep** |

**Target counts after campaign:** NVIDIA Build API calls **0**, NVIDIA model routes **0**, NVIDIA API keys required **0**.

## AWS / BEDROCK (verified locally)

| Item | Value |
|------|--------|
| Region | `us-east-1` |
| Auth | Workshop IAM session + Bedrock bearer (`refresh_bedrock_model_key.py`) |
| Endpoint | `https://bedrock-runtime.us-east-1.amazonaws.com/openai/v1` |
| Protocol (now) | Chat Completions (Responses API evaluation = Wave 2–3) |
| Discovery | `aws bedrock list-foundation-models --by-provider OpenAI`; **not** `GET /models` on runtime |

### Initial model hypothesis (env: `MODEL_*`)

| Role | Profile ID |
|------|------------|
| FAST | `global.openai.gpt-5.6-luna` |
| BALANCED | `global.openai.gpt-5.6-terra` |
| DEEP | `global.openai.gpt-5.6-sol` |
| SAFETY (optional) | `openai.gpt-oss-safeguard-20b` |

All project-configured chat models passed smoke tests (see `scripts/test_bedrock_models.py`).

## AGENT / MODEL CLIENT INVENTORY

| Component | LLM path |
|-----------|----------|
| `assistant/orchestrator.py` | Laya → tools → `chat_completion` → **`complete_text`** |
| `assistant/model_client.py` | **`complete_text`** (canonical) |
| Pipeline agents (`intake`, `extraction`, …) | **`complete_text`** + `OPENAI_MODEL_*` |
| `copilot.py` | **`complete_text`** |
| `tools/image_extract.py` | **`complete_text`** |
| CareGuard | Separate Anthropic/env path — **out of Bedrock wave scope** unless unified later |

## FILES (Wave 1 + early Wave 2)

- `python/hearttwin/intelligence/bedrock/*`
- `python/hearttwin/assistant/model_pool.py`
- `python/hearttwin/assistant/model_client.py`
- `python/hearttwin/assistant/orchestrator.py`
- `python/hearttwin/intelligence/factory.py`
- `python/hearttwin/intelligence/openai_provider.py`
- `python/hearttwin/tests/test_model_pool.py`
- `python/hearttwin/tests/test_model_client.py`
- `python/hearttwin/tests/test_model_reliability.py`
- `.env` / `.env.example` (placeholders only in example)

## TESTS

```bash
python -m pytest -q \
  python/hearttwin/tests/test_model_pool.py \
  python/hearttwin/tests/test_model_client.py \
  python/hearttwin/tests/test_model_reliability.py \
  python/hearttwin/tests/test_intelligence_runtime.py \
  python/hearttwin/tests/test_orchestrator_model_routing.py
```

## FAILURES

- Full 20-agent wave campaign not completed in one session (Wave 1 + partial Wave 2 only).
- `test_orchestrator_model_routing.py` may still reference NVIDIA in integration-test comments — update in Wave 2.
- CareGuard / legacy docs still mention NVIDIA historically.

## SECURITY

- No secrets in this handoff.
- `.env` gitignored; no `NEXT_PUBLIC_*` AWS keys.
- Bearer rotation: `scripts/refresh_bedrock_model_key.py`.

## MEDICAL / DATA INTEGRITY

- Deterministic physics core unchanged.
- Orchestrator still runs numeric + output safety validators on model text.
- No LLM authority over EF/SV/CO/MAP/etc.

## NEXT DEPENDENCIES (Wave 2 gate)

**Completed in Bedrock waves 2–8.** See `WAVE_2_HANDOFF.md` … `WAVE_8_HANDOFF.md` and `FINAL_CERTIFICATION.md`.

## GLOBAL ARCHITECTURE COMPLIANCE

**YES** for Wave 1 scope (NVIDIA inference removed from assistant path; single Copilot + Laya + tools preserved).

---

Official links: [Bedrock APIs](https://docs.aws.amazon.com/bedrock/latest/userguide/apis.html), [Responses API](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-responses-api.html), [Chat Completions](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-chat-completions.html), [OpenAI model cards](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards-openai.html), [API compatibility](https://docs.aws.amazon.com/bedrock/latest/userguide/models-api-compatibility.html), [Getting started](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html), [Laya](https://github.com/NandhaKishorM/laya).
