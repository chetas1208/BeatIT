import assert from "node:assert/strict";
import test from "node:test";
import {
  createComparisonSignalContext,
  createPairedSignalContext,
  hasComparisonSignal,
} from "@/lib/twin/comparison/signals";

test("preserves an observed waveform and its provenance without mutation", () => {
  const waveform = [0.1, -0.2, 0.4];
  const context = createComparisonSignalContext({
    source: "observed",
    waveform,
    sampleRateHz: 500,
    lead: "II",
    unit: "mV",
    sourceId: "ecg-file-1",
    method: "csv_waveform",
    confidence: 0.9,
  });

  waveform[0] = 99;
  assert.equal(context.availability, "available");
  assert.equal(context.source, "observed");
  assert.deepEqual(context.waveform, [0.1, -0.2, 0.4]);
  assert.equal(context.sampleRateHz, 500);
  assert.equal(context.lead, "II");
  assert.equal(context.label, "ECG · observed");
  assert.equal(hasComparisonSignal(context), true);
  assert.equal(Object.isFrozen(context.waveform), true);
});

test("keeps extracted and simulated samples visibly distinct", () => {
  const extracted = createComparisonSignalContext({
    source: "extracted",
    waveform: [1, 2],
    sourceId: "report-1",
  });
  const simulated = createComparisonSignalContext({
    source: "simulated",
    waveform: [3, 4],
    method: "provided educational replay",
  });

  assert.equal(extracted.label, "ECG · extracted");
  assert.equal(simulated.label, "ECG · simulated");
  assert.notEqual(extracted.source, simulated.source);
  assert.equal(hasComparisonSignal(extracted), true);
  assert.equal(hasComparisonSignal(simulated), true);
});

test("does not synthesize a waveform from a simulated source without samples", () => {
  const context = createComparisonSignalContext({
    source: "simulated",
    sampleRateHz: 500,
    reason: "Only HR-derived timing is available.",
  });

  assert.equal(context.availability, "missing");
  assert.equal(context.source, "missing");
  assert.equal(context.waveform, null);
  assert.equal(context.sampleRateHz, null);
  assert.equal(context.reason, "Only HR-derived timing is available.");
  assert.equal(hasComparisonSignal(context), false);
});

test("missing, empty, and non-finite signals remain unavailable", () => {
  for (const input of [
    {},
    { source: "observed" as const, waveform: [] },
    { source: "extracted" as const, waveform: [0, Number.NaN] },
  ]) {
    const context = createComparisonSignalContext(input);
    assert.equal(context.availability, "missing");
    assert.equal(context.source, "missing");
    assert.equal(context.waveform, null);
  }
});

test("rejects contradictory missing-source input instead of relabeling it", () => {
  assert.throws(
    () => createComparisonSignalContext({ source: "missing", waveform: [0, 1] }),
    /cannot contain waveform samples/,
  );
});

test("pairs baseline and scenario independently and reports coverage only", () => {
  const context = createPairedSignalContext({
    baseline: { source: "observed", waveform: [0, 1], lead: "II" },
    scenario: { source: "simulated", waveform: [2, 3] },
  });

  assert.equal(context.coverage, "both");
  assert.deepEqual(context.baseline.waveform, [0, 1]);
  assert.deepEqual(context.scenario.waveform, [2, 3]);
  assert.notEqual(context.baseline.source, context.scenario.source);
  assert.equal(Object.isFrozen(context), true);
});

test("does not claim a paired signal when one side is missing", () => {
  const context = createPairedSignalContext({
    baseline: { source: "observed", waveform: [0, 1] },
    scenario: { source: "missing", reason: "No scenario ECG was supplied." },
  });

  assert.equal(context.coverage, "baseline_only");
  assert.equal(context.scenario.waveform, null);
  assert.equal(hasComparisonSignal(context.scenario), false);
});

