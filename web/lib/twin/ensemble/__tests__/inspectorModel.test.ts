import assert from "node:assert/strict";
import test from "node:test";
import { createFixtureState } from "@/lib/heart/__tests__/fixtures";
import { getComponentUncertaintyView, metricLabel } from "@/lib/twin/ensemble/inspectorModel";
import type { TwinEnsemble } from "@/lib/twin/ensemble/contracts";

function ensemble(originQuality: TwinEnsemble["provenance"]["originQuality"] = "observed"): TwinEnsemble {
  const state = createFixtureState();
  return {
    id: "ensemble-inspector-fixture",
    originSnapshotId: "snapshot-inspector",
    seed: 1208,
    requestedSampleCount: 1,
    acceptedSampleCount: 1,
    rejectedSampleCount: 0,
    samples: [],
    distributions: [
      { metricId: "ejection_fraction_pct", unit: "%", samples: [55], mean: 55, median: 55, variance: 0, standardDeviation: 0, quantiles: { q05: 55, q25: 55, q75: 55, q95: 55 }, min: 55, max: 55 },
      { metricId: "stroke_volume_ml", unit: "mL", samples: [72], mean: 72, median: 72, variance: 0, standardDeviation: 0, quantiles: { q05: 72, q25: 72, q75: 72, q95: 72 }, min: 72, max: 72 },
      { metricId: "cardiac_output_l_min", unit: "L/min", samples: [5.2], mean: 5.2, median: 5.2, variance: 0, standardDeviation: 0, quantiles: { q05: 5.2, q25: 5.2, q75: 5.2, q95: 5.2 }, min: 5.2, max: 5.2 },
      { metricId: "heart_rate_bpm", unit: "bpm", samples: [72], mean: 72, median: 72, variance: 0, standardDeviation: 0, quantiles: { q05: 72, q25: 72, q75: 72, q95: 72 }, min: 72, max: 72 },
    ],
    parameterDistributions: [],
    provenance: {
      originSnapshotId: "snapshot-inspector",
      originTimestamp: state.created_at,
      originQuality,
      originProvenance: [{ source: originQuality === "synthetic" ? "synthetic_replay" : "clinical_record" }],
      evidenceIds: [],
      seed: 1208,
      physiologyVersion: "m5.5-ensemble-projection-v1",
      distributionConfigVersion: "m5.5-backend-ensemble-v1",
      priorVersion: "m5-priors-v1",
      createdAt: state.created_at,
      assumptions: [],
    },
    warnings: [],
    safetyDisclaimer: "Educational cardiac simulation only.",
    representativeIds: { low: "sample-0", median: "sample-0", high: "sample-0" },
  };
}

test("maps only the declared scalar metrics to each supported component", () => {
  const source = ensemble();

  assert.deepEqual(getComponentUncertaintyView(source, "left-ventricle").distributions.map((item) => item.metricId), [
    "ejection_fraction_pct",
    "stroke_volume_ml",
    "cardiac_output_l_min",
  ]);
  assert.deepEqual(getComponentUncertaintyView(source, "blood-flow").distributions.map((item) => item.metricId), [
    "stroke_volume_ml",
    "cardiac_output_l_min",
  ]);
  assert.deepEqual(getComponentUncertaintyView(source, "right-ventricle").distributions, []);
});

test("keeps origin quality and lineage source labels explicit", () => {
  const view = getComponentUncertaintyView(ensemble("synthetic"));

  assert.equal(view.componentLabel, "Left ventricle");
  assert.equal(view.originQualityLabel, "Synthetic replay");
  assert.equal(view.provenanceSourceLabel, "Synthetic replay");
  assert.equal(metricLabel("ejection_fraction_pct"), "Ejection fraction");
});

test("reports unavailable scalar uncertainty without inventing an anatomical estimate", () => {
  const view = getComponentUncertaintyView(ensemble(), "right-ventricle");

  assert.match(view.unavailableMessage, /scalar uncertainty is unavailable/);
  assert.match(view.unavailableMessage, /No anatomical uncertainty is inferred/);
  assert.equal(getComponentUncertaintyView({ ...ensemble(), provenance: { ...ensemble().provenance, originProvenance: [] } }, "right-ventricle").provenanceSourceLabel, "Unavailable");
  assert.equal(getComponentUncertaintyView({ ...ensemble(), provenance: { ...ensemble().provenance, originProvenance: [{ source: "unexpected" as "clinical_record" }] } }, "right-ventricle").provenanceSourceLabel, "Unrecognized source");
});
