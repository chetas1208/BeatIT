import type {
  CardiacFinding,
  CardiacFindings,
  CardiacTwinState,
  MeasuredValue,
  PatientContext,
} from "@/types/heart";

export function measured(value: number, unit: string, source: MeasuredValue["source"] = "user_input"): MeasuredValue {
  return { value, unit, source, confidence: 0.94, source_file_id: "fixture-case" };
}

export function createFixtureState(overrides: Partial<CardiacTwinState> = {}): CardiacTwinState {
  const patientContext: PatientContext = { age_years: measured(52, "years") };
  return {
    case_id: "fixture-case",
    created_at: "2026-09-26T00:00:00Z",
    data_quality_score: 0.94,
    safety_level: "clear",
    patient_context: patientContext,
    measurements: {
      ejection_fraction_pct: measured(48, "%"),
      stroke_volume_ml: measured(72, "mL"),
      cardiac_output_l_min: measured(5.2, "L/min"),
    },
    electrophysiology: {
      rhythm_label: "sinus rhythm",
      rr_interval_ms: measured(833, "ms"),
      qrs_duration_ms: measured(96, "ms"),
      qtc_ms: measured(420, "ms"),
    },
    hemodynamics: {
      preload_index: measured(0.8, "index"),
      afterload_index: measured(1.1, "index"),
      contractility_index: measured(0.72, "index"),
      filling_pressure_index: measured(0.6, "index"),
    },
    tissue_state: {
      scar_fraction: measured(0.12, "fraction"),
      inflammation_index: measured(0.2, "index"),
      oxygen_delivery_index: measured(0.9, "index"),
      myocardial_oxygen_demand_index: measured(0.7, "index"),
    },
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
        recovery_horizon_days: 14,
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
        max_safe_parameter_shift: 0.1,
        uncertainty_penalty_weight: 0.1,
        target_metric: "balanced",
      },
      random_seed: 7,
    },
    source_map: [
      { field: "measurements.ejection_fraction_pct", unit: "%", source: "file_extraction", source_file_id: "echo-001", confidence: 0.91, method: "fixture extraction", evidence: "Synthetic fixture value" },
      { field: "hemodynamics.contractility_index", unit: "index", source: "derived", confidence: 0.82, evidence: "Synthetic deterministic derivation" },
    ],
    warnings: [],
    ...overrides,
  };
}

export function createFixtureFinding(overrides: Partial<CardiacFinding> = {}): CardiacFinding {
  return {
    id: "regional_scar",
    title: "Regional scar signal",
    region: "anterior",
    territory: "LAD",
    aha_segments: [1, 17],
    anchor: { x: 0.1, y: 0.2, z: 0.3 },
    severity: "moderate",
    summary: "Synthetic regional finding for deterministic QA.",
    metric: "scar_fraction",
    codes: [],
    source: "deterministic_fixture",
    educational: true,
    ...overrides,
  };
}

export function createFixtureFindings(findings: CardiacFinding[] = [createFixtureFinding()]): CardiacFindings {
  return {
    findings,
    imaging_source: "synthetic fixture",
    segment_model: "AHA-17",
    disclaimer: "Educational simulation only; not a diagnosis or treatment recommendation.",
    model: "fixture-model",
  };
}
