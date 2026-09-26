import CaseBrowser from "@/components/careguard/cases/CaseBrowser";

export const metadata = {
  title: "CareGuard — Case Browser",
  description: "Browse and demo the 1,000 composite research cases (EHR + ECG + echo).",
};

export default function CareGuardCasesPage() {
  return (
    <main style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 20px" }}>
      <h1 style={{ margin: "0 0 4px" }}>BeatIT CareGuard — Case Browser</h1>
      <p style={{ margin: "0 0 16px", color: "#64748b", fontSize: 14 }}>
        1,000 composite research cases (real deidentified eICU EHR + matched PTB-XL ECG + matched
        EchoNet-Dynamic echo). Select a case to demo it. Matched modalities are from different
        individuals than the eICU record — never presented as the patient&apos;s own.
      </p>
      <CaseBrowser />
    </main>
  );
}
