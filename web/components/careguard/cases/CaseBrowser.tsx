"use client";

// Browse all packaged cases, filter, and select one to demo. Left = list, right =
// composite demo (EHR + ECG + echo + linkage). Additive; does not touch other views.
import { useEffect, useMemo, useState } from "react";
import { careguardCasesApi, type CaseListRow } from "@/lib/careguardCasesApi";
import CaseDetail from "./CaseDetail";

export function CaseBrowser() {
  const [rows, setRows] = useState<CaseListRow[]>([]);
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    careguardCasesApi
      .list()
      .then((r) => {
        setRows(r.cases);
        if (r.cases[0]) setSelected(r.cases[0].case_id);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter(
      (r) =>
        r.case_id.includes(needle) ||
        (r.cv_categories ?? "").toLowerCase().includes(needle) ||
        (r.gender ?? "").toLowerCase().includes(needle) ||
        (r.ecg_superclass ?? "").toLowerCase().includes(needle),
    );
  }, [rows, q]);

  if (err) return <p style={{ color: "#991b1b" }}>Failed to load cases: {err}</p>;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 18, alignItems: "start" }}>
      <aside style={{ border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
        <div style={{ padding: 10, borderBottom: "1px solid #eee" }}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={`Search ${rows.length} cases (id, CV, sex, ECG)…`}
            style={{ width: "100%", padding: "6px 10px", borderRadius: 8, border: "1px solid #cbd5e1" }}
          />
        </div>
        <div style={{ maxHeight: "70vh", overflowY: "auto" }}>
          {filtered.slice(0, 400).map((r) => (
            <button
              key={r.case_id}
              onClick={() => setSelected(r.case_id)}
              style={{
                display: "block", width: "100%", textAlign: "left", padding: "8px 12px",
                border: "none", borderBottom: "1px solid #f1f5f9", cursor: "pointer",
                background: selected === r.case_id ? "#ede9fe" : "white",
              }}
            >
              <div style={{ fontWeight: 600, fontSize: 13 }}>{r.case_id}</div>
              <div style={{ fontSize: 11, color: "#64748b" }}>
                {r.gender ?? "?"} · {r.age ?? "?"}y · {(r.cv_categories ?? "").split("|")[0] || "cv"} ·{" "}
                {r.n_noncardiac_organs ?? 0} organs · EF/ECG {r.ecg_superclass ?? "—"}
              </div>
            </button>
          ))}
          {filtered.length > 400 && (
            <p style={{ fontSize: 11, color: "#94a3b8", padding: 8 }}>
              Showing first 400 of {filtered.length}. Refine the search.
            </p>
          )}
        </div>
      </aside>

      <main style={{ minWidth: 0 }}>
        {selected ? <CaseDetail caseId={selected} /> : <p>Select a case.</p>}
      </main>
    </div>
  );
}

export default CaseBrowser;
