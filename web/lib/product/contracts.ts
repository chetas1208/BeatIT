export const BEATIT_MODES = ["twin", "experiment", "compare", "evidence", "report"] as const;

export type BeatITMode = (typeof BEATIT_MODES)[number];

export interface BeatITSessionContext {
  mode: BeatITMode;
  caseId: string | null;
  snapshotId: string | null;
  componentId: string | null;
  ensembleId: string | null;
  scenarioId: string | null;
  shadowTrialId: string | null;
  pairId: string | null;
  analysisId: string | null;
  targetMetric: string | null;
}

export interface ProductSpace {
  id: BeatITMode;
  label: string;
  shortLabel: string;
  description: string;
}

export const PRODUCT_SPACES: readonly ProductSpace[] = [
  { id: "twin", label: "Twin", shortLabel: "TWIN", description: "Observed state, heart, timeline, and sources" },
  { id: "experiment", label: "Experiment", shortLabel: "EXPERIMENT", description: "Bounded causal and Shadow Trial work" },
  { id: "compare", label: "Compare", shortLabel: "COMPARE", description: "Paired baseline and hypothetical views" },
  { id: "evidence", label: "Evidence", shortLabel: "EVIDENCE", description: "Uncertainty, provenance, and evidence gaps" },
  { id: "report", label: "Report", shortLabel: "REPORT", description: "A unified computational session report" },
];

export const DEFAULT_PRODUCT_CONTEXT: BeatITSessionContext = {
  mode: "twin",
  caseId: null,
  snapshotId: null,
  componentId: null,
  ensembleId: null,
  scenarioId: null,
  shadowTrialId: null,
  pairId: null,
  analysisId: null,
  targetMetric: null,
};

export function isBeatITMode(value: string | null | undefined): value is BeatITMode {
  return value != null && (BEATIT_MODES as readonly string[]).includes(value);
}
