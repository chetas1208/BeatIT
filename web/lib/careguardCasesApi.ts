// Case browser API client (additive). Lists packaged cases and serves one case's
// composite demo payload + asset URLs (ECG PNG, echo GIF/frame).

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1";
const CG = `${API_BASE}/careguard`;

export interface CaseListRow {
  case_id: string;
  age: number | null;
  gender: string | null;
  icu_type: string | null;
  cv_categories: string | null;
  n_noncardiac_organs: number | null;
  ecg_assigned: boolean | null;
  ecg_superclass: string | null;
  overall_completeness_score: number | null;
}

export interface CaseDemo {
  case_id: string;
  summary: Record<string, unknown>;
  ct_imaging?: { status: string; reason?: string; same_subject_as_clinical_record?: boolean };
  modalities: {
    ecg: { source: string | null; same_patient_as_ehr: boolean; warning?: string | null };
    echo: {
      source: string | null;
      same_patient_as_ehr: boolean;
      donor_ejection_fraction_pct?: number | null;
      warning?: string | null;
      note?: string | null;
    };
  };
  quality: { overall_completeness_score: number | null; warnings: string[] };
  assets: Record<string, string>;
  composite_notice: string;
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export const careguardCasesApi = {
  list: () => getJson<{ count: number; cases: CaseListRow[] }>(`${CG}/cases`),
  demo: (caseId: string) => getJson<CaseDemo>(`${CG}/cases/${caseId}/demo`),
  // Fetch a packaged case's FHIR bundle (to import + analyze a pre-tested case).
  bundle: (caseId: string) => getJson<Record<string, unknown>>(`${CG}/cases/${caseId}/bundle`),
  // asset paths from demo() are relative to the careguard router (e.g. /cases/<id>/asset/echo.gif)
  assetUrl: (relPath: string) => `${CG}${relPath}`,
};
