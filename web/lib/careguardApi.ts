// CareGuard API client. Talks to the flag-on FastAPI backend under
// /api/v1/careguard. Base is configurable so the console can point at a
// CareGuard-enabled backend (e.g. :8001 in local dev) without touching the
// existing DualBeat API client.

import type {
  AlternativeCandidate,
  CareGuardRun,
  EvidenceCitation,
  MedicationSafety,
  MedicationSafetyConflict,
  PatientContext,
} from "@/types/careguard";

const BASE =
  process.env.NEXT_PUBLIC_CAREGUARD_API_BASE ??
  (process.env.NEXT_PUBLIC_API_BASE
    ? `${process.env.NEXT_PUBLIC_API_BASE}/careguard`
    : "http://localhost:8001/api/v1/careguard");

export const CAREGUARD_ENABLED =
  (process.env.NEXT_PUBLIC_CAREGUARD_ENABLED ?? "false").toLowerCase() === "true";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.message ?? body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(`CareGuard ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const careguardApi = {
  health: () => req<{ status: string }>("/health"),
  config: () => req<Record<string, unknown>>("/config"),

  importFixture: (fixtureId: string, clinicalQuestion: string) =>
    req<{ case_id: string; validation: unknown; missing_critical_evidence: string[] }>(
      "/fhir/import",
      { method: "POST", body: JSON.stringify({ fixture_id: fixtureId, clinical_question: clinicalQuestion }) },
    ),

  // Manual mode: import an inline FHIR R4 bundle (paste/upload).
  importBundle: (bundle: unknown, clinicalQuestion: string) =>
    req<{ case_id: string; validation: Record<string, unknown>; missing_critical_evidence: string[] }>(
      "/fhir/import",
      { method: "POST", body: JSON.stringify({ bundle, clinical_question: clinicalQuestion }) },
    ),

  loadPackaged: async (caseId: string, clinicalQuestion: string) => {
    const bundle = await req<Record<string, unknown>>(`/cases/${encodeURIComponent(caseId)}/bundle`);
    const imported = await careguardApi.importBundle(bundle, clinicalQuestion);
    return {
      ...imported,
      ingestion: {
        file_count: 1,
        files_analyzed: [`${caseId}/bundle`],
        modalities_analyzed: ["FHIR bundle"],
        labs_summary: {},
        ehr_counts: {},
        ecg: {},
        analysis_profiles: ["packaged case"],
      },
    };
  },

  createRun: (caseId: string, workflowIntent = "care_plan_comparison") =>
    req<{ run: CareGuardRun }>("/runs", {
      method: "POST",
      body: JSON.stringify({ case_id: caseId, workflow_intent: workflowIntent }),
    }),

  advance: (runId: string) =>
    req<{ run: CareGuardRun; stage_result: unknown; terminal?: boolean }>(
      `/runs/${runId}/next`,
      { method: "POST" },
    ),

  context: (caseId: string) =>
    req<{ patient_context: PatientContext }>(`/cases/${caseId}/context`),
  evidence: (caseId: string) =>
    req<{ citations: EvidenceCitation[] }>(`/cases/${caseId}/evidence`),
  candidates: (caseId: string) =>
    req<{ candidates: Record<string, unknown>[] }>(`/cases/${caseId}/candidates`),
  simulation: (caseId: string) =>
    req<{ simulation: Record<string, unknown> }>(`/cases/${caseId}/simulation`),
  critic: (caseId: string) =>
    req<{ critic: Record<string, unknown> }>(`/cases/${caseId}/critic`),
  audit: (caseId: string) =>
    req<{ audit: Record<string, unknown>[]; count: number }>(`/cases/${caseId}/audit`),

  medicationSafety: (caseId: string) =>
    req<{ medication_safety: MedicationSafety }>(`/cases/${caseId}/medication-safety`),
  medicationConflicts: (caseId: string) =>
    req<{ conflicts: MedicationSafetyConflict[] }>(`/cases/${caseId}/medication-conflicts`),
  medicationAlternatives: (caseId: string) =>
    req<{ alternatives: AlternativeCandidate[] }>(`/cases/${caseId}/medication-alternatives`),

  feedback: (caseId: string, decision: string, reason: string, candidateId?: string) =>
    req<{ recorded: boolean }>(`/cases/${caseId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ decision, reason, candidate_id: candidateId }),
    }),

  careEvaluation: (caseId: string, doctorReport: string, patientProgress: string) =>
    req<{ care_evaluation: Record<string, unknown> }>(`/cases/${caseId}/care-evaluation`, {
      method: "POST",
      body: JSON.stringify({ doctor_report: doctorReport, patient_progress: patientProgress }),
    }),

  copilot: (caseId: string, question: string) =>
    req<{ copilot: { answer: string; used_anthropic: boolean; grounded_on: string[] } }>(
      `/cases/${caseId}/copilot`,
      { method: "POST", body: JSON.stringify({ question }) },
    ),
};

export const CAREGUARD_BASE = BASE;
