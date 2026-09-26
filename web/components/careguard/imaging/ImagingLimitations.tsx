"use client";

// Always-visible imaging disclaimers (spec §23). Model output and imaging-only
// scans carry their mandated statements; nothing is hidden.
import type { CtImaging } from "@/types/careguardImaging";
import { IMAGING_ONLY_NOTICE, MODEL_DERIVED_LABEL } from "@/types/careguardImaging";

export function ImagingLimitations({ ctImaging }: { ctImaging: CtImaging }) {
  const lines: string[] = [
    "Research and software-testing dataset. Not for diagnosis or treatment decisions.",
    MODEL_DERIVED_LABEL,
  ];
  if (ctImaging.status === "imaging_only") lines.push(IMAGING_ONLY_NOTICE);
  if (ctImaging.status === "no_linked_ct")
    lines.push("No verified same-subject CT is available for this case.");
  if (ctImaging.status === "prohibited_cross_dataset_match")
    lines.push(
      "A previously attached CT from an unrelated subject was removed; it never belonged to this patient.",
    );
  return (
    <div
      style={{
        background: "#fef3c7",
        borderLeft: "4px solid #f59e0b",
        borderRadius: 6,
        padding: "10px 14px",
        fontSize: 13,
        color: "#78350f",
      }}
    >
      <strong>Imaging limitations</strong>
      <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
        {lines.map((l, i) => (
          <li key={i}>{l}</li>
        ))}
      </ul>
    </div>
  );
}

export default ImagingLimitations;
