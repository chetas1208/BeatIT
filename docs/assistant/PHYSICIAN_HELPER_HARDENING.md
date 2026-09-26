# Physician Helper Hardening — Case Context, Personalized Reports, UI Cleanliness

> Standing requirement set, not a wave deliverable — same status as
> `GLOBAL_ARCHITECTURE.md`. Received mid-Wave-6; scheduled to run as a
> dedicated wave (working name: **Wave 6.5**) after Wave 6 integrates and
> before Wave 7 (E2E + Chaos), so Wave 7's end-to-end tests exercise the
> hardened case-aware assistant, not a pre-hardening version.

## The core product rule

**Personalization comes from case state, not from prettier prose.** Two
different cases must never produce the same report with a handful of
numbers swapped — the finding hierarchy, timeline narrative, evidence,
uncertainties, comparisons, and report structure itself must all change
based on what's actually true in that case. The backend can have any number
of routes, tools, models, and orchestration steps — **the physician sees
none of it.**

## Relationship to already-built work (do not rebuild, harden)

This is an extension of Wave 3 (Physician Intelligence), not a replacement:

- `python/hearttwin/assistant/context_resolver.py` (Wave 3) already does
  bare-referent detection ("this"/"here") via `LayaAdapter.needs_clarification`
  and `apply_context_event` for 5 UI event types. This spec's §2-§18 (case
  context stack, reference resolution, case-revision awareness) is a
  **hardening/extension** of this file — add case_id/revision/timeline
  layers to the existing `ConversationContext`, don't build a second context
  system.
- `python/hearttwin/assistant/physician_brief.py` (Wave 3) already builds a
  real `DecisionSupportBundle` (observed/derived/simulated/uncertain/missing/
  assumptions/limitations) from real tool output, with the important
  precedent that `observed_evidence` is honestly `[]` today because no tool
  exposes genuinely-observed (vs. derived) data yet. This spec's §23-§37
  (`CaseReportComposer`, case-specific reports) **extends** this generator —
  the hard case-specificity requirement (§60: materially different reports
  for materially different cases) needs a real content-hierarchy algorithm
  layered on top of the existing bundle, not a new report system.
- `python/hearttwin/assistant/provenance_mapping.py` (Wave 3) already maps 2
  of the real vocabularies (`ValueSource`, `origin_quality`) to a canonical
  `CanonicalProvenanceKind` enum; the other legacy vocabularies are
  confirmed TypeScript-only. This spec's §11-§12 (OBSERVED/DOCUMENTED/
  DERIVED/SIMULATED/MODEL_INFERRED/USER_PROVIDED/UNKNOWN) should **map onto**
  `CanonicalProvenanceKind`, adding DOCUMENTED/MODEL_INFERRED/USER_PROVIDED/
  UNKNOWN as new values only if a real backend data source needs them —
  don't invent a second provenance vocabulary.
- `python/hearttwin/assistant/safety_validator.py`'s `validate_numeric_claims`
  (Wave 2, Unicode-hardened in Wave 5) already does exactly what this spec's
  §33-§34 (`ReportConsistencyValidator`, numeric mismatch = 0 target) asks
  for numbers — extend its checks (unit validation, historical/current
  confusion, negation reversal) rather than building a parallel validator.
- Wave 4's UI work already established the pattern (feature-flagged,
  off-by-default `BeatITCopilotPanel`) this spec's §38-§57 (no backend
  routes/model names/agent names/tool traces in the UI) must audit and
  enforce across — including auditing Wave 4's own new components, which
  were built before this spec arrived and haven't been checked against it.

## Highest-priority, non-negotiable targets (from §62-§65, §98-§101)

1. **Cross-case contamination rate: 0.** Case A's context/evidence/artifacts
   must never appear in Case B's conversation, report, or cache.
2. **Unsupported clinical statement rate: 0** for assertions presented as
   case facts (as opposed to model prose clearly framed as interpretation).
3. **Numeric mismatch rate: 0** for canonical cardiac values against tool
   output — this is `validate_numeric_claims`'s existing job, extended to
   cover reports, not just chat responses.
4. **Template similarity: reports for meaningfully different cases must not
   be near-identical apart from swapped numbers** — the §60 report test
   matrix (5 deliberately different synthetic cases) is the actual test of
   this, not a subjective read.
5. **Zero UI implementation leakage**: no backend routes, HTTP verbs,
   localhost URLs, model/provider names, agent names, tool-call traces, raw
   JSON, internal UUIDs, or debug panels in ordinary physician-facing UI
   (developer/debug surfaces may keep them, isolated behind an explicit
   flag). This includes auditing Wave 4's own components, which predate
   this spec.

