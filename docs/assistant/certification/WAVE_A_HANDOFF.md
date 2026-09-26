# Wave A Handoff — Architecture Forensics

## What was implemented

- Five certification artifacts under `docs/assistant/certification/` (A1–A5).
- **Integration repairs (P1):**
  - Register Wave 3 physician tools on the singleton registry at first
    `get_tool_registry()` call (`tool_registry.py`).
  - Map `patient_id` → `case_id` for tool arg resolution (`orchestrator.py`).
  - Unified panel sends `patient_id` from active `caseId` (`BeatITCopilotPanel.tsx`).
  - Updated `test_tool_registry.py` expected tool set (8 tools).

## Shared contracts changed

- Tool singleton now includes physician tools by default.
- Tool dispatch accepts `patient_id` as alias for required `case_id`.

## Files added

`docs/assistant/certification/{DUPLICATE_SYSTEM_AUDIT,REQUEST_PATH,CONTEXT_STATE_AUDIT,TOOL_AUTHORITY_MATRIX,PHYSICIAN_SUPPORT_BOUNDARIES,WAVE_A_HANDOFF}.md`

## Files modified

`tool_registry.py`, `orchestrator.py`, `test_tool_registry.py`,
`BeatITCopilotPanel.tsx`

## Architecture decisions

- CareGuard copilot remains **JUSTIFIED** second surface until explicit product merge.
- CopilotKit dock remains **LEGACY** pending Wave C–E consolidation.
- `patient_id` in API context means BeatIT **case id** until a distinct patient model exists.

## Tests

Run: `pnpm test:py` (full suite) after Wave A integration.

## Known failures / open P0–P1

- **P0:** More than one ordinary chat entry point (3 launchers).
- **P1:** UI context events not sent to backend; conversation not reset on case switch.
- **P1:** `case_context.py` not wired to orchestrator.
- **P1:** CopilotKit path bypasses unified rails.

## Security / medical risks

- Legacy OpenAI Q&A path lacks unified numeric validator on all responses.
- Physician audience mode not exposed in unified UI.

## Next-wave dependencies (Wave B)

- Laya benchmark on integrated adapter + policy (`wave5` artifacts baseline).
- NVIDIA fast/deep re-benchmark with locked registry and context alias fix.
- Read `GLOBAL_ARCHITECTURE.md` + this handoff before spawning B1–B5.

## Global Architecture Compliance

**NO** — duplicate chat surfaces and parallel copilot backends remain. Unified
stack is structurally aligned with the invariant; consolidation and proof are
Wave B–E scope.
