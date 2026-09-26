"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { careguardApi, CAREGUARD_ENABLED } from "@/lib/careguardApi";
import { careguardCasesApi, type CaseListRow } from "@/lib/careguardCasesApi";
import { CareGuardCopilot } from "@/components/careguard/CareGuardCopilot";
import { useDualBeatStore } from "@/lib/store";
import type {
  AlternativeCandidate,
  CareGuardRun,
  EvidenceCitation,
  MedicationSafety,
  PatientContext,
} from "@/types/careguard";

const DISCLAIMER = "Clinical decision support draft. Clinician and pharmacist review required.";
const STAGES = [
  "encounter_intake", "fhir_context", "multimorbidity_analysis", "guideline_evidence",
  "medication_safety", "candidate_composition", "hearttwin_scenarios", "clinical_critic",
  "clinician_review_ready",
];

type Loaded = {
  context?: PatientContext;
  citations?: EvidenceCitation[];
  medication?: MedicationSafety;
  candidates?: Record<string, unknown>[];
  critic?: Record<string, unknown>;
  simulation?: Record<string, unknown>;
  audit?: Record<string, unknown>[];
};

const SEV_COLOR: Record<string, string> = {
  blocked_for_draft: "#b91c1c", high_concern: "#c2410c", caution: "#a16207",
  informational: "#334155", insufficient_evidence: "#64748b",
};

