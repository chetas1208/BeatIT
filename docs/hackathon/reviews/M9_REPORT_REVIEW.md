# M9 Report Surface Review

Date: 2026-09-26
Scope: `web/components/product/ReportSurface.tsx`,
`web/lib/product/reportContracts.ts`, their focused tests, and the M9 product
state/information-architecture requirements. No production files were changed
by this review.

## Verdict

**OPEN — the report has a useful deterministic presentation scaffold, but it is
not ready to claim an M9 lineage-safe report.** It keeps missing sections
visible and carries a safety disclaimer, yet readiness is inferred from
in-memory booleans rather than verified authority-owned artifacts. The report
can therefore label incomplete, mismatched, or stale descendants as ready and
cannot explain the exact artifact chain behind each section.

## Pass findings

### REP-P1 — The projection is pure and does not calculate physiology

**Pass, bounded.** `buildProductReport` is a pure mapping from its input to a
fixed title, sections, summaries, and limitations
(`web/lib/product/reportContracts.ts:33-58`). `ReportSurface` reads existing
state and delegates report assembly; it does not introduce a second cardiac
calculation (`web/components/product/ReportSurface.tsx:13-36`). This protects
the numerical-authority boundary, although the inputs are not sufficiently
validated for M9 readiness.

### REP-P2 — Basic unavailable sections are retained instead of fabricated

**Pass, limited to the empty boolean case.** When all input presence flags are
false, every section is marked `unavailable`, the summaries state that required
content is missing, and no zero or inferred metric is created
(`web/lib/product/reportContracts.ts:34-51`;
`web/lib/product/__tests__/reportContracts.test.ts:6-21`). The UI also states
that unavailable sections remain visible so missing evidence is not mistaken
for a result (`web/components/product/ReportSurface.tsx:47-47`).

### REP-P3 — A safety boundary is visible and has a fallback

**Pass, with a contract limitation below.** The surface always renders an
educational-simulation warning and the report builder falls back to the
canonical non-diagnosis/non-treatment wording when the supplied disclaimer is
null (`web/components/product/ReportSurface.tsx:42-42`;
`web/lib/product/reportContracts.ts:42-45`). The report limitations also state
that the output is not a diagnosis, treatment plan, or clinical measurement
and that hypothetical results do not replace observed history
(`web/lib/product/reportContracts.ts:53-56`).

## Open findings

### REP-O1 — Readiness is presence-based, not artifact- and context-based

**Severity: P0 deterministic-readiness gap.** The report marks sections ready
from booleans such as `Boolean(state)`, `Boolean(visualization)`,
`Boolean(temporal.timeline)`, and `Boolean(scenario.result ||
scenario.ensemble)` (`web/components/product/ReportSurface.tsx:26-35`). The
builder then converts each boolean directly to `ready` or `unavailable`
(`web/lib/product/reportContracts.ts:33-40`). There is no `LoadState`, request
ID, context key, authority fingerprint, server revision, or status check.

M9 requires a report to be generated only from current, ready,
authority-owned inputs. A populated React object can be from another case,
snapshot, scenario revision, or an in-flight replacement. The current report
has no way to distinguish those conditions from a current ready artifact.

Required gate: compute readiness from the complete current context key and
validated artifact states; reject or expose `stale`, `loading`, and `error`
inputs rather than collapsing them into `ready`/`unavailable`.

### REP-O2 — Descendant prerequisites are not enforced

**Severity: P0 lineage/readiness gap.** The `experiment` section is ready when
either a scenario result *or an ensemble* exists, even though M9 requires a
matching ensemble and immutable scenario definition for the experiment result
(`web/components/product/ReportSurface.tsx:32`; `web/lib/product/contracts.ts:26-29`).
The `evidence` section is ready whenever an ensemble exists
(`web/components/product/ReportSurface.tsx:34`), although M9 requires a
persisted analysis matching the origin, ensemble, target metric, and evidence
request. No `analysisId` or target-specific analysis is read here.

The `comparison` section is ready for any truthy comparison object
(`web/components/product/ReportSurface.tsx:33`); it does not require a
completed valid Shadow Trial, a matching `shadowTrialId`, or a pair whose
ensemble and scenario match the current context. Consequently, the report can
claim evidence or a paired comparison from a weaker ancestor or stale local
object.

Required gate: enforce the M9 dependency chain
`case → origin snapshot → ensemble → scenario → trial/pair → analysis`, with
each child validated against its parent before it contributes to the report.

### REP-O3 — `reportContext` can silently rebind the report to active state

