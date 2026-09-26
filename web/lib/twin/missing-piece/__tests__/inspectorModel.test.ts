import assert from "node:assert/strict";
import test from "node:test";

import { buildM8InspectorView } from "@/lib/twin/comparison/m8Inspector";
import type { MissingPieceResponse } from "@/types/missing-piece";

const DISCLAIMER =
  "Educational cardiac simulation only. Not for diagnosis or treatment decisions. SIMULATION ONLY. DualBeat is not a medical device, does not provide medical advice, and all outputs are simulated educational estimates.";

function minimalResult(): MissingPieceResponse {
  return {
    target_metric: "stroke_volume_ml",
    sensitivities: [],
    dominant_uncertainty_drivers: [
      {
        parameter_id: "contractility_index",
        metric_id: "stroke_volume_ml",
        uncertainty_magnitude: 0.4,
        sensitivity_magnitude: 0.6,
        impact_score: 0.24,
        normalized_impact: 1,
        method: "uncertainty-impact-heuristic-v1",
      },
    ],
    evidence_ranking: [
      {
        evidence_type: "echocardiographic_measurement",
        target_metric: "stroke_volume_ml",
        constrained_parameters: ["contractility_index"],
        ranking_score: 0.18,
        method: "evidence-priority-score-v1",
        assumptions: [],
      },
    ],
    evidence_constraints: [],
    limitations: ["Evidence Priority Score is not expected information gain or a medical recommendation."],
    safety_disclaimer: DISCLAIMER,
  } as unknown as MissingPieceResponse;
}

test("returns empty guidance when no analysis is loaded", () => {
  const view = buildM8InspectorView(null);
  assert.equal(view.targetMetric, "unavailable");
  assert.equal(view.impacts.length, 0);
});

test("maps dominant drivers and evidence types from a Missing Piece response", () => {
  const view = buildM8InspectorView(minimalResult());
  assert.equal(view.targetMetric, "stroke_volume_ml");
  assert.equal(view.impacts[0]?.parameter_id, "contractility_index");
  assert.deepEqual(view.evidenceTypes, ["echocardiographic_measurement"]);
  assert.match(view.limitation, /not expected information gain/i);
});