export function CareGuardConsole({ embedded = false }: { embedded?: boolean } = {}) {
  // When embedded as a tab, the case is whatever the main panel selected.
  const storeCaseRef = useDualBeatStore((s) => s.caseId);
  const [caseId, setCaseId] = useState<string>("");
  const [run, setRun] = useState<CareGuardRun | null>(null);
  const [loaded, setLoaded] = useState<Loaded>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>("");
  const [question, setQuestion] = useState("HFrEF review with CKD stage 3b — check contraindications and missing labs");
  const [decision, setDecision] = useState<string>("");
  const [docReport, setDocReport] = useState("");
  const [progress, setProgress] = useState("");
  const [careEval, setCareEval] = useState<Record<string, unknown> | null>(null);
  const [evalBusy, setEvalBusy] = useState(false);

  // Case source: pick a real packaged case (of the 1,000) OR upload a FHIR bundle.
  const [cases, setCases] = useState<CaseListRow[]>([]);
  const [selectedCase, setSelectedCase] = useState<string>("");
  const [caseFilter, setCaseFilter] = useState<string>("");
  const [uploadBundle, setUploadBundle] = useState<unknown | null>(null);
  const [uploadName, setUploadName] = useState<string>("");
  const [runningStage, setRunningStage] = useState<string>("");
  const [ingestion, setIngestion] = useState<{
    file_count: number; files_analyzed: string[]; modalities_analyzed: string[];
    labs_summary: Record<string, unknown>; ehr_counts: Record<string, number>;
    ecg: Record<string, unknown>; analysis_profiles: string[];
  } | null>(null);

  useEffect(() => {
    let alive = true;
    careguardCasesApi
      .list()
      .then((r) => {
        if (!alive) return;
        setCases(r.cases);
        if (r.cases[0]) setSelectedCase(r.cases[0].case_id);
      })
      .catch((e) => setError(`Could not load cases: ${(e as Error).message}`));
    return () => {
      alive = false;
    };
  }, []);

  const filteredCases = useMemo(() => {
    const q = caseFilter.trim().toLowerCase();
    const rows = q
      ? cases.filter(
          (c) =>
            c.case_id.toLowerCase().includes(q) ||
            (c.cv_categories ?? "").toLowerCase().includes(q) ||
            (c.ecg_superclass ?? "").toLowerCase().includes(q),
        )
      : cases;
    return rows.slice(0, 200);
  }, [cases, caseFilter]);

  const onUpload = useCallback((file: File | undefined) => {
    if (!file) return;
    file
      .text()
      .then((text) => {
        const parsed = JSON.parse(text);
        setUploadBundle(parsed);
        setUploadName(file.name);
        setSelectedCase("");
        setError("");
      })
      .catch(() => setError(`Could not parse ${file.name} as a FHIR JSON bundle`));
  }, []);

  const clearUpload = useCallback(() => {
    setUploadBundle(null);
    setUploadName("");
    if (cases[0]) setSelectedCase(cases[0].case_id);
  }, [cases]);

  const runCareEval = useCallback(async () => {
    if (!caseId) return;
    setEvalBusy(true);
    try {
      const res = await careguardApi.careEvaluation(caseId, docReport, progress);
      setCareEval(res.care_evaluation);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setEvalBusy(false);
    }
  }, [caseId, docReport, progress]);

  const refresh = useCallback(async (cid: string) => {
    const [ctx, ev, med, cand, crit, sim, aud] = await Promise.allSettled([
      careguardApi.context(cid), careguardApi.evidence(cid), careguardApi.medicationSafety(cid),
      careguardApi.candidates(cid), careguardApi.critic(cid), careguardApi.simulation(cid),
      careguardApi.audit(cid),
    ]);
    setLoaded({
      context: ctx.status === "fulfilled" ? ctx.value.patient_context : undefined,
      citations: ev.status === "fulfilled" ? ev.value.citations : undefined,
      medication: med.status === "fulfilled" ? med.value.medication_safety : undefined,
      candidates: cand.status === "fulfilled" ? cand.value.candidates : undefined,
      critic: crit.status === "fulfilled" ? crit.value.critic : undefined,
      simulation: sim.status === "fulfilled" ? sim.value.simulation : undefined,
      audit: aud.status === "fulfilled" ? aud.value.audit : undefined,
    });
  }, []);

  const activeSelectedCase = embedded && storeCaseRef ? storeCaseRef : selectedCase;
  const runAll = useCallback(async () => {
    if (!uploadBundle && !activeSelectedCase) {
      setError("Select a patient case or upload a FHIR bundle first.");
      return;
    }
    setBusy(true); setError(""); setLoaded({}); setRun(null); setCaseId(""); setDecision(""); setRunningStage(""); setIngestion(null);
    try {
      // Analyze the REAL selected case across ALL its files (FHIR + report +
      // med-evidence + ECG + EHR + analysis), or an uploaded bundle.
      let impCaseId: string;
      if (uploadBundle) {
        const imp = await careguardApi.importBundle(uploadBundle, question);
        impCaseId = imp.case_id;
      } else {
        const pkg = await careguardApi.loadPackaged(activeSelectedCase, question);
        impCaseId = pkg.case_id;
        setIngestion(pkg.ingestion);
      }
      setCaseId(impCaseId);
      const created = await careguardApi.createRun(impCaseId);
      let r = created.run;
      setRun(r);
      // Drive the staged pipeline one bounded stage per call — the pill row
      // updates live as each of the 8 agents completes.
      for (let i = 0; i < 12; i++) {
        setRunningStage(r.next_stage ?? "");
        const out = await careguardApi.advance(r.run_id);
        r = out.run; setRun({ ...r });
        if (out.terminal || !r.next_stage || r.status === "completed") break;
      }
      setRunningStage("");
      await refresh(impCaseId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      setRunningStage("");
    }
  }, [activeSelectedCase, uploadBundle, question, refresh]);

  const sendDecision = useCallback(async (d: string) => {
    if (!caseId) return;
    const reason = d === "override" ? "clinician override — accepts documented risk" : "";
    await careguardApi.feedback(caseId, d, reason);
    setDecision(d);
    await refresh(caseId);
  }, [caseId, refresh]);

  // Embedded tab: adopt the case picked in the main panel + auto-run once, so
  // CareGuard analyzes the SAME case with no separate selection.
  const autoRunRef = useRef<string>("");
  useEffect(() => {
    if (embedded && storeCaseRef && activeSelectedCase === storeCaseRef && autoRunRef.current !== storeCaseRef && !busy) {
      autoRunRef.current = storeCaseRef;
      runAll();
    }
  }, [embedded, storeCaseRef, activeSelectedCase, busy, runAll]);

  if (!CAREGUARD_ENABLED) {
    return (
      <div style={wrap}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>BeatIT CareGuard</h1>
        <p style={{ color: "#64748b" }}>
          CareGuard is disabled. Set <code>NEXT_PUBLIC_CAREGUARD_ENABLED=true</code> (and{" "}
          <code>CAREGUARD_ENABLED=true</code> on the API) to enable this module.
        </p>
      </div>
    );
  }

  const med = loaded.medication;
  const critic = loaded.critic as { safe_to_display?: boolean; blocked_reasons?: string[]; scorecard?: Record<string, number> } | undefined;

  return (
    <div style={wrap}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>BeatIT CareGuard</h1>
          <p style={{ color: "#64748b", margin: "2px 0 0", fontSize: 13 }}>
            Multimorbidity medication-safety & evidence review — task workflow
          </p>
        </div>
        <span style={banner}>{DISCLAIMER}</span>
      </header>

      <section style={card}>
        {embedded ? (
          <>
            <h2 style={h2}>CareGuard review{activeSelectedCase ? ` · ${activeSelectedCase}` : ""}</h2>
            <p style={sub}>Analyzing the case selected in the main panel — runs automatically, drafts appear below. No separate selection needed.</p>
          </>
        ) : (
          <>
            <h2 style={h2}>Patient case</h2>
            <p style={sub}>Pick one of the {cases.length || "…"} real packaged cases, or upload a FHIR R4 bundle. The console analyzes that exact case.</p>
          </>
        )}

        {!embedded && (uploadBundle ? (
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 8 }}>
            <span style={{ ...tag, background: "#dcfce7", color: "#166534", marginLeft: 0 }}>Uploaded: {uploadName}</span>
            <button onClick={clearUpload} style={{ ...secondaryBtn, padding: "4px 10px" }}>Use a packaged case instead</button>
          </div>
        ) : (
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 8 }}>
            <input
              value={caseFilter}
              onChange={(e) => setCaseFilter(e.target.value)}
              placeholder="Filter by case id / cv category / ECG class…"
              style={{ ...input, minWidth: 220 }}
              aria-label="Filter cases"
            />
            <select
              value={selectedCase}
              onChange={(e) => setSelectedCase(e.target.value)}
              style={{ ...input, minWidth: 320 }}
              aria-label="Select a patient case"
            >
              {filteredCases.length === 0 && <option value="">No matching case</option>}
              {filteredCases.map((c) => (
                <option key={c.case_id} value={c.case_id}>
                  {c.case_id} · {c.gender ?? "?"} {c.age ?? "?"}y · {(c.cv_categories ?? "").split("|").slice(0, 2).join(", ") || "—"}
                </option>
              ))}
            </select>
            <label style={{ ...secondaryBtn, display: "inline-flex", alignItems: "center", gap: 6 }}>
              Upload FHIR…
              <input
                type="file"
                accept="application/json,.json"
                onChange={(e) => onUpload(e.target.files?.[0])}
                style={{ display: "none" }}
              />
            </label>
          </div>
        ))}

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          {!embedded && <input value={question} onChange={(e) => setQuestion(e.target.value)} style={input} aria-label="Clinical question" placeholder="Clinical question" />}
          <button onClick={runAll} disabled={busy || (!activeSelectedCase && !uploadBundle)} style={primaryBtn}>
            {busy ? (runningStage ? `Running ${runningStage.replace(/_/g, " ")}…` : "Running…")
              : embedded ? "Re-run CareGuard review" : "Run review on this case"}
          </button>
          {embedded && !activeSelectedCase && (
            <span style={{ ...sub, margin: 0 }}>Select a case in the main panel to begin.</span>
          )}
        </div>
      </section>
      {error && <div style={{ color: "#b91c1c", fontSize: 13 }}>Error: {error}</div>}

      {ingestion && (
        <section style={card}>
          <h2 style={h2}>Multimodal ingestion · {ingestion.file_count} files · {ingestion.modalities_analyzed.length} modalities</h2>
          <p style={sub}>Every file in this case was analyzed — {ingestion.modalities_analyzed.join(", ")}.</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
            {ingestion.modalities_analyzed.map((m) => <span key={m} style={{ ...tag, marginLeft: 0 }}>{m}</span>)}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 16, fontSize: 12 }}>
            {Object.keys(ingestion.labs_summary || {}).length > 0 && (
              <div><strong>Labs:</strong> {Object.entries(ingestion.labs_summary).map(([k, v]) => `${k} ${v}`).join(", ")}</div>
            )}
            {ingestion.ecg?.available ? <div><strong>ECG:</strong> present (heartbeat context)</div> : null}
            {ingestion.analysis_profiles?.length ? <div><strong>Profiles:</strong> {ingestion.analysis_profiles.join(", ")}</div> : null}
          </div>
          <details style={{ marginTop: 6 }}>
            <summary style={{ fontSize: 11, color: "var(--ht-muted)", cursor: "pointer" }}>files analyzed</summary>
            <ul style={{ ...ul, fontSize: 11, color: "var(--ht-muted)" }}>{ingestion.files_analyzed.map((f) => <li key={f}>{f}</li>)}</ul>
          </details>
        </section>
      )}

      {run && (
        <section style={card}>
          <h2 style={h2}>Pipeline · {run.status}{runningStage ? ` · running ${runningStage.replace(/_/g, " ")}…` : ""}</h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {STAGES.map((s) => {
              const done = run.completed_stages.includes(s);
              const sr = run.stage_results.find((x) => x.stage_id === s);
              return (
                <span key={s} title={sr?.warnings.join("; ")} style={{
                  ...pill,
                  background: done ? (sr?.status === "blocked" ? "#fee2e2" : "#dcfce7") : "#f1f5f9",
                  color: done ? (sr?.status === "blocked" ? "#991b1b" : "#166534") : "#94a3b8",
                }}>
                  {s.replace(/_/g, " ")}{sr ? ` · ${sr.status}` : ""}
                </span>
              );
            })}
          </div>
        </section>
      )}

      {loaded.context && (
        <section style={card}>
          <h2 style={h2}>Reconciled patient context</h2>
          <p style={sub}>Every fact links to its FHIR JSON pointer. Provenance coverage {Math.round((loaded.context.provenance_coverage ?? 0) * 100)}%.</p>
          <FactList title="Active cardiac problem" facts={loaded.context.active_cardiac_problem} />
          <FactList title="Comorbidities" facts={loaded.context.active_non_cardiac_conditions} />
          <FactList title="Medications" facts={loaded.context.medications} />
          <FactList title="Allergies" facts={loaded.context.allergies} />
          {loaded.context.missing_critical_evidence.length > 0 && (
            <div style={warnBox}>
              <strong>Missing critical evidence</strong>
              <ul style={ul}>{loaded.context.missing_critical_evidence.map((m, i) => <li key={i}>{m}</li>)}</ul>
            </div>
          )}
        </section>
      )}

      {loaded.citations && loaded.citations.length > 0 && (
        <section style={card}>
          <h2 style={h2}>Guideline evidence</h2>
          {loaded.citations.map((c) => (
            <div key={c.source_id} style={evBox}>
              <div style={{ fontWeight: 700 }}>
                {c.organization} {c.version} · {c.section}
                {c.recommendation_class && <span style={tag}>Class {c.recommendation_class}/{c.evidence_level}</span>}
                {c.synthetic_excerpt && <span style={{ ...tag, background: "#fef9c3", color: "#854d0e" }}>synthetic excerpt</span>}
              </div>
              <p style={{ fontSize: 13, margin: "4px 0", color: "#334155" }}>{c.passage}</p>
              <div style={{ fontSize: 11, color: "#94a3b8" }}>sha256 {c.sha256?.slice(0, 16)}… · {c.canonical_source}</div>
            </div>
          ))}
        </section>
      )}

      {med && (
        <section style={card}>
          <h2 style={h2}>Medication safety · <span style={{ color: SEV_COLOR[med.overall_status] ?? "#334155" }}>{med.overall_status.replace(/_/g, " ")}</span></h2>
          <p style={sub}>Reconciliation score {Math.round((med.medication_reconciliation_score ?? 0) * 100)}%. {med.reconciled_active_medications.map((m) => m.original_text).join(", ")}</p>

          {med.report_mentions_requiring_confirmation.length > 0 && (
            <div style={warnBox}>
              <strong>Report-mentioned conditions — clinician confirmation required</strong>
              <ul style={ul}>
                {med.report_mentions_requiring_confirmation.map((m) => (
                  <li key={m.mention_id}>{m.normalized_display} <span style={{ color: "#94a3b8" }}>({m.status}, {m.temporality})</span></li>
                ))}
              </ul>
            </div>
          )}

          <h3 style={h3}>Conflict matrix</h3>
          <div style={{ overflowX: "auto" }}>
            <table style={table}>
              <thead><tr>{["Severity", "Type", "Finding", "Evidence", "Missing"].map((h) => <th key={h} style={th}>{h}</th>)}</tr></thead>
              <tbody>
                {med.conflicts.map((c) => (
                  <tr key={c.conflict_id}>
                    <td style={td}><span style={{ color: SEV_COLOR[c.severity], fontWeight: 700 }}>{c.severity.replace(/_/g, " ")}</span></td>
                    <td style={td}>{c.conflict_type.replace(/_/g, " ")}</td>
                    <td style={td}>{c.headline}</td>
                    <td style={td}>{c.authoritative_evidence.map((e, i) => <div key={i} style={{ fontSize: 11 }}>{e.source_title} <span style={{ color: "#94a3b8" }}>[{e.authority_tier}]</span></div>)}
                      {c.supplemental_evidence.map((e, i) => <div key={`s${i}`} style={{ fontSize: 11, color: "#94a3b8" }}>{e.source_title} (supp.)</div>)}</td>
                    <td style={td}>{c.missing_information.join("; ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 style={h3}>Candidate alternatives — clinician & pharmacist review required</h3>
          {med.alternative_candidates.map((a) => <AltCard key={a.candidate_id} a={a} />)}
          {med.alternative_candidates.filter((a) => a.display_status === "candidate_for_clinician_review").length === 0 && (
            <p style={{ color: "#64748b", fontSize: 13 }}>
              No adequately supported lower-conflict candidate was identified from the configured evidence sources.
              Additional clinician or pharmacist review is required.
            </p>
          )}
        </section>
      )}

      {loaded.candidates && loaded.candidates.length > 0 && (
        <section style={card}>
          <h2 style={h2}>Care-plan options</h2>
          {loaded.candidates.map((c) => {
            const cd = c as { candidate_id: string; title: string; reasons_for: string[]; reasons_against: string[]; missing_information: string[] };
            return (
              <div key={cd.candidate_id} style={evBox}>
                <div style={{ fontWeight: 700 }}>{cd.title}</div>
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 12, marginTop: 4 }}>
                  <div><span style={{ color: "#166534" }}>For:</span> {cd.reasons_for.join("; ")}</div>
                  <div><span style={{ color: "#991b1b" }}>Against:</span> {cd.reasons_against.join("; ")}</div>
                </div>
                {cd.missing_information.length > 0 && <div style={{ fontSize: 12, color: "#a16207" }}>Missing: {cd.missing_information.join("; ")}</div>}
              </div>
            );
          })}
        </section>
      )}

      {loaded.simulation && (loaded.simulation as { ok?: boolean }).ok && (
        <section style={card}>
          <h2 style={h2}>BeatIT scenario comparison</h2>
          <p style={sub}>Simulated physiologic scenario for comparison only. Not an outcome prediction.</p>
          <SimTable sim={loaded.simulation} />
        </section>
      )}

      {critic && (
        <section style={{ ...card, borderColor: critic.safe_to_display ? "#cbd5e1" : "#fca5a5" }}>
          <h2 style={h2}>Clinical critic</h2>
          <p style={{ fontWeight: 700, color: critic.safe_to_display ? "#166534" : "#b91c1c" }}>
            {critic.safe_to_display ? "Draft cleared for clinician review" : "Display blocked pending revision"}
          </p>
          {(critic.blocked_reasons ?? []).length > 0 && (
            <ul style={ul}>{(critic.blocked_reasons ?? []).map((r, i) => <li key={i} style={{ color: "#b91c1c" }}>{r}</li>)}</ul>
          )}
          {critic.scorecard && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
              {Object.entries(critic.scorecard).map(([k, v]) => (
                <span key={k} style={scorePill}>{k.replace(/_/g, " ")}: {Math.round((v as number) * 100)}%</span>
              ))}
            </div>
          )}
        </section>
      )}

      {caseId && (
        <section style={card}>
          <h2 style={h2}>Clinician decision</h2>
          <p style={sub}>CareGuard does not choose treatment. The clinician remains the decision-maker.</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {["accept_for_draft", "reject", "request_more_information", "override"].map((d) => (
              <button key={d} onClick={() => sendDecision(d)} style={{ ...secondaryBtn, borderColor: decision === d ? "#0f766e" : "#cbd5e1" }}>
                {d.replace(/_/g, " ")}
              </button>
            ))}
          </div>
          {decision && <p style={{ fontSize: 13, color: "#0f766e", marginTop: 6 }}>Recorded: {decision.replace(/_/g, " ")} (audited)</p>}
        </section>
      )}

      {caseId && (
        <section style={card}>
          <h2 style={h2}>Care-process evaluation harness</h2>
          <p style={sub}>Paste what the doctor did + the patient-progress note. The agent analyzes how the process aligned with CareGuard&apos;s evidence — quality support, not a verdict.</p>
          <textarea value={docReport} onChange={(e) => setDocReport(e.target.value)} placeholder="Doctor's report — what was done for this case…"
            style={{ ...input, width: "100%", minHeight: 60, display: "block", marginBottom: 6 }} />
          <textarea value={progress} onChange={(e) => setProgress(e.target.value)} placeholder="Patient progress report…"
            style={{ ...input, width: "100%", minHeight: 44, display: "block", marginBottom: 6 }} />
          <button onClick={runCareEval} disabled={evalBusy} style={primaryBtn}>{evalBusy ? "Analyzing…" : "Evaluate care process"}</button>
          {careEval && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontWeight: 700 }}>
                Overall process alignment: {Math.round(((careEval.overall_process_quality as number) ?? 0) * 100)}%
                {careEval.model_used ? <span style={tag}>via {String(careEval.model_used)}</span> : null}
              </div>
              <div style={{ overflowX: "auto", marginTop: 6 }}>
                <table style={table}>
                  <thead><tr>{["Dimension", "Score", "Addressed", "Not addressed"].map((h) => <th key={h} style={th}>{h}</th>)}</tr></thead>
                  <tbody>
                    {((careEval.dimensions as { name: string; score: number; addressed: string[]; not_addressed: string[] }[]) ?? []).map((d) => (
                      <tr key={d.name}>
                        <td style={td}>{d.name.replace(/_/g, " ")}</td>
                        <td style={{ ...td, color: d.score >= 0.5 ? "#166534" : "#b91c1c", fontWeight: 700 }}>{Math.round(d.score * 100)}%</td>
                        <td style={td}>{d.addressed.join("; ")}</td>
                        <td style={{ ...td, color: "#a16207" }}>{d.not_addressed.join("; ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p style={{ fontSize: 13, marginTop: 8, whiteSpace: "pre-wrap" }}>{String(careEval.narrative ?? "")}</p>
            </div>
          )}
        </section>
      )}

      {loaded.audit && (
        <section style={card}>
          <h2 style={h2}>Audit trail · {loaded.audit.length} events</h2>
          <ul style={{ ...ul, maxHeight: 160, overflowY: "auto" }}>
            {loaded.audit.map((e, i) => {
              const ev = e as { actor: string; action: string };
              return <li key={i} style={{ fontSize: 12 }}><span style={{ color: "#94a3b8" }}>{ev.actor}</span> — {ev.action}</li>;
            })}
          </ul>
        </section>
      )}

      {/* Lower-right analysis agent — always available once a case is loaded. */}
      <CareGuardCopilot caseId={caseId} />
    </div>
  );
}

function FactList({ title, facts }: { title: string; facts: { fact_id: string; display?: string | null; value?: unknown; unit?: string | null; json_pointer: string }[] }) {
  if (!facts || facts.length === 0) return null;
  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{title}</div>
      <ul style={ul}>
        {facts.map((f) => (
          <li key={f.fact_id} title={`FHIR source: ${f.json_pointer}`} style={{ fontSize: 13 }}>
            {f.display ?? String(f.value)}{f.unit ? ` ${f.unit}` : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}

function AltCard({ a }: { a: AlternativeCandidate }) {
  const label: Record<string, string> = {
    candidate_for_clinician_review: "Lower documented conflict burden",
    requires_more_information: "Requires more information",
    excluded_due_to_conflict: "Excluded due to documented conflict",
    insufficient_evidence: "Insufficient evidence",
  };
  const color: Record<string, string> = {
    candidate_for_clinician_review: "#0f766e", requires_more_information: "#a16207",
    excluded_due_to_conflict: "#b91c1c", insufficient_evidence: "#64748b",
  };
  return (
    <div style={{ ...evBox, borderLeft: `3px solid ${color[a.display_status]}` }}>
      <div style={{ fontWeight: 700 }}>
        {a.medication_identity.original_text}
        <span style={{ ...tag, background: "#f1f5f9", color: "#475569" }}>{a.alternative_type.replace(/_/g, " ")}</span>
        <span style={{ ...tag, background: "transparent", color: color[a.display_status], border: `1px solid ${color[a.display_status]}` }}>
          {label[a.display_status]}
        </span>
      </div>
      <div style={{ fontSize: 12, color: "#334155", marginTop: 4 }}>{a.reasons_considered.join("; ")}</div>
      {a.unresolved_questions.length > 0 && <div style={{ fontSize: 12, color: "#a16207" }}>Unresolved: {a.unresolved_questions.join("; ")}</div>}
      {a.guideline_evidence.length > 0 && (
        <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
          Guideline: {a.guideline_evidence.map((e) => e.source_title).join(", ")}
        </div>
      )}
    </div>
  );
}

function SimTable({ sim }: { sim: Record<string, unknown> }) {
  const scenarios = (sim.scenarios as { lever: string; directional_delta_vs_baseline: Record<string, number> }[]) ?? [];
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={table}>
        <thead><tr>{["Scenario", "EF Δ", "CO Δ", "MAP Δ"].map((h) => <th key={h} style={th}>{h}</th>)}</tr></thead>
        <tbody>
          {scenarios.map((s) => (
            <tr key={s.lever}>
              <td style={td}>{s.lever.replace(/_/g, " ")}</td>
              <td style={td}>{s.directional_delta_vs_baseline.ejection_fraction_pct}</td>
              <td style={td}>{s.directional_delta_vs_baseline.cardiac_output_l_min}</td>
              <td style={td}>{s.directional_delta_vs_baseline.mean_arterial_pressure_mmhg}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- styles: DualBeat theme tokens (accent = red/maroon, sharp corners) ----
const wrap: React.CSSProperties = { maxWidth: 1040, margin: "0 auto", padding: 24, display: "flex", flexDirection: "column", gap: 14, fontFamily: "ui-sans-serif, system-ui, sans-serif", color: "var(--ht-ink)" };
const card: React.CSSProperties = { border: "2px solid var(--ht-line-strong)", borderRadius: 4, padding: 16, background: "var(--ht-surface-1)" };
const banner: React.CSSProperties = { background: "var(--ht-warn-soft)", color: "var(--ht-warn)", padding: "6px 10px", borderRadius: 3, fontSize: 12, fontWeight: 600, border: "1px solid var(--ht-warn-line)" };
const h2: React.CSSProperties = { fontSize: 15, fontWeight: 700, margin: "0 0 8px", color: "var(--ht-ink)" };
const h3: React.CSSProperties = { fontSize: 13, fontWeight: 700, margin: "12px 0 6px", color: "var(--ht-ink-2)" };
const sub: React.CSSProperties = { fontSize: 12, color: "var(--ht-muted)", margin: "0 0 8px" };
const input: React.CSSProperties = { flex: 1, minWidth: 260, padding: "8px 10px", border: "1px solid var(--ht-line-strong)", borderRadius: 3, fontSize: 13, background: "var(--ht-surface-1)", color: "var(--ht-ink)" };
const primaryBtn: React.CSSProperties = { padding: "8px 14px", background: "var(--ht-accent)", color: "var(--ht-accent-ink)", border: "none", borderRadius: 3, fontWeight: 700, cursor: "pointer" };
const secondaryBtn: React.CSSProperties = { padding: "8px 12px", background: "var(--ht-surface-1)", color: "var(--ht-ink)", border: "1px solid var(--ht-line-strong)", borderRadius: 3, cursor: "pointer", fontSize: 13 };
const pill: React.CSSProperties = { padding: "3px 8px", borderRadius: 999, fontSize: 11, fontWeight: 600 };
const tag: React.CSSProperties = { marginLeft: 8, padding: "1px 6px", borderRadius: 3, fontSize: 10, background: "var(--ht-signal-soft)", color: "var(--ht-signal)", fontWeight: 600, border: "1px solid var(--ht-signal-line)" };
const scorePill: React.CSSProperties = { padding: "2px 8px", borderRadius: 999, fontSize: 11, background: "var(--ht-surface-3)", color: "var(--ht-ink-2)" };
const warnBox: React.CSSProperties = { background: "var(--ht-warn-soft)", border: "1px solid var(--ht-warn-line)", borderRadius: 3, padding: 10, marginTop: 8, color: "var(--ht-ink)" };
const evBox: React.CSSProperties = { border: "1px solid var(--ht-line)", borderRadius: 3, padding: 10, marginTop: 8, background: "var(--ht-surface-2)" };
const table: React.CSSProperties = { borderCollapse: "collapse", width: "100%", fontSize: 12 };
const th: React.CSSProperties = { textAlign: "left", padding: "6px 8px", borderBottom: "2px solid var(--ht-line-strong)", color: "var(--ht-ink-2)" };
const td: React.CSSProperties = { padding: "6px 8px", borderBottom: "1px solid var(--ht-line)", verticalAlign: "top" };
const ul: React.CSSProperties = { margin: "4px 0", paddingLeft: 18 };
