# M9 Decisions

- The primary navigation is exactly five spaces: TWIN, EXPERIMENT, COMPARE,
  EVIDENCE, and REPORT.
- Mode URLs contain only a product mode. Patient identifiers, evidence text,
  trial payloads, and metrics stay in memory/API state rather than the URL.
- The existing deterministic backend and M6/M7/M8 projections remain
  authoritative. M9 composes them and does not recalculate physiology.
- The heart stays in the central work surface for Twin, Experiment, and Compare;
  Compare uses the existing paired Split Heart renderer.
- Unavailable analysis is displayed as unavailable. The report never fills a
  missing result with an inferred value.
- Existing telemetry is retained as a secondary run-detail rail for the
  sponsor demo; it is not a sixth primary product space.
- Browser, WebGL, assistive-technology, and machine-specific performance
  evidence remain open until a supported browser environment is available.
