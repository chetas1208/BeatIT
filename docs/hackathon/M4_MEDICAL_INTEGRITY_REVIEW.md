# M4 medical integrity review

**Review date:** 2026-09-26  
**Scope:** Read-only review of M4 formulas, safety language, provenance, and
absence of treatment recommendations. No source files were modified.

## Findings and dispositions

### M4-MI-1 — Formula determinism is present, but the provenance reference is not exact

- **Finding:** M4 propagation is deterministic and unit-labelled, including
  `SV = EDV - ESV`, `EF = SV / EDV × 100`, `CO = HR × SV / 1000`, and
  `RR = 60000 / HR` in `web/lib/twin/scenario/propagation.ts:133-160,164-188`.
  However, the M4 `SOURCE.reference` points to the canonical Python formula
  module at `web/lib/twin/scenario/propagation.ts:52-59`, while M4 also has a
  separate TypeScript bounded relationship for EDV/ESV/MAP at `:148-155`.
  The canonical Python equations and guards are in
  `python/hearttwin/tools/cardiac_state.py:13-41`.
- **Disposition:** **Needs reconciliation before claiming canonical-formula
  reuse.** Keep the current deterministic educational model unchanged for this
  review; either make the source reference explicitly identify the M4 bounded
  model or establish tested delegation to the canonical formulas. This is a
  provenance/contract issue, not evidence of LLM arithmetic.

### M4-MI-2 — M4 safety language blocks diagnostic and treatment framing

- **Finding:** The M4 panel identifies the surface as `HYPOTHETICAL SIMULATION`
  and says observed history is unchanged at
  `web/components/twin/scenario/ScenarioPanel.tsx:22-25`. The inspector states
  that results are not a diagnosis, treatment recommendation, or clinical
  prediction at `web/components/twin/scenario/ScenarioInspector.tsx:114-130`,
  and exported reports repeat the boundary at
  `web/lib/twin/scenario/report.ts:4-15`. The global request/output boundary
  remains enforced by `python/hearttwin/safety.py:12-17,45-68,94-114`.
- **Disposition:** **Accept for M4 medical-integrity review; retain as a release
  gate.** The existing safety-language scan does not enumerate M4 TSX/report
  files (`python/hearttwin/tests/test_safety_language.py:277-316`), so add
  M4-specific coverage before promotion rather than relying only on manual
  inspection.

### M4-MI-3 — Scenario lineage is retained and no treatment recommendation is emitted

- **Finding:** Derived measurements are explicitly marked `source: "derived"`
  with method and evidence text at
  `web/lib/twin/scenario/propagation.ts:164-188`. The origin preserves snapshot
  identity, timestamp, cloned state, provenance, and evidence IDs at
  `:194-203,270-277`; the UI exposes scenario provenance and baseline evidence
  at `web/components/twin/scenario/ScenarioInspector.tsx:206-214`. The report
  explicitly ends with “not a diagnosis or treatment recommendation” at
  `web/lib/twin/scenario/report.ts:14`.
- **Disposition:** **Accept, with preservation required.** M4 outputs remain
  hypothetical derived scenarios, not clinical evidence or treatment plans.
  Do not add medication, dosing, emergency, or patient-specific treatment
  language to the scenario controls, reports, or provenance labels.

**Overall disposition:** M4 passes the reviewed safety and non-treatment
boundary. Formula/source reconciliation and M4-specific safety regression
coverage remain follow-up items before a final medical-integrity sign-off.
