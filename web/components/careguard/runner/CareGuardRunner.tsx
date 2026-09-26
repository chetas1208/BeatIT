"use client";

// Two input modes for exercising the CareGuard pipeline end-to-end:
//   (A) Manual  — paste or upload a FHIR R4 bundle + a clinical question.
//   (B) Pre-tested — pick one of the 1,000 packaged cases (its bundle is fetched).
// Either way: import → deterministic PatientContext (proves ingestion works) →
// optional agent run. No modality is presented as the eICU patient's own.
import { useCallback, useEffect, useRef, useState } from "react";
import { careguardApi } from "@/lib/careguardApi";
import { careguardCasesApi, type CaseListRow } from "@/lib/careguardCasesApi";
import type { PatientContext } from "@/types/careguard";

type Mode = "manual" | "pretested";

interface ImportResult {
  case_id: string;
  validation: Record<string, unknown>;
  missing_critical_evidence: string[];
}

export function CareGuardRunner() {
  const [mode, setMode] = useState<Mode>("pretested");
  const [bundleText, setBundleText] = useState("");
  const [question, setQuestion] = useState(
    "Review guideline-concordant therapy and flag missing critical evidence.",
  );
  const [cases, setCases] = useState<CaseListRow[]>([]);
  const [selectedCase, setSelectedCase] = useState<string>("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [imported, setImported] = useState<ImportResult | null>(null);
  const [ctx, setCtx] = useState<PatientContext | null>(null);
  const [agentLog, setAgentLog] = useState<string[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    careguardCasesApi
      .list()
      .then((r) => {
        setCases(r.cases);
        if (r.cases[0]) setSelectedCase(r.cases[0].case_id);
      })
      .catch((e) => setError(`Could not load cases: ${e}`));
  }, []);

  const onFile = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    f.text().then(setBundleText);
  }, []);

  const analyze = useCallback(async () => {
    setError(null);
    setImported(null);
    setCtx(null);
    setAgentLog([]);
    try {
      // 1. obtain the bundle
      setBusy("Preparing bundle…");
      let bundle: unknown;
      if (mode === "manual") {
        if (!bundleText.trim()) throw new Error("Paste or upload a FHIR bundle first.");
        bundle = JSON.parse(bundleText);
      } else {
        if (!selectedCase) throw new Error("Select a case first.");
        bundle = await careguardCasesApi.bundle(selectedCase);
      }
      // 2. import (deterministic — no LLM)
      setBusy("Importing + validating bundle…");
      const imp = await careguardApi.importBundle(bundle, question);
      setImported(imp);
      // 3. deterministic PatientContext (proves ingestion works without any agent)
      setBusy("Extracting patient context…");
      const c = await careguardApi.context(imp.case_id);
      setCtx(c.patient_context);
      setBusy(null);
    } catch (e) {
      setBusy(null);
      setError(String(e));
    }
  }, [mode, bundleText, selectedCase, question]);

  const runAgents = useCallback(async () => {
    if (!imported) return;
    setError(null);
    setAgentLog(["Creating run…"]);
    try {
      const { run } = await careguardApi.createRun(imported.case_id, "clinical_evidence_review");
      let terminal = false;
      let guard = 0;
      while (!terminal && guard++ < 12) {
        const step = await careguardApi.advance(run.run_id);
        setAgentLog((l) => [...l, `stage → ${step.run.current_stage ?? "?"}`]);
        terminal = Boolean(step.terminal);
      }
      setAgentLog((l) => [...l, "Run complete."]);
    } catch (e) {
      setAgentLog((l) => [...l, `Agent run unavailable: ${e}`,
        "(The deterministic import + PatientContext above already verify ingestion; the staged "
        + "agents need the CareGuard backend with an Anthropic key.)"]);
    }
  }, [imported]);

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "flex", gap: 8 }}>
        {(["pretested", "manual"] as Mode[]).map((m) => (
          <button key={m} onClick={() => setMode(m)} style={tab(mode === m)}>
            {m === "pretested" ? "Pre-tested case" : "Manual input"}
          </button>
        ))}
      </div>

      {mode === "pretested" ? (
        <div>
          <label style={lbl}>Select a packaged case ({cases.length} available)</label>
          <select value={selectedCase} onChange={(e) => setSelectedCase(e.target.value)} style={inp}>
            {cases.slice(0, 1000).map((c) => (
              <option key={c.case_id} value={c.case_id}>
                {c.case_id} · {c.gender ?? "?"} {c.age ?? "?"}y · {(c.cv_categories ?? "").split("|")[0]}
              </option>
            ))}
          </select>
        </div>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          <label style={lbl}>Paste a FHIR R4 bundle (or upload a .json file)</label>
          <textarea value={bundleText} onChange={(e) => setBundleText(e.target.value)}
            placeholder='{"resourceType":"Bundle","type":"collection","entry":[…]}'
            style={{ ...inp, minHeight: 160, fontFamily: "monospace", fontSize: 12 }} />
          <input ref={fileRef} type="file" accept="application/json,.json" onChange={onFile} />
        </div>
      )}

      <div>
        <label style={lbl}>Clinical question</label>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} style={inp} />
      </div>

      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <button onClick={analyze} disabled={!!busy} style={primary}>
          {busy ? busy : "Import & analyze"}
        </button>
        {imported && (
          <button onClick={runAgents} style={tab(false)}>Run full agent analysis →</button>
        )}
      </div>

      {error && <p style={{ color: "#991b1b" }}>⚠ {error}</p>}

      {imported && (
        <section style={card}>
          <h3 style={{ margin: "0 0 6px" }}>Ingestion result</h3>
          <p style={{ margin: 0, fontSize: 13 }}>
            case_id <code>{imported.case_id}</code> ·{" "}
            valid: <b>{String(imported.validation.valid ?? "—")}</b> ·{" "}
            resources: {String(imported.validation.total_entries ?? "—")}
          </p>
          {imported.missing_critical_evidence?.length > 0 && (
            <p style={{ margin: "6px 0 0", fontSize: 13, color: "#92400e" }}>
              Missing critical evidence: {imported.missing_critical_evidence.join(", ")}
            </p>
          )}
        </section>
      )}

      {ctx && (
        <section style={card}>
          <h3 style={{ margin: "0 0 6px" }}>Patient context (deterministic — verifies ingestion)</h3>
          <ul style={{ margin: 0, fontSize: 13, lineHeight: 1.6 }}>
            <li>Active cardiac problems: {(ctx.active_cardiac_problem ?? []).length}</li>
            <li>Active non-cardiac conditions: {(ctx.active_non_cardiac_conditions ?? []).length}</li>
            <li>Medications: {(ctx.medications ?? []).length}</li>
            <li>Observations: {(ctx.observations ?? []).length}</li>
            <li>Data-quality score: {String(ctx.data_quality_score ?? "—")}</li>
            <li>Provenance coverage: {String(ctx.provenance_coverage ?? "—")}</li>
            {(ctx.missing_critical_evidence ?? []).length > 0 && (
              <li style={{ color: "#92400e" }}>
                Missing: {(ctx.missing_critical_evidence ?? []).join(", ")}
              </li>
            )}
          </ul>
        </section>
      )}

      {agentLog.length > 0 && (
        <section style={card}>
          <h3 style={{ margin: "0 0 6px" }}>Agent run</h3>
          <pre style={{ margin: 0, fontSize: 12, whiteSpace: "pre-wrap" }}>{agentLog.join("\n")}</pre>
        </section>
      )}
    </div>
  );
}

const inp: React.CSSProperties = {
  width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid #cbd5e1", boxSizing: "border-box",
};
const lbl: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 600, marginBottom: 4, color: "#334155" };
const card: React.CSSProperties = { border: "1px solid #e5e7eb", borderRadius: 10, padding: 14 };
const primary: React.CSSProperties = {
  padding: "8px 16px", borderRadius: 8, border: "none", background: "#7c3aed", color: "white",
  fontWeight: 600, cursor: "pointer",
};
const tab = (active: boolean): React.CSSProperties => ({
  padding: "6px 14px", borderRadius: 8, border: "1px solid #cbd5e1", cursor: "pointer",
  background: active ? "#ede9fe" : "white", fontWeight: active ? 700 : 500,
});

export default CareGuardRunner;
