"use client";

import { useState } from "react";
import { careguardApi } from "@/lib/careguardApi";

/*
 * The lower-right CareGuard analysis agent. A floating button opens a chat panel
 * that answers ANALYSIS questions grounded in the current case's CareGuard
 * artifacts (conflicts, evidence, alternatives, critic). It never diagnoses,
 * doses, or prescribes.
 */
type Turn = { q: string; a: string; via: string; grounded: string[] };

export function CareGuardCopilot({ caseId }: { caseId: string }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);

  const ask = async (question: string) => {
    const query = question.trim();
    if (!query || !caseId) return;
    setBusy(true);
    try {
      const res = await careguardApi.copilot(caseId, query);
      setTurns((t) => [
        ...t,
        { q: query, a: res.copilot.answer, via: res.copilot.used_anthropic ? "Claude" : "deterministic", grounded: res.copilot.grounded_on },
      ]);
      setQ("");
    } catch (e) {
      setTurns((t) => [...t, { q: query, a: `Error: ${(e as Error).message}`, via: "error", grounded: [] }]);
    } finally {
      setBusy(false);
    }
  };

  const suggestions = ["Why was it flagged?", "What alternative and why?", "What is missing?", "Explain the critic verdict"];

  return (
    <>
      <button
        aria-label="Open CareGuard analysis copilot"
        onClick={() => setOpen((o) => !o)}
        style={fab}
      >
        {open ? "×" : "Ask ✦"}
      </button>

      {open && (
        <section style={panel} role="dialog" aria-label="CareGuard copilot">
          <header style={panelHead}>
            <span>CareGuard analysis copilot</span>
            <span style={{ fontSize: 10, color: "#94a3b8" }}>{caseId ? `case ${caseId.slice(0, 10)}` : "no case"}</span>
          </header>

          <div style={thread}>
            {turns.length === 0 && (
              <div style={{ fontSize: 12, color: "#64748b" }}>
                Ask an analysis question about this case. Grounded in the loaded evidence — no diagnosis or dosing.
              </div>
            )}
            {turns.map((t, i) => (
              <div key={i} style={{ marginBottom: 10 }}>
                <div style={qBubble}>{t.q}</div>
                <div style={aBubble}>
                  <div style={{ whiteSpace: "pre-wrap" }}>{t.a}</div>
                  <div style={{ fontSize: 10, color: "#94a3b8", marginTop: 4 }}>
                    via {t.via}{t.grounded.length ? ` · grounded on ${t.grounded.join(", ")}` : ""}
                  </div>
                </div>
              </div>
            ))}
            {busy && <div style={{ fontSize: 12, color: "#0f766e" }}>analyzing…</div>}
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, padding: "0 10px 6px" }}>
            {suggestions.map((s) => (
              <button key={s} onClick={() => ask(s)} disabled={busy} style={chip}>{s}</button>
            ))}
          </div>

          <form
            onSubmit={(e) => { e.preventDefault(); ask(q); }}
            style={{ display: "flex", gap: 6, padding: 10, borderTop: "1px solid #e2e8f0" }}
          >
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask about this case…"
              style={{ flex: 1, padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: 6, fontSize: 13 }} />
            <button type="submit" disabled={busy} style={sendBtn}>Send</button>
          </form>
        </section>
      )}
    </>
  );
}

const fab: React.CSSProperties = { position: "fixed", right: 20, bottom: 20, zIndex: 50, padding: "12px 16px", borderRadius: 999, background: "#0f766e", color: "#fff", border: "none", fontWeight: 700, cursor: "pointer", boxShadow: "0 6px 20px rgba(15,118,110,0.4)" };
const panel: React.CSSProperties = { position: "fixed", right: 20, bottom: 74, zIndex: 50, width: 360, maxWidth: "92vw", height: 460, maxHeight: "70vh", background: "#fff", border: "1px solid #cbd5e1", borderRadius: 12, display: "flex", flexDirection: "column", boxShadow: "0 12px 40px rgba(0,0,0,0.18)" };
const panelHead: React.CSSProperties = { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 12px", borderBottom: "1px solid #e2e8f0", fontWeight: 700, fontSize: 13 };
const thread: React.CSSProperties = { flex: 1, overflowY: "auto", padding: 12 };
const qBubble: React.CSSProperties = { background: "#0f766e", color: "#fff", padding: "6px 10px", borderRadius: 10, fontSize: 12, marginLeft: "auto", maxWidth: "85%", width: "fit-content" };
const aBubble: React.CSSProperties = { background: "#f1f5f9", color: "#0f172a", padding: "8px 10px", borderRadius: 10, fontSize: 12, marginTop: 4 };
const chip: React.CSSProperties = { padding: "3px 8px", borderRadius: 999, border: "1px solid #cbd5e1", background: "#fff", fontSize: 11, cursor: "pointer" };
const sendBtn: React.CSSProperties = { padding: "8px 12px", background: "#0f766e", color: "#fff", border: "none", borderRadius: 6, fontWeight: 600, cursor: "pointer", fontSize: 13 };
