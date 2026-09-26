/*
 * Single source of truth for the unified-assistant feature flag.
 *
 * Wave 4 ("Legacy Chat Removal Engineer" audit + Agent 16's new unified panel)
 * introduces NEXT_PUBLIC_UNIFIED_ASSISTANT_ENABLED so the new panel can ship
 * dark (default OFF) alongside the two still-live legacy chat surfaces
 * (CopilotDock, CareGuardCopilot) without regressing them. This helper exists
 * only to stop every future caller from re-typing the raw env-var string
 * (and risking a typo'd flag name or an inconsistent truthy-check) — see
 * docs/assistant/wave4/legacy-chat-removal-plan.md for the removal plan this
 * flag gates.
 *
 * Convention mirrors the existing NEXT_PUBLIC_CAREGUARD_ENABLED flag
 * (web/lib/careguardApi.ts, web/components/layout/AppShell.tsx): default to
 * disabled on any missing/unset value, case-insensitive "true" to opt in.
 *
 * Not wired into any component by this wave — callers (Agent 16's unified
 * panel, or a future AppShell edit) import and call this instead of reading
 * process.env directly.
 */

export function isUnifiedAssistantEnabled(): boolean {
  return (
    (process.env.NEXT_PUBLIC_UNIFIED_ASSISTANT_ENABLED ?? "false").toLowerCase() === "true"
  );
}
