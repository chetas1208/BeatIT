import assert from "node:assert/strict";
import test from "node:test";
import type { TwinSnapshot } from "@/lib/twin/time/contracts";
import { createFixtureState } from "@/lib/heart/__tests__/fixtures";
import { propagateScenario } from "@/lib/twin/scenario/propagation";

function snapshot(): TwinSnapshot {
  const state = createFixtureState();
  return {
    id: "snapshot-m4-1",
    timestamp: state.created_at,
    state,
    evidenceIds: ["fixture:evidence"],
    changedFields: [],
    provenance: [{ source: "clinical_record", sourceId: "fixture" }],
    quality: "observed",
  };
}

test("scenario propagation isolates observed state and preserves origin", () => {
  const source = snapshot();
  const original = structuredClone(source.state);
  const { result, propagation } = propagateScenario(source, [
    { parameter: "heart_rate_bpm", value: 72 },
    { parameter: "preload_index", value: 0.65 },
    { parameter: "afterload_index", value: 0.575 },
    { parameter: "contractility_index", value: 0.65 },
    { parameter: "systemic_vascular_resistance_index", value: 0.55 },
  ], "scenario-test");

  assert.equal(result.definition.origin.snapshotId, source.id);
  assert.equal(result.scenario.scenarioId, "scenario-test");
  assert.notEqual(result.scenario.state, source.state);
  assert.deepEqual(source.state, original);
  assert.equal(propagation.deterministic, true);
  assert.equal(propagation.status, "complete");
  assert.ok(propagation.paths.length > 0);
});

test("afterload increase reduces stroke volume in the bounded model", () => {
  const source = snapshot();
  const base = propagateScenario(source, [
    { parameter: "heart_rate_bpm", value: 72 },
    { parameter: "preload_index", value: 0.55 },
    { parameter: "afterload_index", value: 0.5 },
    { parameter: "contractility_index", value: 0.65 },
    { parameter: "systemic_vascular_resistance_index", value: 0.55 },
  ], "baseline").result;
  const scenario = propagateScenario(source, [
    { parameter: "heart_rate_bpm", value: 72 },
    { parameter: "preload_index", value: 0.55 },
    { parameter: "afterload_index", value: 0.575 },
    { parameter: "contractility_index", value: 0.65 },
    { parameter: "systemic_vascular_resistance_index", value: 0.55 },
  ], "afterload").result;
  const baseSv = base.scenario.state.measurements.stroke_volume_ml?.value ?? 0;
  const scenarioSv = scenario.scenario.state.measurements.stroke_volume_ml?.value ?? 0;
  assert.ok(scenarioSv < baseSv);
});
