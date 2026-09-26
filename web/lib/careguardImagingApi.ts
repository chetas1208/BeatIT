// Additive API client for the CT imaging + VISTA routes. Mirrors careguardApi.ts.
import type { CtImaging, EndpointCapabilities } from "@/types/careguardImaging";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1";
const CG = `${API_BASE}/careguard`;

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok && res.status !== 409) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export const careguardImagingApi = {
  sources: () => getJson<{ sources: unknown[] }>(`${CG}/imaging/sources`),
  sourceStatus: () => getJson<{ sources: unknown[] }>(`${CG}/imaging/source-status`),
  vistaCapabilities: () => getJson<EndpointCapabilities>(`${CG}/imaging/vista/capabilities`),
  vistaHealth: () => getJson<{ healthy: boolean; configured: boolean }>(`${CG}/imaging/vista/health`),
  caseImaging: (caseId: string) =>
    getJson<{ case_id: string; ct_imaging: CtImaging }>(`${CG}/cases/${caseId}/imaging`),
  imagingVista: (imagingCaseId: string) =>
    getJson<Record<string, unknown>>(`${CG}/imaging/${imagingCaseId}/vista`),
  imagingMetrics: (imagingCaseId: string) =>
    getJson<Record<string, unknown>>(`${CG}/imaging/${imagingCaseId}/metrics`),
  // Fusion is gated server-side: a non-verified case returns HTTP 409 with a reason.
  fuse: async (caseId: string) => {
    const res = await fetch(`${CG}/cases/${caseId}/imaging/fuse`, { method: "POST" });
    return { status: res.status, body: await res.json() };
  },
};
