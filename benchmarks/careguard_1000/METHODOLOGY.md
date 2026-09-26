# Methodology

## Question set

1. **Model generation** — does Sonnet 4.6 beat Sonnet 4.5 with identical case
   information and identical prompt (only the model id differs)?
2. **Retrieval** — how much does an authoritative evidence packet improve each
   standalone model over case-only prompting?
3. **System** — does the full CareGuard pipeline beat direct standalone model
   calls on medication-safety review?
4. **Component contribution** — which CareGuard components create the gain
   (ablations)?
5. **Operational viability** — accuracy, reliability, latency, cost.

## Arms

| Arm id | Track | What it is |
|---|---|---|
| `sonnet_45_case_only` | 2 | Sonnet 4.5, canonical packet, no tools/evidence |
| `sonnet_46_case_only` | 2 | Sonnet 4.6, same input/prompt as above |
| `sonnet_45_evidence_grounded` | 1 | Sonnet 4.5 + independent evidence packet |
| `sonnet_46_evidence_grounded` | 1 | Sonnet 4.6 + same evidence packet |
| `careguard_full` | 2 | Full deterministic CareGuard medication-safety engine |
| `careguard_no_critic` | 4 | CareGuard minus safety critic |
| `careguard_no_retrieval` | 4 | CareGuard minus authoritative evidence |
| `careguard_no_multimorbidity` | 4 | CareGuard minus cross-organ reconstruction |
| `careguard_no_deterministic_conflict_engine` | 4 | CareGuard minus deterministic conflict assertions |

**Two tracks (not collapsed into one score).**
- **Track 1 — controlled reasoning:** Arms C and D receive the exact same
  normalized facts, medication identities, and evidence passages. Measures
  evidence interpretation, cross-condition reasoning, unsupported-claim
  avoidance, and abstention quality.
- **Track 2 — end-to-end product:** Arms A/B get the canonical packet; Arm E
  runs the full pipeline from case files. This compares *standalone model
  workflow* vs *full agentic clinical-evidence system*. It does **not** isolate
  model intelligence and is not claimed to.

## Request construction (spec §5)

For the primary comparison the only intended difference between paired arms is
the model id. All arms share: identical output schema (forced tool use),
identical `max_tokens`, identical input preparation, identical system
instructions, identical tool policy. Temperature/top-p/top-k are omitted (both
models run identically); thinking is omitted (both run thinking-off). No hidden
chain-of-thought is stored — only the final structured output plus stop reason,
token counts, latency, request id, error type, and retry count.

**Structured output.** Both Sonnet 4.5 and 4.6 return the common schema through
a single forced tool (`tool_choice = {type: tool}`). This is portable across
both models without depending on `output_config.format`. Responses are
validated against `schemas/benchmark_output.schema.json`; a validation failure
is recorded as a benchmark failure. A deterministic **syntax-only** repair
(drop unknown keys, coerce obvious scalar types) may be attempted; the original
and repaired results are recorded separately and never silently merged. Model
clinical content is never rewritten by another model.

## Reference labels (spec §2 — no circular evaluation)

Primary scoring comes from **source-derived reference labels** built by
`reference/build_reference_set.py` from:

1. deterministic case facts (FHIR + EHR CSVs + provenance),
2. the case's own RxNorm-normalized medication list,
3. the case's own openFDA drug-label evidence (`has_contraindications`,
   contraindication excerpts, boxed warnings),
4. documented allergies matched to active-medication ingredients,
5. multimorbidity / organ-system analysis already computed deterministically.

These are a **silver** reference set (source-derived, not clinician-adjudicated).
A stratified subset is queued for human adjudication (`adjudication_queue.csv`)
to form a **gold** subset. The system's own predictions are never used as
ground truth; no model grades itself; an optional blinded LLM judge is a
secondary qualitative signal only and never determines the primary result.

## Graders

Deterministic set-based graders compute precision/recall/F1 against the
reference for medications, allergy conflicts, contraindication signals, missing
information, and organ systems, plus source-grounding rate, unsupported-claim
rate, abstention quality, and schema-validity rate. See `graders/` and
`config/metrics.yaml`.

## Statistics

Per-arm metrics are aggregated with case-level bootstrap 95% confidence
intervals (`analysis/bootstrap.py`). Paired arms (4.5 vs 4.6; case-only vs
evidence-grounded; direct vs CareGuard) are compared with the Wilcoxon
signed-rank test on per-case scores, with effect sizes (`analysis/paired_tests.py`).
Repeated trials on a stratified subset measure reliability.

## Operational metrics

Median / p95 latency, cost per case, token usage, tool-call count, API-failure
rate, retry rate, structured-output-failure rate, and system-completion rate
are captured per trial and summarized in `analysis/cost_analysis.py` and
`analysis/latency_analysis.py`.
