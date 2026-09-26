import assert from "node:assert/strict";
import test from "node:test";
import { getComponentEvidence } from "@/lib/heart/evidence";
import { getAnatomyKnowledge } from "@/lib/heart/knowledge";
import {
  buildComponentReport,
  buildPatientComponentState,
  buildPatientComponentStates,
  getPatientComponentState,
} from "@/lib/heart/patient";
import { createFixtureFinding, createFixtureFindings, createFixtureState, measured } from "./fixtures";

test("patient binding preserves measured values, source provenance, and localized findings", () => {
  const state = createFixtureState();
  const findings = createFixtureFindings();
  const leftVentricle = getPatientComponentState("left-ventricle", { state, findings });
  assert.ok(leftVentricle);
  assert.equal(leftVentricle.statusLabel, "observed");
  assert.deepEqual(leftVentricle.metrics.map((metric) => metric.label), ["Contractility index", "Afterload index", "Stroke volume"]);
  assert.equal(leftVentricle.metrics[0]?.value, "0.72 index");
  assert.equal(leftVentricle.evidence.find((item) => item.id === "source:hemodynamics.contractility_index")?.kind, "derived");
  assert.equal(leftVentricle.findings.length, 0);

  const segment = buildPatientComponentState(
    // The fixture finding targets both AHA segments; segment 1 is the direct registry match.
    // The component is read from the public registry through this stable ID.
    { id: "aha-01", category: "myocardial_segment", displayName: "AHA segment 01", anatomy: { description: "fixture" }, geometry: {}, physiologyBindings: ["scar_fraction"], evidenceBindings: [], findingBindings: ["aha-01"], ahaSegment: 1, coronaryTerritory: "LAD", supportsSelection: true, supportsHover: true, supportsFocus: true, supportsUncertainty: true, supportsDifferenceMode: true },
    { state, findings },
  );
  assert.equal(segment.findings.length, 1);
  assert.equal(segment.statusLabel, "derived");
  assert.equal(segment.available, true);
});

test("patient binding preserves direct, extracted, derived, and unavailable evidence kinds", () => {
  const state = createFixtureState({
    measurements: { ejection_fraction_pct: measured(50, "%", "user_input") },
    source_map: [
      { field: "measurements.ejection_fraction_pct", unit: "%", source: "file_extraction", source_file_id: "echo-002", confidence: 0.88 },
    ],
  });
  const report = buildComponentReport("contraction", { state, findings: null });
  assert.ok(report);
  assert.equal(report.patientState.statusLabel, "insufficient_evidence");
  assert.equal(report.patientState.metrics.length, 0);
  assert.match(report.patientState.limitations[0] ?? "", /No patient-specific/);

  const electrical = buildPatientComponentState(
    { id: "fixture-electrical", category: "electrical", displayName: "Fixture electrical", anatomy: { description: "fixture" }, geometry: {}, physiologyBindings: ["rhythm_label"], evidenceBindings: [], findingBindings: [], supportsSelection: true, supportsHover: true, supportsFocus: true, supportsUncertainty: true, supportsDifferenceMode: true },
    { state: createFixtureState({ source_map: [] }), findings: null },
  );
  assert.equal(electrical.metrics[0]?.sourceKind, "unavailable");
});

test("report separates anatomy from patient state and retains safety language", () => {
  const report = buildComponentReport("left-ventricle", { state: createFixtureState(), findings: createFixtureFindings() });
  assert.ok(report);
  assert.equal(report.component.id, "left-ventricle");
  assert.ok(report.knowledge.primaryFunction.length > 0);
  assert.ok(report.sections.some((section) => section.id === "hemodynamics"));
  assert.match(report.safetyNotice, /not a diagnosis/i);
  assert.equal(buildComponentReport("does-not-exist", { state: null, findings: null }), undefined);
});

test("missing patient state is explicit and does not fabricate values", () => {
  const input = { state: null, findings: null };
  const state = getPatientComponentState("left-ventricle", input);
  assert.ok(state);
  assert.equal(state.available, false);
  assert.equal(state.statusLabel, "insufficient_evidence");
  assert.deepEqual(state.metrics, []);
  assert.match(state.limitations[0] ?? "", /No CardiacTwinState/);
  assert.deepEqual(buildPatientComponentStates(input).find((entry) => entry.componentId === "left-ventricle")?.metrics, []);
  assert.deepEqual(getComponentEvidence("left-ventricle", null), []);
  assert.equal(getAnatomyKnowledge("unknown-component").name, "Unknown component");
});

test("AHA and coronary findings are linked without matching unrelated findings", () => {
  const findings = createFixtureFindings([
    createFixtureFinding({ id: "aha-01", aha_segments: [1], territory: "LAD" }),
    createFixtureFinding({ id: "inferior-signal", aha_segments: [3], territory: "RCA" }),
  ]);
  const segment = getPatientComponentState("aha-01", { state: null, findings });
  assert.ok(segment);
  assert.deepEqual(segment.findings.map((finding) => finding.id), ["aha-01"]);
  const lad = getPatientComponentState("lad", { state: null, findings });
  assert.ok(lad);
  assert.deepEqual(lad.findings.map((finding) => finding.id), ["aha-01"]);
  const rca = getPatientComponentState("rca", { state: null, findings });
  assert.ok(rca);
  assert.deepEqual(rca.findings.map((finding) => finding.id), ["inferior-signal"]);
});
