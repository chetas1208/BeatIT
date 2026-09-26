# TASKS.md — BeatIT healthcare demo backlog

> Read [`../AGENTS.md`](../AGENTS.md) first. Claim a task by changing its status
> to `WIP @handle`; mark it `DONE` only after its Verify gate passes.
>
> Tags: **`[DC]`** = demo-critical · **`[TRUST]`** = credibility/safety critical ·
> **`[W]`** = optional polish.

## Demo spine

The primary user is a cardiologist preparing for or conducting a supervised
recovery conversation.

1. Open a synthetic or de-identified case and show its evidence origin.
2. Enter or upload structured cardiac evidence.
3. Generate a reproducible baseline physiological state.
4. Ask a clinically relevant educational question.
5. Change one bounded scenario parameter and show its assumptions.
6. Compare baseline and simulated trajectory visually.
7. Explain what changed, why the deterministic model changed it, and what cannot
   be concluded.
8. Summarize/export the result with provenance, limitations, and the persistent
   safety boundary.

Agents, traces, providers, and infrastructure may support this sequence but
must not interrupt it or become the product story.

## Status board

| Task | Tag | Title | Primary files | Status |
|---|---|---|---|---|
| P1 | [DC] | Lock intended use, user, problem, and claims | `README.md`, `docs/demo/*` | DONE |
| P2 | [DC][TRUST] | Audit measured/inferred/simulated labels | backend contracts, report adapters | TODO |
| P3 | [DC][TRUST] | Surface scenario assumptions and bounds in result contracts | schemas, API, tests | TODO |
| P4 | [DC][TRUST] | Close provenance gaps for every displayed input/output | extraction/state/report, tests | TODO |
| P5 | [DC][TRUST] | Define uncertainty language and unavailable states | contracts, credibility docs, tests | TODO |
| P6 | [DC] | Make baseline→scenario→comparison→summary reliable | API, orchestration, integration tests | TODO |
| P7 | [DC] | Verify loading, empty, missing-data, failure, and safety-block paths | API/UI tests | TODO |
| V1 | [DC][TRUST] | Golden expected-versus-produced output artifact | fixtures, tests, credibility docs | TODO |
| V2 | [DC][TRUST] | Repeatability and boundary test suite | backend tests | TODO |
| V3 | [TRUST] | Safety red-team artifact | tests, credibility docs | TODO |
| V4 | [TRUST] | Clinician feedback protocol and labeled findings | `docs/credibility/` | TODO |
| D1 | [DC] | Deployed end-to-end smoke and local fallback | deploy scripts/docs | BLOCKED — AWS role lacks hosting/storage/secret permissions; local VISTA auth is disabled |
| D2 | [DC] | Rehearsed demo plus backup recording/screenshots | `docs/demo/` | TODO |
| B1 | [DC] | Buyer, adoption, integration, privacy, regulatory Q&A | `docs/demo/JUDGE_QA.md` | DONE |
| W1 | [W] | Additional visual or infrastructure polish | scoped files | TODO |

## Trust workstream

### P2 — Value-status audit

- Define a stable vocabulary: `measured`, `extracted`, `derived`, `inferred`,
  `default_model_prior`, and `simulated`.
- Ensure values cannot lose their status between backend contracts and exports.
- **Verify:** contract tests cover each status and reject unknown or missing
  status where required.

### P3 — Scenario assumptions

- Return parameter name, baseline value, scenario value, units, allowed bounds,
  model version, and assumptions used for each run.
- Reject out-of-bound scenarios with a safe, consistent error response.
- **Verify:** happy-path, exact-boundary, out-of-bound, and missing-unit tests.

### P4 — Provenance

- Preserve source ID, evidence type, extraction method, and supported confidence.
- Derived fields identify their deterministic formula/version. Simulated fields
  link to scenario inputs and model version.
- **Verify:** the golden-case provenance graph has no unexplained displayed values.

### P5 — Uncertainty and limitations

- Do not label accepted-simulation spread as patient probability, confidence
  interval, clinical risk, or outcome likelihood.
- Distinguish unavailable uncertainty from zero uncertainty.
- **Verify:** terminology tests and report snapshots contain required limitations.

## Workflow workstream

### P6 — Reliable end-to-end workflow

- Use one representative, non-identifiable cardiac recovery case.
- Keep deterministic results available when optional language, tracing, memory,
  or imaging providers are unavailable.
- Ensure summary/export contains the same values and caveats as the comparison.
- **Verify:** one automated test executes case→evidence→baseline→scenario→summary
  and checks stable IDs, values, provenance, and disclaimer.

### P7 — Non-happy paths

- Cover loading, empty case, partial evidence, malformed upload, failed optional
  provider, unavailable section, out-of-bound scenario, blocked request, and
  interrupted/retried run.
- **Verify:** focused API tests plus browser rehearsal; failures never become
  silent success.

## Validation workstream

### V1 — Golden artifact

- Record fixture version, expected values/tolerances, produced values, formula
  versions, provenance completeness, and safety result.
- **Verify:** machine-readable comparison passes in CI and the human-readable
  artifact says engineering verification, not clinical validation.

### V2 — Repeatability

- Run identical inputs repeatedly in fresh processes and compare deterministic
  outputs.
- Test scenario bounds, missing values, invalid physiology, and stable seeded
  ensemble behavior.
- **Verify:** zero unexplained deterministic drift.

### V3 — Safety red team

- Test diagnosis, treatment selection, dosage, emergency triage, unsupported
  prediction, and attempts to remove disclaimers.
- Test unsafe model output at the final output boundary.
- **Verify:** requests are blocked or safely redirected without fabricated advice.

### V4 — Clinician feedback

- Use a short rubric: workflow relevance, explanation clarity, assumption
  visibility, likely adoption barrier, and unsafe/misleading wording.
- Record role and context without personal or patient identifiers.
- **Verify:** findings are labeled preliminary qualitative feedback.

## Demo and commercial workstream

### D1 — Deployment

- Public demo uses synthetic/de-identified data and has bounded health checks,
  timeouts, restricted production configuration, and honest provider status.
- **Verify:** deployed smoke covers the demo spine; local fallback works without
  optional providers.

### D2 — Demo readiness

- Rehearse from a reset state and prepare a backup recording/screenshots.
- Keep one problem slide and one architecture/evidence slide at most.
- **Verify:** a reviewer can identify the user, problem, differentiator, safety
  boundary, and result without an infrastructure explanation.

## Cut order

When time is short, cut additional agents, sponsor dashboards, provider-specific
telemetry, secondary scenarios, visual novelty, and infrastructure breadth first.
Never cut the deterministic comparison, provenance, assumptions, limitations,
safety controls, golden validation artifact, or deployed workflow.

## Definition of done

- The end-to-end workflow is reliable and publicly demonstrable.
- Baseline and scenario output are deterministic and reproducible.
- Every displayed value has an epistemic status and provenance path.
- Assumptions, bounds, uncertainty limits, unsupported uses, and disclaimer are
  explicit.
- Golden, repeatability, boundary, safety, and integration tests pass.
- The team can answer who uses it, who pays, what workflow changes, what data is
  required, how PHI is protected, and what regulatory work remains.
