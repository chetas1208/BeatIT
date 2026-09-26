# Laya Results (Certification Wave B)

Source: `docs/assistant/wave5/artifacts/metrics_summary_v2.json` (160 fixtures).

## Policy (production)

- **Default path:** deterministic fallback in `laya_adapter.py` when `LAYA_ENABLED=false`.
- **Threshold gating:** `laya_policy.py` uses measured accuracy; `classify_intent` at **58.6%** → defers to clarification before any NVIDIA call.
- **Real server:** zero-shot `convaiinnovations/laya` **65.0%** overall vs fallback **80.6%** on BeatIT fixtures — fallback preferred for routing today except research.

## Per-decision (fallback vs real Laya)

| Decision | Fallback acc | Real Laya acc | Real ECE (where computed) |
|----------|--------------|---------------|---------------------------|
| classify_intent | 58.6% | **75.9%** | 0.151 |
| select_tool_family | **73.3%** | 63.3% | 0.126 |
| needs_evidence_retrieval | **85.0%** | 65.0% | 0.144 |
| needs_simulation | **90.0%** | 70.0% | 0.177 |
| needs_clarification | **95.2%** | 52.4% | 0.313 |
| needs_physician_review_framing | **90.0%** | 75.0% | 0.059 |
| is_complex_reasoning_required | **85.0%** | 50.0% | 0.325 |

## Adversary (Wave B2 summary)

Six known gaps remain `xfail` in `test_decision_adversary.py` (leetspeak, inserted-space, phrasing gaps, routing quirks). NVIDIA content-safety model caught 4/6 in Wave 6 evaluation — optional additive rail, not wired by default.

## Fine-tuning

Not deployed. Laya docs recommend domain specialization; BeatIT defers until baseline + calibration campaign justify it.

## Fallback

Verified: `LAYA_ENABLED=false` → deterministic router (`test_certification_failure_matrix.py`).
