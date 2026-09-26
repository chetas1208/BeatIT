# Physician-Support Boundary Audit (Certification Wave A5)

Physician support = **`ConversationContext.audience == "physician"`** on the
**same** orchestrator (`GLOBAL_ARCHITECTURE.md`), plus `physician_brief.py`
artifact generation (not auto-invoked on every message today).

## Flow classification

| Class | Mechanism | Example |
|-------|-----------|---------|
| **Informational** | Tool read + deterministic render | Ensemble uncertainty message |
| **Evidence support** | T0 tools | `get_raw_provenance_ledger`, findings |
| **Simulation support** | REST / CopilotKit actions (legacy) | operate, ensemble, shadow trial — not all in ToolRegistry |
| **Decision support** | `DecisionSupportBundle` / `PHYSICIAN_BRIEF` artifact | Observed/derived/simulated sections — no `recommended_treatment` |
| **High-stakes blocked** | `classify_request_safety` pre-Laya | Treatment, diagnosis, emergency phrasing → `HUMAN_DECISION_REQUIRED` |
| **Output blocked** | `check_output_safety`, `language_integrity`, `report_consistency` | Imperative prescribing language stripped |

## Legacy physician-adjacent surfaces

| Surface | Boundary |
|---------|----------|
| CopilotKit `answer_case_question` | OpenAI over case JSON — **not** unified orchestrator rails (numeric validator, Laya policy) |
| CareGuard copilot | Refuses dosing; separate disclaimer string |
| Intake agent | Blocks treatment in notes at case creation |

## Gaps

- Unified panel always sends `audience: "general"` — physician policy not exposed in UI.
- `build_physician_brief` exists but is not wired as default tool route in orchestrator.
- Wave 6 deep-model jailbreak documented — post-output safety is load-bearing.

## Compliance

Physician **mode** architecture is sound in schema; **product** still splits
across three chat backends until certification Waves C–E complete.
