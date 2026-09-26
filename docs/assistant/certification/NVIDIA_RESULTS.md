# NVIDIA Results (Certification Wave B)

Sources: `docs/assistant/wave6/{fast-model-benchmark,deep-model-benchmark,safety-model-evaluation,cost-latency-reliability}.md`.

## Locked IDs (hypothesis, benchmarked 2026-09-26)

| Role | Model ID | Status |
|------|----------|--------|
| FAST | `nvidia/nemotron-3.5-lightning-30b-a3b` | Live; **not suitable** as fast chat (CoT preamble, 4–56s latency) |
| DEEP | `nvidia/nemotron-3-super-120b-a12b` | Live; strong grounding tests; **must keep output safety gates** (prescribe jailbreak documented) |
| SAFETY (eval only) | `nvidia/nemotron-3.5-content-safety` | 4/6 adversarial bypasses caught; 0 FP on benign BeatIT text; fail-open recommended |

## Key pool

- 3× `MODEL_API_KEY_*` — round-robin verified under real load (Wave 6).
- Simulated failure matrix: `test_model_reliability.py` (1/2/3 keys down).
- **No credentials printed** in docs or tests.

## Routing policy (Wave B5)

1. Deterministic tool when args resolve.  
2. Else `should_defer_to_clarification` (conservative).  
3. Else FAST vs DEEP via `is_complex_reasoning_required`.  
4. Output: `validate_numeric_claims` + `check_output_safety`.  
5. Any model failure → safe deterministic/clarification fallback.

## Numeric hallucination (deep model tests)

Tool-planning and provenance tests: **0** fabricated tool names in Wave 6 sample. Post-gate blocked unsolicited prescribing content.
