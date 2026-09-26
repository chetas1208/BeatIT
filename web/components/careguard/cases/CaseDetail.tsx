"use client";

// Composite case demo: EHR summary + ECG + echo (matched external modalities,
// clearly donor-labeled) + CT linkage + quality. Never presents a matched modality
// as the eICU patient's own.
import { useEffect, useState } from "react";
import { careguardCasesApi, type CaseDemo } from "@/lib/careguardCasesApi";
import ImagingLinkageBadge from "@/components/careguard/imaging/ImagingLinkageBadge";
import type { CtImaging } from "@/types/careguardImaging";

function Donor({ text }: { text?: string | null }) {
  if (!text) return null;
  return (
    <p style={{ margin: "4px 0 0", fontSize: 12, color: "#92400e", background: "#fef3c7",
      borderRadius: 6, padding: "4px 8px" }}>⚠ {text}</p>
  );
}

export function CaseDetail({ caseId }: { caseId: string }) {
  const [demo, setDemo] = useState<CaseDemo | null>(null);
  const [errorState, setErrorState] = useState<{ caseId: string; message: string } | null>(null);

  useEffect(() => {
    let active = true;
    careguardCasesApi.demo(caseId)
      .then((result) => {
        if (!active) return;
        setDemo(result);
        setErrorState(null);
      })
      .catch((e) => {
        if (active) setErrorState({ caseId, message: String(e) });
      });
    return () => {
      active = false;
    };
  }, [caseId]);

  const currentDemo = demo?.case_id === caseId ? demo : null;
  const err = errorState?.caseId === caseId ? errorState.message : null;
  if (err) return <p style={{ color: "#991b1b" }}>Failed to load {caseId}: {err}</p>;
  if (!currentDemo) return <p>Loading {caseId}…</p>;

  const s = currentDemo.summary as {
    demographics?: { age_band?: unknown; gender?: unknown; icu_type?: unknown };
    cardiovascular_context?: string[];
    noncardiac_organ_systems?: string[];
  };
  const demoAsset = (name: string) =>
    currentDemo.assets[name] ? careguardCasesApi.assetUrl(currentDemo.assets[name]) : null;

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <h2 style={{ margin: 0 }}>{currentDemo.case_id}</h2>
        {currentDemo.ct_imaging && (
          <ImagingLinkageBadge ctImaging={currentDemo.ct_imaging as CtImaging} />
        )}
        <span style={{ fontSize: 13, color: "#555" }}>
          {String(s?.demographics?.age_band ?? "")} · {String(s?.demographics?.gender ?? "")} ·{" "}
          {String(s?.demographics?.icu_type ?? "")}
        </span>
      </div>

      <p style={{ fontSize: 12, background: "#fef3c7", borderLeft: "4px solid #f59e0b",
        borderRadius: 6, padding: "8px 12px", color: "#78350f" }}>
        {currentDemo.composite_notice}
      </p>

      <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div style={{ border: "1px solid #e5e7eb", borderRadius: 10, padding: 12 }}>
          <h4 style={{ margin: "0 0 6px" }}>Cardiovascular context</h4>
          <p style={{ margin: 0, fontSize: 13 }}>
            {(s?.cardiovascular_context ?? []).join(", ") || "n/a"}
          </p>
          <h4 style={{ margin: "10px 0 6px" }}>Non-cardiac organ systems</h4>
          <p style={{ margin: 0, fontSize: 13 }}>
            {(s?.noncardiac_organ_systems ?? []).join(", ")}
          </p>
          <h4 style={{ margin: "10px 0 6px" }}>Completeness</h4>
          <p style={{ margin: 0, fontSize: 13 }}>
            {currentDemo.quality.overall_completeness_score ?? "—"}
          </p>
        </div>

        <div style={{ border: "1px solid #e5e7eb", borderRadius: 10, padding: 12 }}>
          <h4 style={{ margin: "0 0 6px" }}>ECG — matched external modality (PTB-XL)</h4>
          {demoAsset("ecg.png") ? (
            <img src={demoAsset("ecg.png")!} alt="ECG" style={{ maxWidth: "100%", maxHeight: 220 }} />
          ) : (
            <p style={{ fontSize: 13 }}>No ECG.</p>
          )}
          <Donor text={currentDemo.modalities.ecg.warning} />
        </div>
      </section>

      <section style={{ border: "1px solid #e5e7eb", borderRadius: 10, padding: 12 }}>
        <h4 style={{ margin: "0 0 6px" }}>
          Echocardiogram — matched external modality (EchoNet-Dynamic)
        </h4>
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
          {demoAsset("echo.gif") ? (
            <img src={demoAsset("echo.gif")!} alt="Echocardiogram"
              style={{ width: 224, imageRendering: "pixelated", borderRadius: 6, background: "#000" }} />
          ) : (
            <p style={{ fontSize: 13 }}>No echo.</p>
          )}
          <div style={{ fontSize: 13 }}>
            <p style={{ margin: "0 0 4px" }}>
              <strong>Donor EF:</strong> {currentDemo.modalities.echo.donor_ejection_fraction_pct ?? "—"}%
            </p>
            <p style={{ margin: 0, color: "#92400e" }}>
              {currentDemo.modalities.echo.note ?? "Donor value — not the eICU patient's."}
            </p>
            <Donor text={currentDemo.modalities.echo.warning} />
          </div>
        </div>
      </section>

      {currentDemo.quality.warnings.length > 0 && (
        <details style={{ fontSize: 12, color: "#555" }}>
          <summary>Data-quality warnings ({currentDemo.quality.warnings.length})</summary>
          <ul>{currentDemo.quality.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </details>
      )}
    </div>
  );
}

export default CaseDetail;
