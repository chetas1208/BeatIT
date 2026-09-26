import assert from "node:assert/strict";
import test from "node:test";
import {
  buildComparisonDeltas,
  buildDisplayDifference,
  buildDisplayDifferences,
  buildMetricDelta,
  buildMetricDeltas,
  getDifferencePolicy,
} from "@/lib/twin/comparison/differences";
import type { ShadowTrialPair } from "@/types/shadow-trial";

function pair(
  deltas: Partial<ShadowTrialPair["deltas"]>,
  options: {
    valid?: boolean;
    baseline?: number;
    scenario?: number;
    deltaUnits?: Record<string, string>;
  } = {},
): Pick<ShadowTrialPair, "valid" | "deltas"> & Partial<ShadowTrialPair> {
  const baseline = options.baseline ?? 10;
  const scenario = options.scenario ?? 99;
  return {
    valid: options.valid ?? true,
    deltas,
    delta_units: options.deltaUnits,
    baseline_state: {
      measurements: { ejection_fraction_pct: { value: baseline } },
    },
    scenario_state: {
      measurements: { ejection_fraction_pct: { value: scenario } },
    },
  } as Pick<ShadowTrialPair, "valid" | "deltas"> & Partial<ShadowTrialPair>;
}

test("maps backend deltas in stable order with metric-specific display units", () => {
  const differences = buildDisplayDifferences(
    pair({
      map_mmhg: -2.5,
      cardiac_output_l_min: 0.125,
      ejection_fraction_pct: 2,
      heart_rate_bpm: 4,
    }),
  );

  assert.deepEqual(
    differences.map(({ metricId, delta, unit, direction, kind }) => ({
      metricId,
      delta,
      unit,
      direction,
      kind,
    })),
    [
      { metricId: "ejection_fraction_pct", delta: 2, unit: "percentage points", direction: "positive", kind: "percentage_points" },
      { metricId: "cardiac_output_l_min", delta: 0.125, unit: "L/min", direction: "positive", kind: "absolute" },
      { metricId: "heart_rate_bpm", delta: 4, unit: "bpm", direction: "positive", kind: "absolute" },
      { metricId: "map_mmhg", delta: -2.5, unit: "mmHg", direction: "negative", kind: "absolute" },
    ],
  );
  assert.equal(differences[0]?.displayValue, "+2.00 percentage points");
  assert.equal(differences[1]?.displayValue, "+0.125 L/min");
});

test("uses metric-specific neutral thresholds and omits near-zero display rows", () => {
  const cases: Array<{
    metricId: Parameters<typeof buildMetricDelta>[1];
    tolerance: number;
  }> = [
    { metricId: "ejection_fraction_pct", tolerance: 0.01 },
    { metricId: "cardiac_output_l_min", tolerance: 0.001 },
    { metricId: "pv_loop_area_index", tolerance: 0.001 },
  ];

  for (const { metricId, tolerance } of cases) {
    assert.equal(buildMetricDelta(pair({ [metricId]: tolerance }), metricId), null);
    assert.equal(buildMetricDelta(pair({ [metricId]: -tolerance }), metricId), null);
    assert.equal(buildMetricDelta(pair({ [metricId]: tolerance * 1.01 }), metricId)?.absoluteDelta, tolerance * 1.01);
    assert.equal(buildMetricDelta(pair({ [metricId]: -tolerance * 1.01 }), metricId)?.absoluteDelta, -tolerance * 1.01);
  }
});

test("EF distinguishes percentage points from baseline-relative percent", () => {
  const difference = buildMetricDelta(
    pair({ ejection_fraction_pct: 2 }, { baseline: 55, scenario: 57 }),
    "ejection_fraction_pct",
  );

  assert.ok(difference);
  assert.equal(difference.unit, "percentage points");
  assert.equal(difference.absoluteDelta, 2);
  assert.equal(difference.relativeDelta, (2 / 55) * 100);
  assert.equal(difference.absoluteSemantics, "counterfactual_minus_baseline");
  assert.equal(difference.relativeSemantics, "percent_change_from_baseline");
  assert.equal(buildDisplayDifference(pair({ ejection_fraction_pct: 2 }), "ejection_fraction_pct")?.displayValue, "+2.00 percentage points");
});

test("never recomputes a delta from cardiac state values", () => {
  const difference = buildMetricDelta(
    pair({ ejection_fraction_pct: 2 }, { baseline: 10, scenario: 99 }),
    "ejection_fraction_pct",
  );

  assert.equal(difference?.absoluteDelta, 2);
  assert.notEqual(difference?.absoluteDelta, 89);
  assert.equal(difference?.relativeDelta, 20);
});

test("comparison rows copy values but retain the DTO delta as authority", () => {
  const [difference] = buildComparisonDeltas(
    pair({ ejection_fraction_pct: 2 }, { baseline: 10, scenario: 99 }) as ShadowTrialPair,
  );

  assert.deepEqual(difference, {
    id: "ejection_fraction_pct",
    label: "Ejection fraction",
    baseline: 10,
    scenario: 99,
    delta: 2,
    valueUnit: "%",
    deltaUnit: "percentage points",
    direction: "increase",
    changed: true,
  });
});

test("valid no-op pairs produce no display rows and do not mutate the DTO", () => {
  const input = pair({
    ejection_fraction_pct: 0,
    stroke_volume_ml: 0,
    cardiac_output_l_min: 0,
    heart_rate_bpm: 0,
  });
  const before = structuredClone(input);

  assert.deepEqual(buildDisplayDifferences(input), []);
  assert.deepEqual(buildMetricDeltas(input), []);
  assert.deepEqual(input, before);
});

test("missing, invalid, and non-finite deltas are unavailable rather than zero", () => {
  assert.deepEqual(
    buildDisplayDifferences(pair({ ejection_fraction_pct: 2 }), ["stroke_volume_ml"]),
    [],
  );
  assert.deepEqual(buildDisplayDifferences(pair({ ejection_fraction_pct: 0 }, { valid: false })), []);
  assert.deepEqual(buildDisplayDifferences(pair({ ejection_fraction_pct: Number.NaN })), []);
});

test("rejects a DTO unit that contradicts the metric policy", () => {
  assert.throws(
    () => buildMetricDelta(
      pair({ ejection_fraction_pct: 2 }, { deltaUnits: { ejection_fraction_pct: "%" } }),
      "ejection_fraction_pct",
    ),
    /does not match/,
  );
});

test("policies expose the M6 units and neutral thresholds", () => {
  assert.deepEqual(getDifferencePolicy("ejection_fraction_pct"), {
    label: "Ejection fraction",
    unit: "percentage points",
    neutralTolerance: 0.01,
    kind: "percentage_points",
    decimalPlaces: 2,
  });
  assert.equal(getDifferencePolicy("stroke_volume_ml").unit, "mL");
  assert.equal(getDifferencePolicy("stroke_volume_ml").neutralTolerance, 0.01);
  assert.equal(getDifferencePolicy("cardiac_output_l_min").neutralTolerance, 0.001);
  assert.equal(getDifferencePolicy("pv_loop_area_index").unit, "index");
});
