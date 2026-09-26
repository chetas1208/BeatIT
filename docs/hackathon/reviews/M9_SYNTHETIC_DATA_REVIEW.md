# M9 Synthetic-Data and Lineage Review

Date: 2026-09-26 UTC  
Scope: observed/derived/simulated/prior/synthetic labels; M5.5, M6, and M8
wording; generated reports and shell entrypoints. Read-only audit; the only
file created by this review is this document.

## Verdict

**OPEN — the core lineage policy and canonical ensemble contract are explicit,
but M9 report labeling and the synthetic fallback/report path are not closed.**
The current checked-in cohort is all real eICU source records, while the
application’s cardiac fixtures, plausible-twin outputs, and benchmark baseline
are synthetic or simulated and are generally labeled as such. The remaining
issues are primarily presentation and release-documentation risks: a global
report legend is not section provenance, one generated case-report template
hard-codes a real-source statement, and the shell advertises a fallback path
whose implementation is absent from the invoked pipeline.

## Pass findings

### LIN-P1 — The canonical taxonomy is defined and non-interchangeable

**PASS.** `docs/hackathon/OBSERVED_SYNTHETIC_POLICY.md:7-34` defines
`OBSERVED`, `DERIVED`, `SIMULATED`, `SYNTHETIC`, `INTERPOLATED`, and `PRIOR`
separately. It also states the important boundary that accepted ensemble
samples are simulated, while projected state fields may carry derived source
metadata. This is consistent with the backend request contract:
`python/hearttwin/ensemble.py:77-109` requires explicit
`origin_quality` and rejects synthetic replay provenance labeled `observed`.

### LIN-P2 — Backend provenance preserves prior, source, and derived-output context

**PASS, bounded.** Distribution requests carry source, evidence IDs, rationale,
and version (`python/hearttwin/ensemble.py:31-39`). The canonical projection
marks sampled state values `DERIVED` and records the projection method
(`python/hearttwin/ensemble.py:378-395`). Response provenance retains origin
quality, origin provenance, evidence IDs, physiology/distribution/prior
versions, and the independent-input/percentile limitations
(`python/hearttwin/ensemble.py:416-454`). This supports auditability without
turning a prior or deterministic output into an observation.

### LIN-P3 — Synthetic replay is visible in the active twin surface

**PASS for the reviewed ensemble surface.** The selected-twin UI uses
`PLAUSIBLE SIMULATED TWIN` and adds `synthetic replay origin` when the origin
quality is synthetic (`web/components/twin/ensemble/PlausibleTwinsPanel.tsx:121`).
The timeline also renders a synthetic snapshot as `synthetic replay`
(`web/components/twin/timeline/Timeline.tsx:58`). The retained frontend
provenance tests assert the synthetic origin and warning
(`web/lib/twin/ensemble/__tests__/provenance.test.ts:116-123`).

### LIN-P4 — Fixtures, benchmark inputs, and benchmark reports declare their boundaries

**PASS for the inspected artifacts.** The cardiac fixture README states that
all fixtures are synthetic and non-patient data
(`fixtures/hearttwin/README.md:1-10`). The ensemble benchmark explicitly marks
its fixture, prior, origin quality, and output as synthetic
(`scripts/benchmark_ensemble.py:61-67,100-133,213-230`). The CareGuard report
generator places a research/deidentified/synthetic/composite boundary in every
generated report (`benchmarks/careguard_1000/analysis/generate_report.py:17-23,
45-61`) and identifies its score reference as source-derived silver rather than
system output (`:190-196`).

### LIN-P5 — Current checked-in cohort classification agrees with the dataset report

**PASS for the current snapshot.** `data/cohort/cohort_manifest.json` contains
1,000 rows, all with `source_type: real`; the generated count probe returned
`Counter({'real': 1000})`. `data/FINAL_REPORT.md:9-22` correspondingly reports
zero Synthea/synthetic fallback cases. The data dictionary defines the expected
`real`/`synthetic` manifest field and provenance extension
(`data/DATA_DICTIONARY.md:17-22,71-79`).

### LIN-P6 — Shell entrypoints are syntactically valid and expose lineage counts

**PASS, limited to shell integrity and reporting.** `bash -n` passed for
`data/scripts/run_all.sh`, `data/scripts/imaging/run_imaging_pipeline.sh`,
`benchmarks/careguard_1000/run_core_benchmark.sh`, and
`benchmarks/careguard_1000/run_full_benchmark.sh`. The main data shell prints
real and synthetic-fallback counts and the quality-report path
(`data/scripts/run_all.sh:36-61`); the benchmark shell invokes the report
generator and names its output (`benchmarks/careguard_1000/run_core_benchmark.sh:7-14`).
This proves the reporting hooks exist, not that every fallback or imaging branch
has been executed.

## Open findings

### LIN-O1 — M9 REPORT has a global legend, not section-level lineage

**OPEN — high presentation/credibility risk.** `ReportSurface` displays one
legend containing all five statuses (`web/components/product/ReportSurface.tsx:43-45`),
but each report section receives the same flat list of at most snapshot,
ensemble, and pair IDs (`:20-36,49-54`). The report builder labels the first
section `Observed twin` and marks readiness from booleans
(`web/lib/product/reportContracts.ts:33-51`). It does not attach
observed/derived/simulated/prior/synthetic status, origin quality, or the exact
artifact lineage to the individual section. A reader can therefore see a
`SYNTHETIC` legend without knowing which section is synthetic, while the
“Observed twin” wording can coexist with a simulated/derived descendant.

Required closure: section-specific provenance with exact artifact IDs, source
classification, parent relation, and an explicit unavailable/stale reason.

