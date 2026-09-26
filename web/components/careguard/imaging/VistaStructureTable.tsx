"use client";

// VISTA per-structure results. Every row carries the model-derived label. Volumes
// are deterministic (voxels × spacing); confidence shows only if the endpoint
// returned a defined measure — never invented.
import type { VistaStructureResult } from "@/types/careguardImaging";
import { MODEL_DERIVED_LABEL } from "@/types/careguardImaging";

export function VistaStructureTable({ results }: { results: VistaStructureResult[] }) {
  if (!results.length) {
    return (
      <p style={{ fontSize: 13, color: "#555" }}>
        No VISTA segmentation available for this case (endpoint gated / no live run). No
        masks or volumes are shown because none were produced.
      </p>
    );
  }
  return (
    <div>
      <p style={{ fontSize: 12, color: "#7c3aed", fontWeight: 600 }}>{MODEL_DERIVED_LABEL}</p>
      <table style={{ borderCollapse: "collapse", fontSize: 13, width: "100%" }}>
        <thead>
          <tr>
            {["Structure", "Status", "Volume (mL)", "Confidence"].map((h) => (
              <th
                key={h}
                style={{ border: "1px solid #ddd", padding: "4px 10px", textAlign: "left" }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <tr key={r.structure_id}>
              <td style={{ border: "1px solid #ddd", padding: "4px 10px" }}>
                {r.requested_label}
              </td>
              <td style={{ border: "1px solid #ddd", padding: "4px 10px" }}>{r.status}</td>
              <td style={{ border: "1px solid #ddd", padding: "4px 10px" }}>
                {r.volume_ml == null ? "—" : r.volume_ml.toFixed(1)}
              </td>
              <td style={{ border: "1px solid #ddd", padding: "4px 10px" }}>
                {r.confidence == null ? "not supplied" : r.confidence.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default VistaStructureTable;
