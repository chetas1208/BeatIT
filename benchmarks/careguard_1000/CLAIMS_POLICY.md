# Claims policy

What this benchmark **may** claim:

- Software-behavior comparisons on a research corpus: e.g. "on the silver
  reference set, Arm X detected N% of source-documented allergy conflicts vs M%
  for Arm Y, paired Wilcoxon p = …".
- Operational facts: measured latency, cost, token usage, failure/retry rates.
- Component-contribution statements from ablations, scoped to the ablation
  subset.

What this benchmark **must not** claim:

- Clinical validation, safety, efficacy, or fitness for diagnosis/treatment.
- That all 1,000 cases are "clinically adjudicated ground truth" — they are not
  unless licensed clinicians reviewed them. Use: *source-derived reference
  label*, *silver reference set*, *human-adjudicated gold subset*.
- That Track 2 isolates model intelligence.
- Superiority beyond what the statistics support (report CIs and p-values; do
  not round a non-significant difference up to a claim).

Terminology (required):
`source-derived reference label`, `silver reference set`,
`human-adjudicated gold subset`, `benchmark task`, `trial`, `grader`,
`transcript`, `outcome`, `paired comparison`.

Circular-evaluation prohibitions (enforced by `tests/test_no_data_leakage.py`):

- CareGuard output is never a reference label for CareGuard.
- No model grades its own arm.
- The tested model never sees the expected answers.
- The optional LLM judge is secondary and blinded; it never sets the primary
  result.
- Outputs are never hand-edited before grading; only documented deterministic
  syntax repair is allowed, reported separately.
