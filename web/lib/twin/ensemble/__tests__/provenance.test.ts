import assert from "node:assert/strict";
import test from "node:test";
import { createFixtureState } from "@/lib/heart/__tests__/fixtures";
import type { EnsembleConfig, ParameterDistribution } from "@/lib/twin/ensemble/contracts";
import { runEnsemble } from "@/lib/twin/ensemble/runner";
import type { TwinSnapshot } from "@/lib/twin/time/contracts";

function snapshot(quality: TwinSnapshot["quality"] = "observed"): TwinSnapshot {
  const state = createFixtureState();
  return {
    id: "snapshot-m5-provenance-fixture",
    timestamp: state.created_at,
    state,
    evidenceIds: ["fixture:evidence", "fixture:echo"],
    changedFields: [],
    provenance: [{ source: "clinical_record", sourceId: "fixture-record" }],
    quality,
  };
}

function fixed(
  parameterId: ParameterDistribution["parameterId"],
  value: number,
  evidenceIds: readonly string[] = [],
): ParameterDistribution {
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
    evidenceIds,
    rationale: "Deterministic provenance fixture input.",
    version: "test-v1",
  };
}

function distributions(): readonly ParameterDistribution[] {
  return [
    fixed("heart_rate_bpm", 72, ["fixture:evidence", "distribution:heart-rate"]),
    fixed("preload_index", 0.8, ["distribution:preload", "fixture:echo"]),
    fixed("afterload_index", 1.1),
    fixed("contractility_index", 0.72),
    fixed("systemic_vascular_resistance_index", 0.9),
  ];
}

function config(overrides: Partial<EnsembleConfig> = {}): EnsembleConfig {
  return {
    seed: 7,
    requestedSampleCount: 6,
    distributions: distributions(),
    ...overrides,
  };
}

test("includes every ensemble version in the ensemble identity", () => {
  const source = snapshot();
  const base = runEnsemble(source, config());
  const variants = [
    runEnsemble(source, config({ physiologyVersion: "physiology-test-v2" })),
    runEnsemble(source, config({ distributionConfigVersion: "distribution-test-v2" })),
    runEnsemble(source, config({ priorVersion: "prior-test-v2" })),
  ];

  assert.equal(new Set([base, ...variants].map((ensemble) => ensemble.id)).size, 4);
  assert.deepEqual(base.provenance, {
    originSnapshotId: source.id,
    originTimestamp: source.timestamp,
    originQuality: "observed",
    originProvenance: source.provenance,
    evidenceIds: ["fixture:evidence", "fixture:echo", "distribution:heart-rate", "distribution:preload"],
    seed: 7,
    physiologyVersion: "m4-deterministic-v1",
    distributionConfigVersion: "m5-ensemble-v1",
    priorVersion: "m5-priors-v1",
    createdAt: source.timestamp,
    assumptions: [
      "Parameters are sampled independently because BeatIT has no validated joint correlation model for these proxies.",
      "Percentiles describe accepted deterministic simulations, not clinical probability or confidence intervals.",
    ],
  });
});

test("keeps sample IDs unique across seeds and ensemble configurations", () => {
  const ensembles = [
    runEnsemble(snapshot(), config({ seed: 7 })),
    runEnsemble(snapshot(), config({ seed: 42 })),
    runEnsemble(snapshot(), config({ requestedSampleCount: 7 })),
    runEnsemble(snapshot(), config({ parentScenarioId: "scenario-provenance-fixture" })),
  ];
  const sampleIds = ensembles.flatMap((ensemble) => ensemble.samples.map((sample) => sample.id));

  assert.equal(new Set(sampleIds).size, sampleIds.length);
  for (const ensemble of ensembles) {
    assert.equal(new Set(ensemble.samples.map((sample) => sample.id)).size, ensemble.samples.length);
  }
});

test("aggregates snapshot and parameter evidence IDs without duplicates", () => {
  const ensemble = runEnsemble(snapshot(), config());

  assert.deepEqual(ensemble.provenance.evidenceIds, [
    "fixture:evidence",
    "fixture:echo",
    "distribution:heart-rate",
    "distribution:preload",
  ]);
});

test("warns when the ensemble originates from synthetic replay data", () => {
  const synthetic = runEnsemble(snapshot("synthetic"), config());
  const observed = runEnsemble(snapshot(), config());
  const warning = "Origin snapshot is synthetic replay data; it is not patient evidence.";

  assert.equal(synthetic.provenance.originQuality, "synthetic");
  assert.ok(synthetic.warnings.includes(warning));
  assert.ok(!observed.warnings.includes(warning));
});
