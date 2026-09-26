"use client";

// The linkage state is NEVER hidden. This badge renders the exact ct_imaging
// status for a case, including the "invalid cross-dataset pairing removed" state.
import type { CtImaging } from "@/types/careguardImaging";
import { LINKAGE_BADGE } from "@/types/careguardImaging";

const TONE: Record<string, { bg: string; fg: string; border: string }> = {
  ok: { bg: "#dcfce7", fg: "#166534", border: "#16a34a" },
  info: { bg: "#e0f2fe", fg: "#075985", border: "#0891b2" },
  warn: { bg: "#fef3c7", fg: "#92400e", border: "#f59e0b" },
  danger: { bg: "#fee2e2", fg: "#991b1b", border: "#dc2626" },
};

export function ImagingLinkageBadge({ ctImaging }: { ctImaging: CtImaging }) {
  const meta = LINKAGE_BADGE[ctImaging.status] ?? {
    label: ctImaging.status,
    tone: "warn" as const,
  };
  const c = TONE[meta.tone];
  return (
    <span
      title={ctImaging.reason}
      style={{
        display: "inline-flex",
        gap: 6,
        alignItems: "center",
        padding: "2px 10px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        background: c.bg,
        color: c.fg,
        border: `1px solid ${c.border}`,
      }}
    >
      <span aria-hidden>🩻</span>
      {meta.label}
      {ctImaging.same_subject_as_clinical_record === false &&
        ctImaging.status === "imaging_only" && (
          <span style={{ fontWeight: 400, opacity: 0.8 }}>· different subject</span>
        )}
    </span>
  );
}

export default ImagingLinkageBadge;
