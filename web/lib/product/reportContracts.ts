import type { BeatITSessionContext } from "./contracts";

export type ReportSectionStatus = "ready" | "partial" | "unavailable";

export interface ProductReportSection {
  id: string;
  title: string;
  status: ReportSectionStatus;
  summary: string;
  provenance: string[];
}

export interface ProductReport {
  title: string;
  context: BeatITSessionContext;
  safetyDisclaimer: string;
  sections: ProductReportSection[];
  limitations: string[];
}

export interface ProductReportInput {
  context: BeatITSessionContext;
  safetyDisclaimer: string | null;
  hasState: boolean;
  hasVisualization: boolean;
  hasTimeline: boolean;
  hasExperiment: boolean;
  hasComparison: boolean;
  hasEvidence: boolean;
  provenance: string[];
}

export function buildProductReport(input: ProductReportInput): ProductReport {
  const section = (id: string, title: string, ready: boolean, summary: string): ProductReportSection => ({
    id,
    title,
    status: ready ? "ready" : "unavailable",
    summary,
    provenance: input.provenance,
  });

  return {
    title: "BeatIT computational session report",
    context: input.context,
    safetyDisclaimer: input.safetyDisclaimer ?? "Educational simulation only; not for diagnosis or treatment decisions.",
    sections: [
      section("twin", "Observed twin", input.hasState && input.hasVisualization, input.hasState ? "The active cardiac state and visualization are available for inspection." : "Run or load a case to populate the observed twin."),
      section("timeline", "Timeline", input.hasTimeline, input.hasTimeline ? "The selected timeline context is retained in this session." : "No longitudinal timeline is available."),
      section("experiment", "Bounded experiment", input.hasExperiment, input.hasExperiment ? "A hypothetical branch or paired experiment is available." : "No completed hypothetical experiment is recorded."),
      section("comparison", "Paired comparison", input.hasComparison, input.hasComparison ? "A same-sample baseline/counterfactual pair is available." : "No paired comparison is selected."),
      section("evidence", "Evidence and uncertainty", input.hasEvidence, input.hasEvidence ? "Evidence mapping and bounded uncertainty context are available." : "Evidence analysis is unavailable until a plausible-twin ensemble exists."),
    ],
    limitations: [
      "This report summarizes deterministic computational outputs and provenance; it is not a diagnosis, treatment plan, or clinical measurement.",
      "Hypothetical and plausible-twin results remain explicitly labeled and do not replace observed history.",
      "Unavailable sections are retained as unavailable rather than filled with inferred values.",
    ],
  };
}
