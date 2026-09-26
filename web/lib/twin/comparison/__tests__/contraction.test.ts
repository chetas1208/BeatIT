import assert from "node:assert/strict";
import test from "node:test";
import {
  buildContractionVisualMapping,
  CONTRACTION_DISPLAY_LIMITATION,
  CONTRACTION_MISSING_LIMITATION,
  CONTRACTION_RANGE_LIMITATION,
  CONTRACTION_VISUAL_LIMITATION,
  type ContractionPairInput,
} from "@/lib/twin/comparison/contraction";

function input(overrides: Partial<ContractionPairInput> = {}): ContractionPairInput {
  return {
    metricId: "ejection_fraction_pct",
    baseline: { value: 42, unit: "%" },
    scenario: { value: 48, unit: "%" },
    delta: { value: 6, unit: "percentage_points" },
    ...overrides,
  };
}

test("maps supplied paired values to bounded visual references", () => {
  const result = buildContractionVisualMapping(input());

  assert.equal(result.availability, "complete");
  assert.equal(result.metricLabel, "Ejection fraction");
  assert.equal(result.baseline.label, "BASELINE VISUAL REFERENCE");
  assert.equal(result.scenario.label, "SCENARIO VISUAL REFERENCE");
  assert.equal(result.baseline.displayLevel, 0.42);
  assert.equal(result.scenario.displayLevel, 0.48);
  assert.equal(result.difference.direction, "higher_supplied_value");
  assert.equal(result.difference.label, "SUPPLIED VALUE HIGHER");
  assert.equal(result.difference.delta, 6);
  assert.equal(result.difference.displayEmphasis, 0.06);
  assert.deepEqual(result.limitations, [
    CONTRACTION_VISUAL_LIMITATION,
    CONTRACTION_DISPLAY_LIMITATION,
    CONTRACTION_MISSING_LIMITATION,
    CONTRACTION_RANGE_LIMITATION,
  ]);
});

test("uses the canonical delta without deriving it from side values", () => {
  const result = buildContractionVisualMapping(input({
    baseline: { value: 42, unit: "%" },
    scenario: { value: 48, unit: "%" },
    delta: { value: -3, unit: "percentage_points" },
  }));

  assert.equal(result.difference.delta, -3);
  assert.equal(result.difference.direction, "lower_supplied_value");
  assert.equal(result.difference.label, "SUPPLIED VALUE LOWER");
});

test("reports no modeled difference and keeps the zero delta exact", () => {
  const result = buildContractionVisualMapping(input({
    baseline: { value: 1, unit: "index" },
    scenario: { value: 1, unit: "index" },
    delta: { value: 0, unit: "index" },
    metricId: "contractility_index",
  }));

  assert.equal(result.difference.delta, 0);
  assert.equal(result.difference.direction, "no_modeled_difference");
  assert.equal(result.difference.label, "NO MODELED DIFFERENCE");
  assert.equal(result.difference.displayEmphasis, 0);
});

test("fails closed for missing values and bounds display levels", () => {
  const result = buildContractionVisualMapping(input({
    baseline: { value: null, unit: "%" },
    scenario: { value: 120, unit: "%" },
    delta: { value: null, unit: "percentage_points" },
  }));

  assert.equal(result.availability, "partial");
  assert.equal(result.baseline.displayLevel, null);
  assert.equal(result.scenario.displayLevel, 1);
  assert.equal(result.difference.direction, "value_unavailable");
  assert.equal(result.difference.label, "VALUE UNAVAILABLE");
  assert.equal(result.difference.displayEmphasis, 0);
});

test("validates semantic inputs without mutating caller values", () => {
  const source = input();
  const snapshot = structuredClone(source);

  buildContractionVisualMapping(source);
  assert.deepEqual(source, snapshot);
  assert.throws(
    () => buildContractionVisualMapping(input({ baseline: { value: Number.NaN, unit: "%" } })),
    /baseline\.value must be finite/,
  );
  assert.throws(
    () => buildContractionVisualMapping(input({ scenario: { value: 48, unit: "index" } })),
    /units must match/,
  );
  assert.throws(
    () => buildContractionVisualMapping(input({ delta: { value: 6, unit: "" } })),
    /delta\.unit must not be empty/,
  );
  assert.throws(
    () => buildContractionVisualMapping(input({ baseline: { value: 42, unit: "mL" }, scenario: { value: 48, unit: "mL" } })),
    /units are not supported/,
  );
});
