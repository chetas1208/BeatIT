import assert from "node:assert/strict";
import test from "node:test";
import type { ShadowTrialPair, ShadowTrialResponse } from "@/types/shadow-trial";
import {
  projectComparisonCausalTrace,
  projectPairCausalTrace,
} from "@/lib/twin/comparison/provenance";

function pair(sampleId: string, valid = true): ShadowTrialPair {
  return {
    sample_id: sampleId,
    baseline_twin_id: sampleId,
    scenario_twin_id: "trial-1-scenario-" + sampleId,
    baseline_state: {} as ShadowTrialPair["baseline_state"],
    scenario_state: {} as ShadowTrialPair["scenario_state"],
    baseline_parameters: { afterload_index: 1, preload_index: 0.8 },
    scenario_parameters: { afterload_index: 1.2, preload_index: 0.8 },
    parameters: { afterload_index: 1, preload_index: 0.8 },
    deltas: valid ? { stroke_volume_ml: -4.5, ejection_fraction_pct: -2 } : {},
    delta_units: valid ? { stroke_volume_ml: "mL", ejection_fraction_pct: "percentage_points" } : {},
    valid,
    rejection_reasons: valid ? [] : ["scenario output unavailable"],
  };
}

function response(pairs: readonly ShadowTrialPair[] = [pair("sample-b"), pair("sample-a")]): ShadowTrialResponse {
  return {
    id: "trial-1",
    definition_id: "scenario-1",
    baseline_ensemble_id: "ensemble-1",
    requested_pairs: pairs.length,
    valid_pairs: pairs.filter((item) => item.valid).length,
    invalid_pairs: pairs.filter((item) => !item.valid).length,
    paired_results: [...pairs],
    effect_distributions: [],
    provenance: {
      origin_snapshot_id: "snapshot-1",
      origin_quality: "synthetic",
      origin_provenance: [{ source: "synthetic_replay", evidenceIds: ["fixture-1"] }],
      evidence_ids: ["evidence-b", "evidence-a", "evidence-a"],
      pairing_policy: "same baseline sample identity; no scenario resampling",
      seed: 7,
      physiology_version: "m5.5-physiology-v1",
      ensemble_version: "m5.5-ensemble-v1",
      prior_version: "m5-priors-v1",
      scenario_definition_hash: "sha256:scenario-1",
    },
    warnings: ["simulated warning"],
    status: "complete",
    fingerprint: "sha256:trial-1",
    safety_disclaimer: "Hypothetical simulation only.",
    definition: {
      id: "scenario-1",
      origin_snapshot_id: "snapshot-1",
      baseline_ensemble_id: "ensemble-1",
      scenario: {
        id: "scenario-1",
        label: "Afterload hypothetical",
        origin_snapshot_id: "snapshot-1",
        parameters: [
          { parameter: "preload_index", baseline: 0.8, value: 0.8, delta: 0, unit: "index" },
          { parameter: "afterload_index", baseline: 1, value: 1.2, delta: 0.2, unit: "index" },
        ],
      },
      metrics: ["ejection_fraction_pct", "stroke_volume_ml"],
      created_at: "2026-09-26T00:00:00Z",
      provenance: {},
    },
  };
}

test("projects only authoritative M6 lineage into a stable ordered trace", () => {
  const trace = projectComparisonCausalTrace(response());

  assert.equal(trace.deterministic, true);
  assert.deepEqual(trace.pairIds, ["sample-a", "sample-b"]);
  assert.deepEqual(trace.evidenceIds, ["evidence-a", "evidence-b"]);
  assert.deepEqual(trace.lineage.pairs.map((item) => item.sampleId), ["sample-a", "sample-b"]);
  assert.deepEqual(trace.steps.map((step) => step.kind), [
    "origin_snapshot",
    "baseline_ensemble",
    "scenario_definition",
    "baseline_twin",
    "scenario_twin",
    "paired_comparison",
    "paired_delta",
    "paired_delta",
    "baseline_twin",
    "scenario_twin",
    "paired_comparison",
    "paired_delta",
    "paired_delta",
  ]);

  const scenario = trace.steps.find((step) => step.kind === "scenario_definition");
  assert.deepEqual(
    (scenario?.details.parameters as Array<{ parameter: string }>).map((item) => item.parameter),
    ["afterload_index", "preload_index"],
  );
  assert.ok(!trace.steps.some((step) => step.kind === "paired_delta" && step.parentIds.some((id) => id.includes("afterload"))));
});

test("pair ordering does not affect the deterministic projection and does not mutate input", () => {
  const source = response();
  const before = structuredClone(source);
  const reversed = { ...source, paired_results: [...source.paired_results].reverse() };

  assert.deepEqual(projectComparisonCausalTrace(source), projectComparisonCausalTrace(reversed));
  assert.deepEqual(source, before);
});

test("retains invalid-pair rejection lineage and supports a single-pair projection", () => {
  const invalid = pair("sample-invalid", false);
  const trace = projectComparisonCausalTrace(response([invalid]));
  const comparison = trace.steps.find((step) => step.kind === "paired_comparison");

  assert.deepEqual(trace.pairIds, ["sample-invalid"]);
  assert.equal(comparison?.details.valid, false);
  assert.deepEqual(comparison?.details.rejectionReasons, ["scenario output unavailable"]);
  assert.deepEqual(projectPairCausalTrace(response(), "sample-b").pairIds, ["sample-b"]);
  assert.deepEqual(projectComparisonCausalTrace(response([invalid]), { includeInvalidPairs: false }).pairIds, []);
});

test("fails closed on broken M6 pair identity or origin lineage", () => {
  const brokenPair = { ...pair("sample-a"), baseline_twin_id: "other-sample" };
  assert.throws(() => projectComparisonCausalTrace(response([brokenPair])), /baseline_twin_id/);

  const brokenOrigin = response([pair("sample-a")]);
  brokenOrigin.definition = {
    ...brokenOrigin.definition!,
    scenario: { ...brokenOrigin.definition!.scenario, origin_snapshot_id: "other-snapshot" },
  };
  assert.throws(() => projectComparisonCausalTrace(brokenOrigin), /origin_snapshot_id/);

  const brokenDefinition = response([pair("sample-a")]);
  brokenDefinition.definition = {
    ...brokenDefinition.definition!,
    id: "other-scenario",
  };
  assert.throws(() => projectComparisonCausalTrace(brokenDefinition), /definition\.id/);
});

test("does not manufacture a scenario step when the M6 definition has no parameters", () => {
  const source = response([pair("sample-a")]);
  source.definition = {
    ...source.definition!,
    scenario: { ...source.definition!.scenario, parameters: [] },
  };

  const trace = projectComparisonCausalTrace(source);
  const scenarioStep = trace.steps.find((step) => step.kind === "scenario_definition");
  assert.deepEqual(scenarioStep?.details.parameters, []);
  assert.equal(trace.steps.filter((step) => step.kind === "paired_delta").length, 2);
});
