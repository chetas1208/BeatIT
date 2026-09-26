import { CareGuardConsole } from "@/components/careguard/CareGuardConsole";

/*
 * CareGuard route — the clinician-facing multimorbidity evidence-review console.
 * Additive to BeatIT; only reachable when NEXT_PUBLIC_CAREGUARD_ENABLED=true.
 * This is a task workflow (import → context → evidence → conflicts → alternatives
 * → simulation → critic → decision), never a generic dashboard.
 */
export default function CareGuardPage() {
  return <CareGuardConsole />;
}
