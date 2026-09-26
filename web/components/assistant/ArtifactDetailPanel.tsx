"use client";

/*
 * CONTRACT: the expandable detail surface an ArtifactCard's "View" affordance
 *   opens. Dispatches by artifact.type — PHYSICIAN_BRIEF gets the real
 *   PhysicianBriefView; the other 6 types (reserved in
 *   python/hearttwin/assistant/schemas.py's AssistantArtifactType but with no
 *   backend generator yet, per docs/assistant/WAVE_3_HANDOFF.md) get an
 *   honestly-labeled raw-payload fallback rather than a fabricated view or a
 *   crash. Modeled as a slide-in/modal after the existing
 *   web/components/heart/report/ComponentReportPanel.tsx pattern (role="dialog"
 *   aria-modal, full-bleed over the panel it's opened from) so it matches this
 *   codebase's one existing detail-overlay convention instead of inventing a
 *   second one.
 */

import { useRef } from "react";
import { X } from "@phosphor-icons/react";
import { useFocusTrap } from "@/lib/assistant/useFocusTrap";
import type { AssistantArtifact } from "./ArtifactCard";
import { hasRealArtifactView } from "./ArtifactCard";
import { PhysicianBriefView } from "./PhysicianBriefView";

/** Pretty-print an arbitrary payload as key: value lines, recursing one level
 * into nested objects/arrays via JSON — this is a deliberately unpolished
 * placeholder, not a real view (see module contract above). */
function RawPayloadFallback({ artifact }: { artifact: AssistantArtifact }) {
  const entries = Object.entries(artifact.payload ?? {});
  return (
    <div className="space-y-3">
      <div className="flex items-start gap-2 rounded-[var(--ht-r-sm)] border border-[var(--ht-warn-line)] bg-[var(--ht-warn-soft)] px-3 py-2.5 text-[0.78rem] leading-relaxed text-ink-2">
        <span>
          A detailed view is not yet available for artifact type{" "}
          <code className="ht-mono">{artifact.type}</code> — no backend generator produces a
          typed payload for this type yet (Wave 4). Showing the raw payload data below instead
          of a real view.
        </span>
      </div>
      {entries.length === 0 ? (
        <p className="text-[0.78rem] italic text-muted">This artifact has an empty payload.</p>
      ) : (
        <dl className="space-y-2">
          {entries.map(([key, value]) => (
            <div key={key} className="rounded-[var(--ht-r-sm)] border border-[var(--ht-line)] bg-surface-2/50 px-2.5 py-2">
              <dt className="ht-eyebrow text-[0.6rem]">{key}</dt>
              <dd className="ht-mono mt-1 whitespace-pre-wrap break-words text-[0.74rem] text-ink-2">
                {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

export function ArtifactDetailPanel({
  artifact,
  onClose,
}: {
  artifact: AssistantArtifact;
  onClose: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Mounted only while open (the caller conditionally renders this panel), so
  // the trap is active for the component's whole lifetime; restores focus to
  // the ArtifactCard "View" button that opened it on unmount.
  useFocusTrap(containerRef, true, onClose);

  return (
    <div
      ref={containerRef}
      role="dialog"
      aria-modal="true"
      aria-label={`${artifact.title} detail`}
      className="absolute inset-0 z-30 overflow-y-auto bg-[var(--ht-surface-1)] p-5"
    >
      <div className="mx-auto max-w-2xl">
        <div className="flex items-start justify-between">
          <div>
            <p className="ht-eyebrow">BeatIT assistant artifact</p>
            <h2 className="mt-1 text-xl font-semibold text-ink">{artifact.title}</h2>
          </div>
          <button
            type="button"
            aria-label="Close artifact detail"
            onClick={onClose}
            className="ht-btn ht-btn-ghost"
          >
            <X size={16} />
          </button>
        </div>

        <div className="mt-5">
          {hasRealArtifactView(artifact.type) ? (
            <PhysicianBriefView artifact={artifact} />
          ) : (
            <RawPayloadFallback artifact={artifact} />
          )}
        </div>

        {artifact.provenance.length > 0 ? (
          <div className="mt-6 border-t border-[var(--ht-line)] pt-3">
            <p className="ht-eyebrow">Provenance</p>
            <ul className="mt-2 space-y-1 text-[0.74rem] text-muted">
              {artifact.provenance.map((ref, i) => (
                <li key={i}>
                  <span className="text-ink-2">{ref.kind}</span>
                  {ref.source_id ? ` · ${ref.source_id}` : ""}
                  {ref.description ? ` — ${ref.description}` : ""}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}