## What NOT to do

- Do not build a second chatbot, conversation API, tool registry, or
  provenance model — everything routes through what Waves 2-4 already built
  (`orchestrator.py`, `tool_registry.py`/`physician_tools.py`,
  `CanonicalProvenanceKind`).
- Do not hard-code report narrative templates or prose — §88 is explicit:
  case-narrative logic (e.g. "if EF down AND CO down AND MAP down, emphasize
  worsening hemodynamic pattern") is a real rule evaluated against real
  case data, not a fill-in-the-blank template string.
- Do not fabricate confidence percentages (§93) — matches Wave 5's existing
  rule against treating Laya's raw/uncalibrated probability as clinical
  confidence.
- Do not delete backend routes, APIs, or internal orchestration to satisfy
  the UI-cleanliness rule (§44) — hide them behind the product; developer
  tooling and telemetry stay intact, just isolated from the physician-facing
  surface.

## Scheduled scope for the dedicated wave (5 agents, run after Wave 6 integrates)

Given the full 104-section spec is guidance-and-principle-heavy, not every
section is a discrete deliverable. The wave should target the highest-leverage,
testable subset:

1. **Case Context Hardening Engineer** — extend `ConversationContext`/
   `context_resolver.py` with case_id, case_revision, current_selection
   (component/metric/experiment/artifact), and historical-vs-current
   awareness (§2-§10, §17-§18, §71-§75). Build `ClinicalContextResolver`
   (§16) as a hardening of the existing resolver, not a parallel one.
2. **Report Personalization Engineer** — extend `physician_brief.py` (or a
   sibling module) with real content-hierarchy logic: which findings lead,
   which sections appear/are suppressed, delta-emphasis when a prior
   revision exists (§21, §26-§30, §88). Must produce materially different
   output for materially different synthetic test cases (§60) — this is the
   wave's hardest, most important deliverable.
3. **Report Consistency Validator Engineer** — extend numeric/unit/negation/
   uncertainty/observed-vs-derived-vs-simulated consistency checking (§33-§34,
   §9-§12) on top of `validate_numeric_claims`, not a parallel system.
4. **UI Cleanliness Auditor** — grep the frontend (§81) for leaked backend
   routes, HTTP verbs, localhost URLs, model/provider/agent names, tool
   traces, raw JSON, debug strings — across ALL existing surfaces including
   Wave 4's new `web/components/assistant/*` (built before this spec landed,
   never audited against it) and the two legacy chat surfaces. Fix what's
   safely fixable this wave; document the rest.
5. **Case Isolation & Personalization Test Engineer** — build the §56 context
   test matrix and §60/§61 report test matrix (5 synthetic cases: reduced-EF
   trajectory, preserved-EF/rhythm issue, hemodynamic experiment, incomplete
   data, contradictory measurements) and assert the 4 non-negotiable metrics
   above, especially cross-case contamination = 0.

## Final deliverables (per the spec's §102)

`docs/architecture/PHYSICIAN_HELPER_CONTEXT.md`,
`docs/architecture/CASE_CONTEXT_MODEL.md`,
`docs/architecture/REPORT_PERSONALIZATION.md`,
`docs/ui/PHYSICIAN_HELPER_UI.md`,
`docs/testing/CASE_AWARE_ASSISTANT_TESTS.md`,
`docs/testing/PERSONALIZED_REPORT_TESTS.md` (directories created, empty
pending the dedicated wave), plus implementation and tests under
`python/hearttwin/assistant/` and `web/`.

## Final report format (§103), for whoever integrates this wave

WHAT CHANGED · HOW DOES CASE CONTEXT FLOW INTO THE ASSISTANT · HOW IS THE
CURRENT UI SELECTION RESOLVED · HOW IS HISTORICAL CONTEXT HANDLED · HOW ARE
OBSERVED/DERIVED/SIMULATED FACTS DISTINGUISHED · HOW IS CASE CONTAMINATION
PREVENTED · HOW ARE REPORTS PERSONALIZED · HOW ARE REPORT NUMBERS VALIDATED
· HOW ARE UNSUPPORTED CLAIMS BLOCKED · WHICH INTERNAL UI DETAILS WERE
REMOVED · WHAT REMAINS INTERNAL/DEBUG-ONLY · WHICH CASE TESTS WERE RUN ·
WHICH REPORT TESTS WERE RUN · WHAT FAILED · WHAT REMAINS TO BE IMPROVED.
