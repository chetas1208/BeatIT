# Benchmark card

| | |
|---|---|
| **Name** | CareGuard 1,000-Case Medication-Safety Benchmark |
| **Version** | 1.0 |
| **Task** | Structured medication-safety review of a single case |
| **Corpus** | ~1,000 composite cases (eICU-CRD Demo EHR + PTB-XL ECG + EchoNet echo), de-identified open data |
| **Units** | case-level predictions → deterministic grading vs source-derived labels |
| **Models under test** | `claude-sonnet-4-5-20250929`, `claude-sonnet-4-6` (Models-API verified) |
| **System under test** | HeartTwin CareGuard deterministic medication-safety engine |
| **Reference** | silver (source-derived) + queued human-adjudicated gold subset |
| **Primary graders** | deterministic set metrics (P/R/F1) + grounding / unsupported-claim / abstention rates |
| **Secondary** | optional blinded LLM judge (off by default; never sets primary) |
| **Stats** | case-level bootstrap 95% CI; paired Wilcoxon; repeated-trial reliability |
| **Operational** | latency (median/p95), cost/case, tokens, tool calls, failure/retry/schema-failure rates |
| **Cost cap** | $500, explicit confirmation required |
| **Not** | a clinical-validation study; not for diagnosis/treatment |

## Arms

`sonnet_45_case_only`, `sonnet_46_case_only`, `sonnet_45_evidence_grounded`,
`sonnet_46_evidence_grounded`, `careguard_full`, `careguard_no_critic`,
`careguard_no_retrieval`, `careguard_no_multimorbidity`,
`careguard_no_deterministic_conflict_engine`.

## Intended comparisons

- **4.6 vs 4.5** (case-only; evidence-grounded) — model generation effect.
- **evidence-grounded vs case-only** (each model) — retrieval effect.
- **CareGuard vs direct models** — system effect (Track 2, not model-isolating).
- **full vs each ablation** — component contribution.

## Known failure modes measured

schema/structured-output failure, API failure, over-assertion without evidence,
missed allergy/contraindication signals, poor abstention, latency/cost spikes.
