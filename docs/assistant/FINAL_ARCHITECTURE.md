# BeatIT Copilot — Final Architecture

Canonical invariant: `docs/assistant/GLOBAL_ARCHITECTURE.md`.

## User-facing

- **BeatIT Copilot** — one panel on the cardiac console (default enabled).
- **CareGuard copilot** — separate, feature-flagged product tab (justified).
- **CopilotDock** — legacy; hidden when unified assistant is enabled.

## Request path

`BeatITCopilotPanel` → `POST /api/v1/assistant/message` → `orchestrator.handle_message`:

1. Input safety rail  
2. Context resolution  
3. Laya / deterministic System-1  
4. Tool registry (8 tools)  
5. Optional NVIDIA System-2 (gated)  
6. Numeric + output safety rails  
7. Artifacts optional  

## Data plane

CardiacTwinState, ensembles, cases, shadow trials, missing piece — accessed only through existing Python engines and storage; LLMs never compute physiology.

## Certification

`docs/assistant/certification/FINAL_RELEASE_DECISION.md`
