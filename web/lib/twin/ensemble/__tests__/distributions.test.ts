import assert from "node:assert/strict";
import test from "node:test";
import {
  createSeededRandom,
  sampleDistribution,
  validateDistribution,
} from "@/lib/twin/ensemble/distributions";
import type {
  DistributionBounds,
  DistributionFamily,
  ParameterDistribution,
} from "@/lib/twin/ensemble/contracts";

const scenarioBounds: DistributionBounds = { min: 30, max: 200 };

function distribution(
  family: DistributionFamily,
  parameters: ParameterDistribution["parameters"],
  bounds: DistributionBounds = scenarioBounds,
): ParameterDistribution {
  return {
    parameterId: "heart_rate_bpm",
    family,
    parameters,
    bounds,
    source: "population_prior",
    evidenceIds: ["evidence-1"],
    rationale: "Focused distribution test fixture.",
    version: "m5-test-v1",
  };
}

function samples(
  value: ParameterDistribution,
  seed: number,
  count = 8,
): number[] {
  const random = createSeededRandom(seed);
  return Array.from({ length: count }, () => sampleDistribution(value, random));
}

test("accepts valid fixed, normal, uniform, and empirical distributions", () => {
  const validDistributions = [
    distribution("fixed", { value: 72 }),
    distribution("normal", { mean: 72, sd: 4 }),
    distribution("uniform", { min: 60, max: 90 }),
    distribution("empirical", { values: [60, 72, 90] }),
  ];

  for (const value of validDistributions) {
    assert.doesNotThrow(() => validateDistribution(value));
  }
});

test("rejects invalid standard deviation, bounds, and NaN values", () => {
  const invalidCases: Array<[string, ParameterDistribution, RegExp]> = [
    [
      "zero standard deviation",
      distribution("normal", { mean: 72, sd: 0 }),
      /standard deviation must be > 0/,
    ],
    [
      "negative standard deviation",
      distribution("normal", { mean: 72, sd: -1 }),
      /standard deviation must be > 0/,
    ],
    [
      "reversed bounds",
      distribution("fixed", { value: 72 }, { min: 100, max: 90 }),
      /bounds are reversed/,
    ],
    [
      "bounds outside scenario range",
      distribution("fixed", { value: 72 }, { min: 29, max: 200 }),
      /bounds exceed scenario bounds/,
    ],
    [
      "NaN bounds",
      distribution("fixed", { value: 72 }, { min: Number.NaN, max: 200 }),
      /bounds\.min must be finite/,
    ],
    [
      "NaN parameter",
      distribution("fixed", { value: Number.NaN }),
      /Distribution parameter value must be finite/,
    ],
  ];

  for (const [label, value, message] of invalidCases) {
    assert.throws(() => validateDistribution(value), { name: "RangeError", message });
    assert.throws(() => sampleDistribution(value, createSeededRandom(7)), { name: "RangeError", message }, label);
  }
});

test("samples fixed, normal, uniform, and empirical distributions from a seeded source", () => {
  const fixedSamples = samples(distribution("fixed", { value: 72 }), 2026);
  assert.deepEqual(fixedSamples, Array.from({ length: 8 }, () => 72));

  const normalSamples = samples(distribution("normal", { mean: 72, sd: 4 }), 2026);
  assert.equal(normalSamples.length, 8);
  assert.ok(normalSamples.every(Number.isFinite));
  assert.ok(new Set(normalSamples).size > 1);

  const uniformSamples = samples(distribution("uniform", { min: 60, max: 90 }), 2026);
  assert.ok(uniformSamples.every((value) => value >= 60 && value <= 90));

  const empiricalValues = [60, 72, 90];
  const empiricalSamples = samples(distribution("empirical", { values: empiricalValues }), 2026);
  assert.ok(empiricalSamples.every((value) => empiricalValues.includes(value)));
});

test("reproduces the same samples for the same seed across all supported families", () => {
  const distributions = [
    distribution("fixed", { value: 72 }),
    distribution("normal", { mean: 72, sd: 4 }),
    distribution("uniform", { min: 60, max: 90 }),
    distribution("empirical", { values: [60, 72, 90] }),
  ];

  for (const value of distributions) {
    assert.deepEqual(samples(value, 4242), samples(value, 4242));
  }
});
