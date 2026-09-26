import assert from "node:assert/strict";
import test from "node:test";
import {
  M6_HEMODYNAMIC_METRIC_ORDER,
  mapHemodynamicDisplayValue,
  mapHemodynamicDisplayValues,
} from "@/lib/twin/comparison/hemodynamics";

test("maps M6 SV, CO, and MAP with explicit units and neutral numerical directions", () => {
  const values = mapHemodynamicDisplayValues([
    { metricId: "map_mmhg", baseline: 92, scenario: 88, delta: -4, unit: "mmHg" },
    { metricId: "cardiac_output_l_min", baseline: 5.2, scenario: 5.325, delta: 0.125, unit: "L/min" },
    { metricId: "stroke_volume_ml", baseline: 78, scenario: 78.004, delta: 0.004, unit: "mL" },
  ]);

  assert.deepEqual(values.map(({ metricId, baseline, scenario, delta, unit, deltaUnit, domain, direction }) => ({
    metricId,
    baseline,
    scenario,
    delta,
    unit,
    deltaUnit,
    domain,
    direction,
  })), [
    { metricId: "stroke_volume_ml", baseline: 78, scenario: 78.004, delta: 0.004, unit: "mL", deltaUnit: "mL", domain: "volume", direction: "neutral" },
    { metricId: "cardiac_output_l_min", baseline: 5.2, scenario: 5.325, delta: 0.125, unit: "L/min", deltaUnit: "L/min", domain: "flow", direction: "increase" },
    { metricId: "map_mmhg", baseline: 92, scenario: 88, delta: -4, unit: "mmHg", deltaUnit: "mmHg", domain: "pressure", direction: "decrease" },
  ]);
});

test("uses the supplied M6 delta instead of recomputing physiology", () => {
  const display = mapHemodynamicDisplayValue({
    metricId: "stroke_volume_ml",
    baseline: 70,
    scenario: 95,
    delta: 2,
  });

  assert.equal(display.delta, 2);
  assert.notEqual(display.delta, display.scenario! - display.baseline!);
  assert.equal(display.direction, "increase");
  assert.equal(display.directionLabel, "Increase");
});

test("represents missing values without inventing zero or direction", () => {
  const display = mapHemodynamicDisplayValue({
    metricId: "map_mmhg",
    baseline: null,
    scenario: null,
    delta: null,
  });

  assert.equal(display.unit, "mmHg");
  assert.equal(display.valueAvailability, "unavailable");
  assert.equal(display.direction, "unavailable");
  assert.equal(display.directionLabel, "Unavailable");
});

test("keeps the M6 metric order and rejects contradictory units or non-finite values", () => {
  assert.deepEqual(M6_HEMODYNAMIC_METRIC_ORDER, [
    "stroke_volume_ml",
    "cardiac_output_l_min",
    "map_mmhg",
  ]);
  assert.throws(
    () => mapHemodynamicDisplayValue({ metricId: "cardiac_output_l_min", baseline: 5, scenario: 6, delta: 1, unit: "mL" }),
    /does not match L\/min/,
  );
  assert.throws(
    () => mapHemodynamicDisplayValue({ metricId: "map_mmhg", baseline: Number.NaN, scenario: 80, delta: 0 }),
    /baseline must be finite/,
  );
});

