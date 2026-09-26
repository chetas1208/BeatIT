import assert from "node:assert/strict";
import test from "node:test";
import { createFixtureState } from "@/lib/heart/__tests__/fixtures";
import type { ParameterDistribution, TwinEnsemble, TwinSample } from "@/lib/twin/ensemble/contracts";
import { chooseRepresentatives, runEnsemble } from "@/lib/twin/ensemble/runner";
import type { TwinSnapshot } from "@/lib/twin/time/contracts";

function snapshot(): TwinSnapshot {
  const state = createFixtureState();
  return {
    id: "snapshot-m5-fixture",
    timestamp: state.created_at,
    state,
    evidenceIds: ["fixture:evidence", "fixture:echo"],
    changedFields: [],
    provenance: [{ source: "clinical_record", sourceId: "fixture-record" }],
    quality: "observed",
  };
}

function fixed(parameterId: ParameterDistribution["parameterId"], value: number): ParameterDistribution {
  const bounds = parameterId === "heart_rate_bpm"
    ? { min: 30, max: 200 }
    : parameterId === "preload_index" || parameterId === "contractility_index"
      ? { min: 0, max: 1.5 }
      : { min: 0, max: 2 };
  return {
    parameterId,
    family: "fixed",
    parameters: { value },
    bounds,
    source: "scenario",
    evidenceIds: ["fixture:evidence"],
    rationale: "Deterministic fixture input for ensemble runner tests.",
    version: "test-v1",
  };
}

function empiricalDistributions(): readonly ParameterDistribution[] {
  return [
    {
      parameterId: "heart_rate_bpm",
      family: "empirical",
      parameters: { values: [60, 80, 100] },
      bounds: { min: 30, max: 200 },
      source: "scenario",
      evidenceIds: ["fixture:evidence"],
      rationale: "Deterministic empirical fixture input for replay tests.",
      version: "test-v1",
    },
    fixed("preload_index", 0.8),
    fixed("afterload_index", 1.1),
    fixed("contractility_index", 0.72),
    fixed("systemic_vascular_resistance_index", 0.9),
  ];
}

function config(seed: number, distributions: readonly ParameterDistribution[] = empiricalDistributions()) {
  return { seed, requestedSampleCount: 20, distributions };
}

function heartRate(sample: TwinSample): number {
  return sample.state.measurements.heart_rate_bpm?.value ?? Number.NaN;
}

function fixtureEnsemble(overrides: Partial<TwinEnsemble> = {}): TwinEnsemble {
  const base = runEnsemble(snapshot(), config(7));
  return { ...base, ...overrides };
}

test("replays an ensemble byte-for-byte for the same snapshot and seed", () => {
  const source = snapshot();
  const first = runEnsemble(source, config(7));
  const replay = runEnsemble(source, config(7));

  assert.deepEqual(replay, first);
  assert.deepEqual(source.state, createFixtureState());
});

test("changes sampled members and ensemble identity when the seed changes", () => {
  const first = runEnsemble(snapshot(), config(7));
  const second = runEnsemble(snapshot(), config(42));

  assert.notEqual(second.id, first.id);
  assert.notDeepEqual(
    second.samples.map(heartRate),
    first.samples.map(heartRate),
  );
  assert.equal(second.seed, 42);
});

test("accounts for rejected normal draws and retains their reasons", () => {
  const distributions = [
    {
      parameterId: "heart_rate_bpm" as const,
      family: "normal" as const,
      parameters: { mean: 70, sd: 4 },
      bounds: { min: 65, max: 75 },
      source: "scenario" as const,
      evidenceIds: ["fixture:evidence"],
      rationale: "Narrow support deliberately exercises rejection accounting.",
      version: "test-v1",
    },
    fixed("preload_index", 0.8),
    fixed("afterload_index", 1.1),
    fixed("contractility_index", 0.72),
    fixed("systemic_vascular_resistance_index", 0.9),
  ] satisfies readonly ParameterDistribution[];
  const ensemble = runEnsemble(snapshot(), { ...config(7, distributions), requestedSampleCount: 24 });
  const rejected = ensemble.samples.filter((sample) => !sample.valid);

  assert.ok(rejected.length > 0);
  assert.ok(ensemble.acceptedSampleCount > 0);
  assert.equal(ensemble.acceptedSampleCount + ensemble.rejectedSampleCount, ensemble.requestedSampleCount);
  assert.equal(ensemble.rejectedSampleCount, rejected.length);
  assert.ok(rejected.every((sample) => sample.rejectionReasons.some((reason) => reason.includes("outside declared bounds"))));
  assert.ok(ensemble.samples.filter((sample) => sample.valid).every((sample) => sample.rejectionReasons.length === 0));
});