**Severity: P0 context-integrity gap.** `ReportSurface` fills missing
`snapshotId`, `ensembleId`, and `scenarioId` from the currently selected
temporal/scenario objects (`web/components/product/ReportSurface.tsx:20-25`).
This is fallback rebinding, not validation: a context that omitted an ID can
become associated with whichever in-memory object is currently selected. The
fallback also leaves `shadowTrialId`, `pairId`, and `analysisId` untouched, so
the resulting context can mix identifiers from different revisions.

M9 says a report is a deterministic projection of valid references, not a
second source of context, and requires incompatible descendants to be dropped
or shown stale/unavailable. The report must not manufacture a coherent-looking
chain by combining independently selected objects.

Required gate: accept one verified report context, derive a stable context key,
and fail closed when the active objects do not exactly match it. Do not fill
missing descendant IDs from ambient component state.

### REP-O4 — Provenance is a flat list reused for every section

**Severity: P1 provenance/auditability gap.** The surface constructs one list
containing at most the selected snapshot ID, ensemble ID, and pair ID
(`web/components/product/ReportSurface.tsx:35`) and passes that same list to
every section. `buildProductReport` assigns `input.provenance` unchanged to
each section (`web/lib/product/reportContracts.ts:34-40`). The list omits the
scenario, Shadow Trial, and analysis IDs even though they exist in
`BeatITSessionContext` (`web/lib/product/contracts.ts:5-16`).

This makes a timeline section appear sourced by an ensemble or pair, makes an
experiment section appear sourced by a pair without naming its trial/scenario,
and provides no origin quality, observed/derived/simulated/synthetic label,
authority version, fingerprint, timestamp, or lineage relation. The status
legend is only a global legend; it does not attach source status to a report
section (`web/components/product/ReportSurface.tsx:43-45`).

Required gate: use typed, section-specific provenance records containing the
exact artifact IDs and parent links, source classification, authority
version/fingerprint where applicable, and an explicit reason when provenance
is incomplete.

### REP-O5 — Unavailable is conflated with loading, stale, error, and partial

**Severity: P1 safety/UX state gap.** `ReportSectionStatus` declares
`"partial"`, but the builder never emits it; all non-ready paths become
`"unavailable"` (`web/lib/product/reportContracts.ts:3-10,34-40`). The report
has no representation for a request in progress, a stale retained artifact, a
recoverable backend error, unauthorized/missing persisted artifact, or
incomplete evidence coverage.

M9 requires these states to remain distinguishable. In particular, stale data
must not be presented as current, and an error must not silently fall back to a
previous result. The current text “No completed hypothetical experiment is
recorded” can be rendered for a loading or stale context without identifying
what the user must retry or which ancestor is still valid.

Required gate: carry the M9 load state/reason through the report projection and
render actionable, explicit states such as loading, stale, error, and
unavailable. Keep a stale payload out of ready summaries and downstream report
inputs.

### REP-O6 — The safety disclaimer is visible but not canonicalized

**Severity: P1 safety-contract limitation.** The fallback wording is safe, but
any non-null `safetyDisclaimer` is copied through without validation
(`web/lib/product/reportContracts.ts:42-45`). The focused test deliberately
accepts the arbitrary string `"Use for education."`
(`web/lib/product/__tests__/reportContracts.test.ts:24-36`). There is no
contract assertion that an upstream/custom disclaimer preserves the required
non-diagnosis, non-treatment, educational-simulation boundary.

The current surface does not introduce diagnostic or treatment language, so
this is a defensive contract gap rather than evidence of an unsafe string in
the reviewed path. The report should either use the canonical disclaimer
unconditionally or validate supplied text against the safety contract before
rendering it.

### REP-O7 — Report tests cover only boolean happy paths

**Severity: P1 verification gap.** The two focused tests cover all flags false
and one combination of true flags (`web/lib/product/__tests__/reportContracts.test.ts:6-37`).
They do not test mismatched IDs, missing parent artifacts, stale/loading/error
states, section-specific provenance, synthetic versus observed origin labels,
analysis requirements, safety-disclaimer integrity, or deterministic context
keys. A passing test therefore proves only the current boolean mapping, not
M9 report readiness or lineage safety.

Required gate: add contract tests for the full dependency matrix, exact
provenance mapping, fail-closed mismatches, stale/error handling, and canonical
safety text. These tests should be added only when implementation work is
authorized; this review made no production edits.

## Verification evidence

- Static source review completed for `ReportSurface`, `reportContracts`, the
  focused report tests, `AppShell` context construction, and the M9 product
  state/information-architecture documents.
- The attempted focused TypeScript test command could not run because the
  workspace has no resolvable `tsx` package (`ERR_MODULE_NOT_FOUND: Cannot find
  package 'tsx'`). No test pass is claimed for this review.
- No production files were edited. The only intended new file is this review.
