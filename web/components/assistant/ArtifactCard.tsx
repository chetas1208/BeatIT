"use client";

/*
 * CONTRACT: the compact, chat-inline representation of a unified-assistant
 *   artifact — per docs/assistant/GLOBAL_ARCHITECTURE.md "ARTIFACT ARCHITECTURE",
 *   chat text and structured artifacts are separate. A chat turn says something
 *   like "I found three evidence sources supporting this" and drops one of
 *   these cards, never the raw payload. Clicking "View" is the only way to see
 *   the real detail (ArtifactDetailPanel).
 *
 * Type note (Wave 4 / Agent 18): `web/types/assistant.ts` (owned by Agent 16,
 * building `BeatITCopilotPanel.tsx` concurrently this same wave) did NOT exist
 * in this tree when this task started — checked via `ls`/`find` first. It
 * landed mid-task (concurrent timing), so this file imports its
 * `AssistantArtifact`/`AssistantArtifactType`/`ProvenanceRef` types rather
 * than redefining them, per GLOBAL_ARCHITECTURE.md's "1 artifact system"
 * invariant. `web/types/assistant.ts` itself is never edited here (out of
 * scope for this task).
 */

import type { Icon } from "@phosphor-icons/react";
import {
  ChartLineUp,
  ClipboardText,
  ClockCounterClockwise,
  Flask,
  Gauge,
  Heartbeat,
  Table,
} from "@phosphor-icons/react";
import type { AssistantArtifact, AssistantArtifactType } from "@/types/assistant";

export type { AssistantArtifact, AssistantArtifactType, ProvenanceRef } from "@/types/assistant";

// ---------------------------------------------------------------------------
// Per-type presentation. Only PHYSICIAN_BRIEF has a real generator today
// (python/hearttwin/assistant/physician_brief.py) — the other 6 are reserved
// in AssistantArtifactType but have no backend producer yet (Wave 2's tool
// registry only returns raw ToolResults). The card still needs to render
// something honest for all 7, since the chat surface can't predict which
// type a future wave wires up first.
// ---------------------------------------------------------------------------

const ARTIFACT_META: Record<AssistantArtifactType, { label: string; icon: Icon }> = {
  cardiac_component_report: { label: "Component report", icon: Heartbeat },
  timeline_summary: { label: "Timeline summary", icon: ClockCounterClockwise },
  evidence_table: { label: "Evidence table", icon: Table },
  pv_comparison: { label: "PV comparison", icon: ChartLineUp },
  shadow_trial_summary: { label: "Shadow trial summary", icon: Flask },
  uncertainty_analysis: { label: "Uncertainty analysis", icon: Gauge },
  physician_brief: { label: "Physician brief", icon: ClipboardText },
};

/** True only for the one type this wave gave a real payload shape/generator. */
export function hasRealArtifactView(type: AssistantArtifactType): boolean {
  return type === "physician_brief";
}

// ---------------------------------------------------------------------------
// One-line summary, derived defensively from the payload — never fabricated.
// Every other artifact type's payload shape is unknown until its own wave
// lands, so this only reaches into the one shape we do know
// (DecisionSupportBundle) and otherwise falls back to an honest source count.
// ---------------------------------------------------------------------------

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function summarize(artifact: AssistantArtifact): string {
  if (artifact.type === "physician_brief") {
    const payload = asRecord(artifact.payload);
    const derived = Array.isArray(payload.derived_evidence) ? payload.derived_evidence.length : 0;
    const observed = Array.isArray(payload.observed_evidence) ? payload.observed_evidence.length : 0;
    const simulated = Array.isArray(payload.simulated_results) ? payload.simulated_results.length : 0;
    const total = observed + derived + simulated;
    const parts: string[] = [];
    if (observed) parts.push(`${observed} observed`);
    if (derived) parts.push(`${derived} derived`);
    if (simulated) parts.push(`${simulated} simulated`);
    return parts.length
      ? `${parts.join(", ")} finding${total === 1 ? "" : "s"}`
      : "No findings populated yet";
  }

  const sourceCount = artifact.source_tool_ids.length;
  return sourceCount > 0
    ? `From ${sourceCount} tool result${sourceCount === 1 ? "" : "s"}`
    : "No source tools recorded";
}

// ---------------------------------------------------------------------------
// The card itself.
// ---------------------------------------------------------------------------

export function ArtifactCard({
  artifact,
  onView,
}: {
  artifact: AssistantArtifact;
  onView?: (artifact: AssistantArtifact) => void;
}) {
  const meta = ARTIFACT_META[artifact.type];
  const IconCmp = meta?.icon ?? ClipboardText;
  const label = meta?.label ?? artifact.type;

  return (
    <div className="ht-panel my-1.5 flex w-full items-center gap-2.5 overflow-hidden px-3 py-2.5">
      <span
        aria-hidden
        className="grid size-8 flex-none place-items-center rounded-[var(--ht-r-sm)] border border-[var(--ht-line)] bg-surface-2 text-signal-bright"
      >
        <IconCmp weight="duotone" className="size-4" />
      </span>
      <div className="flex min-w-0 flex-1 flex-col leading-tight">
        <span className="ht-eyebrow">{label}</span>
        <span className="truncate text-[0.84rem] font-semibold text-ink">{artifact.title}</span>
        <span className="truncate text-[0.72rem] text-muted">{summarize(artifact)}</span>
      </div>
      <button
        type="button"
        onClick={() => onView?.(artifact)}
        className="ht-btn ht-btn-secondary h-8 flex-none px-3 text-[0.78rem]"
        aria-label={`View ${label.toLowerCase()}: ${artifact.title}`}
      >
        View
      </button>
    </div>
  );
}
