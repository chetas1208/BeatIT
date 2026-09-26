import CareGuardRunner from "@/components/careguard/runner/CareGuardRunner";

export const metadata = {
  title: "BeatIT CareGuard — Runner",
  description: "Two ways to exercise CareGuard: paste/upload a FHIR bundle, or pick a pre-tested case.",
};

export default function CareGuardRunnerPage() {
  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "24px 20px" }}>
      <h1 style={{ margin: "0 0 4px" }}>BeatIT CareGuard — Runner</h1>
      <p style={{ margin: "0 0 18px", color: "#64748b", fontSize: 14 }}>
        Two input modes. <b>Manual</b>: paste or upload a FHIR R4 bundle. <b>Pre-tested</b>: pick one
        of the 1,000 packaged composite cases. Either way, the bundle is imported and parsed into a
        deterministic patient context that verifies the pipeline works — then optionally run the agents.
      </p>
      <CareGuardRunner />
    </main>
  );
}