### LIN-O2 — REPORT readiness can promote weak or mismatched artifacts

**OPEN — P0 context boundary.** The report treats any scenario result or
ensemble as an experiment, and any ensemble as evidence
(`web/components/product/ReportSurface.tsx:26-35`). It does not require the
M9 chain `case → origin snapshot → ensemble → scenario → trial/pair → analysis`
or validate that descendants match the active context. The normative contract
requires those relationships and says stale/mismatched descendants must not be
reported as ready (`docs/hackathon/M9_PRODUCT_STATE.md:87-121,151-180`). This
is a lineage-label issue even when the underlying numerical artifacts are
correct.

### LIN-O3 — The generated patient report hard-codes a real source label

**OPEN — conditional mislabeling risk.** `data/scripts/case_writer.py:134-143`
always emits `Source dataset: ... (real, deidentified ICU stay)` and then calls
the record a composite research case. The manifest writer preserves
`asm.source_type` and `real_patient_data` (`:385-398`), so the report template
can disagree with its machine-readable source metadata if a synthetic fallback
case reaches it. The current cohort has no such rows, so this is not observed
mislabeling in the checked-in output; it is an unclosed fallback-path hazard.

Required closure: branch the report wording from `source_type` and explicitly
identify synthetic/Synthea records as synthetic, non-PHI, and non-patient
evidence.

### LIN-O4 — The advertised synthetic fallback is recorded but not runnable from the main shell

**OPEN — pipeline completeness gap.** `data/scripts/04_select_cohort.py:1-11`
and `:418-428` record `synthetic_shortfall` and
`synthetic_fallback_allowed`, but `data/scripts/run_all.sh:21-34` has no
synthetic fallback/04b stage. A repository file listing also finds no
`04b`/Synthea generator under `data/scripts/`. The current all-real manifest is
consistent with the zero shortfall, but the shell’s “Synthetic fallback cases”
summary is only a count/reporting hook, not evidence that fallback generation,
lineage propagation, and report labeling work end to end.

Required closure: either implement and invoke the fallback stage with manifest,
FHIR, report, and validation labels, or make the documented fallback status
explicitly unsupported rather than an available pipeline branch.

### LIN-O5 — M5.5/M6 completion wording is stale when read as repository status

**OPEN — documentation status drift.** `docs/hackathon/M5_5_COMPLETION.md:7-10`
says “M6 has not started,” and its closing text says no M6/M7/M8 work is
included (`:70-75`), while the repository contains an M6 completion record
describing the paired engine, persistence, API routes, and UI
(`docs/hackathon/M6_COMPLETION.md:7-18`) and M8 is marked complete for Tier-1
scope (`docs/hackathon/M8_COMPLETION.md:1-22`). These statements are defensible
as frozen M5.5 historical scope, but the documents do not consistently signal
that they are historical when surfaced alongside current milestone records.

Required closure: label M5.5 statements as “at M5.5 close” and point to the
current M6/M8 status, without weakening the still-open M5.5 gates.

### LIN-O6 — M6/M8 wording must retain scope qualifiers in reports and UI

**OPEN — claim-boundary maintenance.** M6 is explicitly incomplete and not
ready for M7 (`docs/hackathon/M6_COMPLETION.md:5-11`), while M8 is complete only
for Tier-1 scope and explicitly excludes posterior, probability, confidence
interval, diagnosis, treatment, and clinical-measurement claims
(`docs/hackathon/M8_COMPLETION.md:37-50`). The M9 report currently summarizes
“bounded experiment” and “evidence and uncertainty” without carrying those
scope qualifiers or the M8 heuristic limitation
(`web/lib/product/reportContracts.ts:49-56`). The wording is not an observed
unsafe claim, but it can over-compress a bounded simulation into a generic
“experiment” or “evidence” result.

Required closure: carry milestone scope, simulated/prior origin, heuristic
name, and explicit limitations into report sections and any exported report
format.

### LIN-O7 — M8 performance documentation contains an internal contradiction

**OPEN — evidence labeling issue.** `docs/hackathon/M8_PERFORMANCE.md:3-4`
records a narrow local probe and says it is not a hosted-capacity claim; the
same document includes measured sample-count rows. However, the M9 inherited
status audit records a stale statement that no M8 benchmark was recorded
(`docs/hackathon/M9_PREFLIGHT.md`, M8 completion-audit section). The M8
completion also correctly says browser/WebGL and machine-specific performance
signoff remain blocked (`docs/hackathon/M8_COMPLETION.md:44-48`). Until the
stale statement is reconciled, reports must not present the local probe as an
SLO, capacity result, or browser-performance validation.

## Verification record

Commands run from `/home/923873155/BeatIT`:

```text
bash -n data/scripts/run_all.sh
bash -n data/scripts/imaging/run_imaging_pipeline.sh
bash -n benchmarks/careguard_1000/run_core_benchmark.sh
bash -n benchmarks/careguard_1000/run_full_benchmark.sh
  PASS — all four shell entrypoints

python manifest count probe
  PASS — 1,000 rows; source_type_counts = {'real': 1000}
```

No production code, fixture, shell script, report output, or prior review was
edited. No browser, deployment, or patient-data validation is claimed.

## Disposition

The taxonomy and canonical backend/fixture boundaries pass. M9 lineage review
remains **OPEN** until LIN-O1/O2 are addressed in the report contract, and the
fallback/report status is either made executable and label-safe (LIN-O3/O4) or
explicitly narrowed. M5.5/M6/M8 records should be treated as scoped milestone
evidence, not interchangeable current-status claims.
