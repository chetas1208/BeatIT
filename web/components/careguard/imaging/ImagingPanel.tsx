"use client";

// Additive imaging section for the CareGuard console. Shows the linkage state,
// limitations, and (for imaging cases) VISTA results. When a clinical case has no
// verified CT it shows an honest message and a SEPARATE independent-demo entry —
// never a random substitute CT presented as the patient's.
import { useCallback, useState } from "react";
import { careguardImagingApi } from "@/lib/careguardImagingApi";
import type { CtImaging, VistaStructureResult } from "@/types/careguardImaging";
import ImagingLinkageBadge from "./ImagingLinkageBadge";
import ImagingLimitations from "./ImagingLimitations";
import VistaStructureTable from "./VistaStructureTable";

export function ImagingPanel({
  caseId,
  ctImaging,
  vistaResults = [],
}: {
  caseId: string;
  ctImaging: CtImaging;
  vistaResults?: VistaStructureResult[];
}) {
  const [fuseMsg, setFuseMsg] = useState<string | null>(null);

  const tryFuse = useCallback(async () => {
    const { status, body } = await careguardImagingApi.fuse(caseId);
    setFuseMsg(
      status === 409
        ? `Blocked (409): ${body.message}`
        : `Fusion allowed: ${body.linkage_status}`,
    );
  }, [caseId]);

  const hasVerifiedCt =
    ctImaging.status === "same_subject_verified" ||
    ctImaging.status === "imaging_native_same_subject";

  return (
    <section style={{ display: "grid", gap: 12, padding: 16, border: "1px solid #e5e7eb", borderRadius: 12 }}>
      <header style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>CT imaging</h3>
        <ImagingLinkageBadge ctImaging={ctImaging} />
      </header>

      <ImagingLimitations ctImaging={ctImaging} />

      {hasVerifiedCt ? (
        <VistaStructureTable results={vistaResults} />
      ) : (
        <div style={{ fontSize: 13, color: "#374151" }}>
          <p style={{ margin: "0 0 8px" }}>
            No verified same-subject CT is available for this case.
          </p>
          <button
            type="button"
            onClick={tryFuse}
            style={{
              padding: "6px 12px",
              borderRadius: 8,
              border: "1px solid #94a3b8",
              background: "#f1f5f9",
              cursor: "pointer",
            }}
          >
            Open independent VISTA imaging demonstration
          </button>
          <p style={{ margin: "8px 0 0", fontSize: 12, color: "#6b7280" }}>
            The demonstration uses an independent imaging benchmark case (not this patient&apos;s CT).
          </p>
          {fuseMsg && (
            <p style={{ marginTop: 8, color: fuseMsg.startsWith("Blocked") ? "#991b1b" : "#166534" }}>
              {fuseMsg}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

export default ImagingPanel;
