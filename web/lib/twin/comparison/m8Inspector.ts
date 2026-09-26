import type { MissingPieceResponse, ParameterUncertaintyImpact } from "@/types/missing-piece";

export type M8InspectorView = {
  targetMetric: string;
  impacts: ParameterUncertaintyImpact[];
  evidenceTypes: string[];
  limitation: string;
};

export function buildM8InspectorView(result: MissingPieceResponse | null): M8InspectorView {
  if (!result) {
    return {
      targetMetric: "unavailable",
      impacts: [],
      evidenceTypes: [],
      limitation: "Run a target-specific Missing Piece analysis to expose scalar uncertainty drivers.",
    };
  }
  return {
    targetMetric: result.target_metric,
    impacts: result.dominant_uncertainty_drivers,
    evidenceTypes: result.evidence_ranking.map((item) => item.evidence_type),
    limitation: result.limitations[0] ?? "Scalar deterministic projection only.",
  };
}