test("summarizes accepted outputs as sorted finite distributions", () => {
  const ensemble = runEnsemble(snapshot(), config(7));
  const expectedUnits = new Map([
    ["ejection_fraction_pct", "%"],
    ["stroke_volume_ml", "mL"],
    ["cardiac_output_l_min", "L/min"],
    ["heart_rate_bpm", "bpm"],
  ]);

  assert.deepEqual(ensemble.distributions.map(({ metricId }) => metricId), [...expectedUnits.keys()]);
  for (const distribution of ensemble.distributions) {
    assert.equal(distribution.unit, expectedUnits.get(distribution.metricId));
    assert.equal(distribution.samples.length, ensemble.acceptedSampleCount);
    assert.ok(distribution.samples.every(Number.isFinite));
    assert.deepEqual(distribution.samples, [...distribution.samples].sort((a, b) => a - b));
    assert.ok(distribution.min <= distribution.quantiles.q05);
    assert.ok(distribution.quantiles.q05 <= distribution.quantiles.q25);
    assert.ok(distribution.quantiles.q25 <= distribution.median);
    assert.ok(distribution.median <= distribution.quantiles.q75);
    assert.ok(distribution.quantiles.q75 <= distribution.quantiles.q95);
    assert.ok(distribution.quantiles.q95 <= distribution.max);
  }

  const heartRateDistribution = ensemble.distributions.find(({ metricId }) => metricId === "heart_rate_bpm");
  assert.ok(heartRateDistribution);
  assert.equal(heartRateDistribution.mean, 80);
  assert.equal(heartRateDistribution.median, 80);
  assert.equal(heartRateDistribution.min, 60);
  assert.equal(heartRateDistribution.max, 100);
});

test("records snapshot, evidence, seed, versions, and assumptions in provenance", () => {
  const ensemble = runEnsemble(snapshot(), {
    ...config(19),
    physiologyVersion: "physiology-test-v1",
    distributionConfigVersion: "distribution-test-v1",
    priorVersion: "prior-test-v1",
  });

  assert.deepEqual(ensemble.provenance, {
    originSnapshotId: "snapshot-m5-fixture",
    originTimestamp: "2026-09-26T00:00:00Z",
    originQuality: "observed",
    originProvenance: [{ source: "clinical_record", sourceId: "fixture-record" }],
    evidenceIds: ["fixture:evidence", "fixture:echo"],
    seed: 19,
    physiologyVersion: "physiology-test-v1",
    distributionConfigVersion: "distribution-test-v1",
    priorVersion: "prior-test-v1",
    createdAt: "2026-09-26T00:00:00Z",
    assumptions: [
      "Parameters are sampled independently because BeatIT has no validated joint correlation model for these proxies.",
      "Percentiles describe accepted deterministic simulations, not clinical probability or confidence intervals.",
    ],
  });
  assert.ok(ensemble.samples.every((sample) => sample.originSnapshotId === ensemble.originSnapshotId && sample.seed === ensemble.seed));
});

test("selects low, lower-median, and high valid representatives for a metric", () => {
  const ensemble = runEnsemble(snapshot(), config(7));
  const representatives = chooseRepresentatives(ensemble, "heart_rate_bpm");

  assert.ok(representatives.low);
  assert.ok(representatives.median);
  assert.ok(representatives.high);
  assert.equal(heartRate(representatives.low), 60);
  assert.equal(heartRate(representatives.median), 80);
  assert.equal(heartRate(representatives.high), 100);
  assert.ok(representatives.low.index < ensemble.samples.length);
  assert.ok(representatives.median.index < ensemble.samples.length);
  assert.ok(representatives.high.index < ensemble.samples.length);
});

test("returns null representatives when no samples are valid", () => {
  const ensemble = fixtureEnsemble({
    samples: Object.freeze([
      Object.freeze({
        ...fixtureEnsemble().samples[0],
        valid: false,
        rejectionReasons: Object.freeze(["fixture rejection"]),
      }),
    ]),
  });

  assert.deepEqual(chooseRepresentatives(ensemble), { median: null, low: null, high: null });
});
