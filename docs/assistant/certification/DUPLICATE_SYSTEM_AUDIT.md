# Duplicate-System Audit (Certification Wave A1)

> Invariant: `docs/assistant/GLOBAL_ARCHITECTURE.md`. Prior discovery:
> `docs/assistant/CHAT_SURFACE_AUDIT.md` (Wave 1). Re-audited 2026-09-26 for
> certification.

## Verdict

**Global Architecture Compliance: PARTIAL (2026-09-26)** — main cardiac console:
**one** launcher (BeatIT Copilot, default ON; CopilotDock hidden). Whole repo:
**two** when CareGuard enabled (+ justified CareGuard copilot). Unified API:
`POST /api/v1/assistant/message`.

## Chat launchers (frontend)

| Surface | Location | Disposition | Notes |
|---------|----------|-------------|-------|
| **Cardiology Copilot (CopilotKit)** | `web/components/copilot/CopilotDock.tsx`, `AppShell.tsx` | **LEGACY → MERGE** | OpenAI + `/copilotkit`; pipeline actions + `answer_case_question` |
| **CareGuard analysis copilot** | `web/components/careguard/CareGuardCopilot.tsx` | **JUSTIFIED (separate product tab)** | Anthropic + REST; feature-flagged. Still a second chat UX when CareGuard enabled |
| **BeatIT Copilot (unified)** | `BeatITCopilotTrigger.tsx` + `BeatITCopilotPanel.tsx` | **KEEP (target primary)** | Off unless `NEXT_PUBLIC_UNIFIED_ASSISTANT_ENABLED=true`; uses `assistantApi.ts` |

Tab suppression (`AppShell` hides CopilotDock on CareGuard tab) is **visibility toggle**, not consolidation.

## Conversation APIs (backend)

| API | Module | Disposition |
|-----|--------|-------------|
| `POST /api/v1/assistant/message` | `assistant/router.py` → `orchestrator.handle_message` | **KEEP (canonical target)** |
| `/copilotkit/*` | `copilot.py` + CopilotKit SDK | **LEGACY → MERGE** actions into tool registry over time |
| `POST /api/v1/careguard/cases/{id}/copilot` | `careguard/copilot_agent.py` | **JUSTIFIED** for CareGuard-only Q&A until product merge decision |

## Model / provider clients

| Client | Path | Disposition |
|--------|------|-------------|
| Unified NVIDIA pool | `assistant/model_pool.py`, `model_client.py` | **KEEP** |
| OpenAI (CopilotKit Q&A) | `intelligence/factory.py`, `copilot.py` | **LEGACY** |
| Anthropic (CareGuard) | `careguard/anthropic/` | **JUSTIFIED** (CareGuard) |

## Tool registries

| Registry | Disposition |
|----------|-------------|
| `assistant/tool_registry.py` + `physician_tools.register_physician_tools` | **KEEP (single registry)** — physician tools now registered on singleton init (Wave A integration) |
| CopilotKit actions in `copilot.py` | **LEGACY** — parallel tool surface, not registered in `ToolRegistry` |

## Decision / routing layers

| Layer | Disposition |
|-------|-------------|
| `laya_adapter.py` + `laya_policy.py` | **KEEP (System-1)** |
| `orchestrator.py` pipeline | **KEEP (request control plane)** |
| CopilotKit client-side action routing | **LEGACY** |

## Context stores

| Store | Disposition |
|-------|-------------|
| `ConversationContext` (`assistant/schemas.py`) | **KEEP (canonical)** |
| `CaseContext` (`case_context.py`) | **KEEP (additive)** — not wired into orchestrator yet |
| `web/lib/assistant/contextEvents.ts` (Zustand) | **KEEP** — **not wired** to UI clicks / panel requests |
| CopilotKit runtime history | **LEGACY** |
| CareGuard `useState` turns | **LEGACY** |
| BeatITCopilotPanel local `turns` | **MERGE** — needs server/session persistence |

## Prompt / policy stacks

| Stack | Disposition |
|-------|-------------|
| `safety_validator.py` + `language_integrity.py` | **KEEP (deterministic rails)** |
| `python/hearttwin/safety.py` (intake rules) | **KEEP** |
| CopilotKit action docstrings | **LEGACY** |
| CareGuard copilot prompts | **JUSTIFIED** (CareGuard) |

## Recommended consolidation order (post-certification)

1. Enable unified panel by default after Wave C physician scenarios pass.
2. Route CopilotKit pipeline actions through `ToolRegistry` or proxy to same orchestrator.
3. Retire CopilotDock or reduce to thin wrapper over BeatIT Copilot.
4. CareGuard: either embed unified assistant with CareGuard context or keep justified second surface with shared safety/disclaimer constants.
