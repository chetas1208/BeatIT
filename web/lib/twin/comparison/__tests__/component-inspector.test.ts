import assert from "node:assert/strict";
import test from "node:test";
import {
  buildComponentInspectorModel,
  type ComponentInspectorInput,
} from "@/lib/twin/comparison/component-inspector";

function input(overrides: Partial<ComponentInspectorInput> = {}): ComponentInspectorInput {
  return {
    componentId: "left-ventricle",
    componentLabel: "Left ventricle",
    metricId: "ejection_fraction_pct",
    metricLabel: "Ejection fraction",
    values: {
      baseline: { value: 42, unit: "%" },
      scenario: { value: 48, unit: "%" },
      delta: { value: 6, unit: "percentage points" },
    },
    causalText: "The bounded afterload change is propagated through the deterministic model.",
    provenanceText: "M6 paired result · sample-001 · scenario-001",
    limitations: ["Educational projection only."],
    ...overrides,
  };
}

test("preserves paired canonical values and supplied explanation text", () => {
  const model = buildComponentInspectorModel(input());

  assert.deepEqual(model.baseline, { value: 42, unit: "%" });
  assert.deepEqual(model.scenario, { value: 48, unit: "%" });
  assert.deepEqual(model.delta, { value: 6, unit: "percentage points" });
  assert.equal(model.availability, "complete");
  assert.equal(model.causalText, "The bounded afterload change is propagated through the deterministic model.");
  assert.equal(model.provenanceText, "M6 paired result · sample-001 · scenario-001");
  assert.deepEqual(model.limitations, [
    "Values are read from the canonical paired result; this inspector does not recompute physiology.",
    "Educational projection only.",
  ]);
});

test("keeps zero and negative backend deltas without recomputing them", () => {
  const zero = buildComponentInspectorModel(input({
    values: {
      baseline: { value: 100, unit: "mL" },
      scenario: { value: 100, unit: "mL" },
      delta: { value: 0, unit: "mL" },
    },
  }));
  const source = input({
    values: {
      baseline: { value: 100, unit: "mL" },
      scenario: { value: 96, unit: "mL" },
      delta: { value: -4, unit: "mL" },
    },
  });
  const model = buildComponentInspectorModel(source);

  assert.equal(zero.delta.value, 0);
  assert.equal(model.delta.value, -4);
  assert.equal(model.availability, "complete");
  assert.deepEqual(source.values, {
    baseline: { value: 100, unit: "mL" },
    scenario: { value: 96, unit: "mL" },
    delta: { value: -4, unit: "mL" },
  });
});

test("marks missing paired values as partial or unavailable and supplies honest fallbacks", () => {
  const partial = buildComponentInspectorModel(input({
    componentLabel: null,
    metricLabel: null,
    values: {
      baseline: { value: 70, unit: "bpm" },
      scenario: { value: null, unit: "bpm" },
      delta: { value: null, unit: "bpm" },
    },
    causalText: "   ",
    provenanceText: null,
    limitations: ["   ", "No component-specific value is available."],
  }));
  const unavailable = buildComponentInspectorModel(input({
    values: {
      baseline: { value: null, unit: "index" },
      scenario: { value: null, unit: "index" },
      delta: { value: null, unit: "index" },
    },
  }));

  assert.equal(partial.componentLabel, "left ventricle");
  assert.equal(partial.metricLabel, "ejection fraction pct");
  assert.equal(partial.availability, "partial");
  assert.match(partial.causalText, /No causal explanation/);
  assert.match(partial.provenanceText, /No provenance description/);
  assert.equal(partial.limitations.length, 2);
  assert.equal(unavailable.availability, "unavailable");
});

test("rejects invalid semantic IDs, values, and incomparable units", () => {
  assert.throws(() => buildComponentInspectorModel(input({ componentId: "  " })), /componentId/);
  assert.throws(() => buildComponentInspectorModel(input({ metricId: "  " })), /metricId/);
  assert.throws(() => buildComponentInspectorModel(input({
    values: {
      baseline: { value: 42, unit: "%" },
      scenario: { value: 48, unit: "fraction" },
      delta: { value: 6, unit: "percentage points" },
    },
  })), /units must match/);
  assert.throws(() => buildComponentInspectorModel(input({
    values: {
      baseline: { value: Number.NaN, unit: "%" },
      scenario: { value: 48, unit: "%" },
      delta: { value: 6, unit: "percentage points" },
    },
  })), /finite/);
  assert.throws(() => buildComponentInspectorModel(input({
    values: {
      baseline: { value: 42, unit: "" },
      scenario: { value: 48, unit: "" },
      delta: { value: 6, unit: "percentage points" },
    },
  })), /unit/);
});
