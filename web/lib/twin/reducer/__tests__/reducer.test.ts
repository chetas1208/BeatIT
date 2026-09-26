import assert from "node:assert/strict";
import test from "node:test";
import type { CardiacTwinState } from "@/types/heart";
import type { TwinEvent } from "@/lib/twin/time/contracts";
import {
  createWearablePayloadHook,
  reduceTwinEvent,
  reduceTwinEvents,
} from "@/lib/twin/reducer";

function measured(value: number, unit = "bpm") {
  return { value, unit, source: "user_input" as const, confidence: 0.9 };
}

function createState(): CardiacTwinState {
  return {
    case_id: "fixture-case",
    created_at: "2026-09-26T00:00:00.000Z",
    data_quality_score: 0.8,
    safety_level: "caution",
    patient_context: { age_years: null },
    measurements: { heart_rate_bpm: measured(70) },
    electrophysiology: { rhythm_label: "sinus rhythm" },
    hemodynamics: {},
    tissue_state: {},
    operating_environment: {
      mode: "rest",
      simulation_duration_seconds: 10,
      time_step_ms: 10,
      activity_level_mets: 1,
      hydration_index: 1,
      sleep_recovery_index: 1,
      stress_catecholamine_index: 0,
      ambient_temperature_c: 22,
      altitude_m: 0,
      oxygen_fraction: 0.21,
      data_uncertainty_policy: "conservative",
      missing_value_policy: "null",
    },
    simulation_config: {
      operating: {
        mode: "rest",
        simulation_duration_seconds: 10,
        time_step_ms: 10,
        activity_level_mets: 1,
        hydration_index: 1,
        sleep_recovery_index: 1,
        stress_catecholamine_index: 0,
        ambient_temperature_c: 22,
        altitude_m: 0,
        oxygen_fraction: 0.21,
        data_uncertainty_policy: "conservative",
        missing_value_policy: "null",
      },
      recovery: {
        recovery_horizon_days: 7,
        scenario_type: "stability_monitoring",
        contractility_delta_per_day: 0,
        afterload_delta_per_day: 0,
        preload_delta_per_day: 0,
        inflammation_decay_rate: 0,
        oxygen_delivery_delta_per_day: 0,
        stiffness_delta_per_day: 0,
        scar_remodeling_rate: 0,
        heart_rate_adaptation_rate: 0,
        arrhythmia_stability_delta: 0,
        max_safe_parameter_shift: 0,
        uncertainty_penalty_weight: 0,
        target_metric: "stability",
      },
      random_seed: 1,
    },
    source_map: [],
    warnings: [],
  };
}

function event(
  id: string,
  type: TwinEvent["type"],
  payload: unknown,
  evidenceIds: string[] = [],
): TwinEvent {
  return {
    id,
    timestamp: "2026-09-26T01:00:00.000Z",
    type,
    source: type === "wearable_sample" ? "wearable" : "clinical_record",
    payload,
    provenance: { source: type === "wearable_sample" ? "wearable" : "clinical_record", evidenceIds },
  };
}

test("reduces explicit nested measurement updates without mutating input", () => {
  const initial = createState();
  const nextMeasurement = measured(74);
  const result = reduceTwinEvent(
    initial,
    event("echo-1", "measurement", {
      path: "measurements.heart_rate_bpm",
      value: nextMeasurement,
    }, ["source-echo-1"]),
  );

  assert.equal(initial.measurements.heart_rate_bpm?.value, 70);
  assert.equal(result.state.measurements.heart_rate_bpm?.value, 74);
  assert.notStrictEqual(result.state.measurements.heart_rate_bpm, nextMeasurement);
  assert.deepEqual(result.changes[0], {
    path: "measurements.heart_rate_bpm",
    previousValue: measured(70),
    nextValue: measured(74),
    reason: "new_evidence",
    evidenceIds: ["echo-1", "source-echo-1"],
  });
});

test("applies explicit update batches without deriving unrelated fields", () => {
  const initial = createState();
  const result = reduceTwinEvent(initial, event("batch-1", "clinical_evidence", {
    updates: [
      { path: "measurements.heart_rate_bpm", value: measured(76) },
      { path: "electrophysiology.rhythm_label", value: "review required" },
    ],
  }));

  assert.equal(result.changes.length, 2);
  assert.equal(result.state.measurements.heart_rate_bpm?.value, 76);
  assert.equal(result.state.electrophysiology.rhythm_label, "review required");
  assert.equal(result.state.hemodynamics.contractility_index, undefined);
});

test("replays in order and records derivation versus observation", () => {
  const result = reduceTwinEvents(createState(), [
    event("m-1", "measurement", { path: "measurements.heart_rate_bpm", value: measured(72) }),
    event("d-1", "state_update", { path: "data_quality_score", value: 0.85 }),
  ]);

  assert.equal(result.state.measurements.heart_rate_bpm?.value, 72);
  assert.equal(result.state.data_quality_score, 0.85);
  assert.equal(result.changes[0]?.reason, "new_evidence");
  assert.equal(result.changes[1]?.reason, "deterministic_derivation");
  assert.equal(result.events[1]?.state.data_quality_score, 0.85);
});

test("wearable payload hooks map only declared fields", () => {
  const hooks = createWearablePayloadHook({ heartRate: "measurements.heart_rate_bpm" });
  const result = reduceTwinEvent(
    createState(),
    event("wear-1", "wearable_sample", { heartRate: measured(81), unknownMetric: 999 }, ["device-1"]),
    { wearablePayloadHooks: hooks },
  );

  assert.equal(result.state.measurements.heart_rate_bpm?.value, 81);
  assert.deepEqual(result.changes[0]?.evidenceIds, ["wear-1", "device-1"]);
  assert.equal("unknownMetric" in result.state, false);
});

test("unknown wearable payloads are safe no-ops and duplicate values are not logged", () => {
  const initial = createState();
  const noOp = reduceTwinEvent(initial, event("wear-2", "wearable_sample", { vendorField: 1 }));
  const duplicate = reduceTwinEvent(initial, event("m-2", "measurement", {
    path: "measurements.heart_rate_bpm",
    value: measured(70),
  }));

  assert.notStrictEqual(noOp.state, initial);
  assert.deepEqual(noOp.state, initial);
  assert.deepEqual(duplicate.changes, []);
});

test("rejects prototype-polluting and out-of-state paths", () => {
  const initial = createState();
  assert.throws(
    () => reduceTwinEvent(initial, event("bad-1", "state_update", { path: "__proto__.polluted", value: true })),
    /Unsafe or invalid Twin state path/,
  );
  assert.throws(
    () => reduceTwinEvent(initial, event("bad-2", "state_update", { path: "patient_context.__proto__", value: true })),
    /Unsafe or invalid Twin state path/,
  );
  assert.throws(
    () => reduceTwinEvent(initial, event("bad-3", "state_update", { path: "not_a_state_field.value", value: true })),
    /outside CardiacTwinState/,
  );
  assert.equal((Object.prototype as { polluted?: boolean }).polluted, undefined);
});
