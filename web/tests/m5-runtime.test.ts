import assert from "node:assert/strict";
import test from "node:test";
import {
  createSeededRandom,
  sampleDistribution,
  validateDistribution,
} from "@/lib/twin/ensemble/distributions";
import { mapBackendEnsembleResponse } from "@/lib/twin/ensemble/adapter";
import { pvUncertaintyEnvelope } from "@/lib/twin/ensemble/pvEnvelope";
import type { ParameterDistribution } from "@/lib/twin/ensemble/contracts";
import type { EnsembleApiResponse } from "@/types/ensemble";

const heartRateDistribution: ParameterDistribution = {
  parameterId: "heart_rate_bpm",
  family: "normal",
  parameters: { mean: 72, sd: 3 },
  bounds: { min: 30, max: 200 },
  source: "measurement",
  sourceDetail: "runtime-test-fixture",
  evidenceIds: ["fixture:heart-rate"],
  rationale: "Runtime harness contract fixture.",
  version: "m5-runtime-test-v1",
};

test("executes the M5 distribution contract through the alias-aware Node harness", () => {
  validateDistribution(heartRateDistribution);

  const first = sampleDistribution(
    heartRateDistribution,
    createSeededRandom(2026),
  );
  const replay = sampleDistribution(
    heartRateDistribution,
    createSeededRandom(2026),
  );

  assert.equal(first, replay);
  assert.ok(Number.isFinite(first));
  assert.throws(
    () => validateDistribution({
      ...heartRateDistribution,
      parameters: { mean: 72, sd: 0 },
    }),
    /standard deviation must be > 0/,
  );
});

test("maps the canonical backend response and preserves safety and provenance", () => {
  const state = { measurements: {} } as EnsembleApiResponse["samples"][number]["state"];
  const safetyDisclaimer =
    "Educational cardiac simulation only. Not for diagnosis or treatment decisions. " +
    "SIMULATION ONLY. DualBeat is not a medical device, does not provide medical advice, " +
    "and all outputs are simulated educational estimates.";
  const originProvenance = [{
    source: "synthetic_replay" as const,
    sourceId: "replay-runtime",
    method: "fixture-replay",
    evidenceIds: ["evidence-runtime"],
    note: "Runtime provenance fixture.",
  }];
  const assumptions = ["Runtime mapping must preserve backend lineage."];
  const warning = "Origin snapshot is synthetic replay data; it is not patient evidence.";
  const response = {
    id: "ensemble-runtime",
    origin_snapshot_id: "snapshot-runtime",
    seed: 7,
    requested_sample_count: 1,
    accepted_sample_count: 1,
    rejected_sample_count: 0,
    samples: [{ id: "sample-0", index: 0, seed: 7, origin_snapshot_id: "snapshot-runtime", origin_quality: "synthetic", parameters: {}, outputs: { ejection_fraction_pct: 55 }, state, valid: true, rejection_reasons: [] }],
    distributions: [{ metric_id: "ejection_fraction_pct", unit: "%", samples: [55], mean: 55, median: 55, variance: 0, standard_deviation: 0, quantiles: { q05: 55, q25: 55, q75: 55, q95: 55 }, min: 55, max: 55 }],
    parameter_distributions: [],
    provenance: { origin_snapshot_id: "snapshot-runtime", origin_timestamp: "2026-01-01T00:00:00.000Z", origin_quality: "synthetic", origin_provenance: originProvenance, parent_scenario_id: "scenario-runtime", evidence_ids: ["evidence-runtime"], seed: 7, physiology_version: "m5.5-ensemble-projection-v1", distribution_config_version: "m5.5-backend-ensemble-v1", prior_version: "m5-priors-v1", created_at: "2026-01-01T00:00:00.000Z", assumptions },
    warnings: [warning],
    safety_disclaimer: safetyDisclaimer,
    representative_sample_ids: { low: "sample-0", median: "sample-0", high: "sample-0" },
  } satisfies EnsembleApiResponse;

  const mapped = mapBackendEnsembleResponse(response);
  assert.equal(mapped.samples[0]?.state, state);
  assert.equal(mapped.samples[0]?.originQuality, "synthetic");
  assert.equal(mapped.distributions[0]?.median, 55);
  assert.deepEqual(mapped.provenance, {
    originSnapshotId: "snapshot-runtime",
    originTimestamp: "2026-01-01T00:00:00.000Z",
    originQuality: "synthetic",
    originProvenance,
    parentScenarioId: "scenario-runtime",
    evidenceIds: ["evidence-runtime"],
    seed: 7,
    physiologyVersion: "m5.5-ensemble-projection-v1",
    distributionConfigVersion: "m5.5-backend-ensemble-v1",
    priorVersion: "m5-priors-v1",
    createdAt: "2026-01-01T00:00:00.000Z",
    assumptions,
  });
  assert.deepEqual(mapped.warnings, [warning]);
  assert.equal(mapped.safetyDisclaimer, safetyDisclaimer);
  assert.deepEqual(mapped.representativeIds, response.representative_sample_ids);
  assert.equal(pvUncertaintyEnvelope(mapped).pointwiseLoopAvailable, false);
});
