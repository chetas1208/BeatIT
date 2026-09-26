# M5.5 Agent Plan — Probabilistic Twin Closure

Last updated: 2026-09-26

## Scope

M5.5 closes the credibility and integration gaps around plausible cardiac twins.
The Python backend is the sole numerical authority. This milestone includes
durable local ensemble persistence, explicit observed/synthetic lineage,
canonical contracts and golden vectors, frontend API consumption, uncertainty
visualization, Python 3.13 and frontend validation, and release documentation.

M6, M7, and M8 are explicitly out of scope. No clinical calibration, Bayesian
posterior claim, patient probability, treatment recommendation, or diagnostic
feature is introduced.

## Coordination rules

- The lead reviews every contribution before it is counted as meaningful.
- Agents own only the files listed for their workstream; shared files are edited
  by the lead after receiving recommendations.
- An agent counts only when it returns concrete evidence: a reviewed patch,
  test, fixture, audit, or release artifact tied to this milestone.
- A stopped, duplicate, speculative, or unverified response is recorded but not
  counted toward the 20-contribution gate.

## Workstreams

| ID | Workstream | Primary scope | Dependency |
|---|---|---|---|
| 1 | Numerical authority audit | Python/TypeScript formula and rounding audit | none |
| 2 | Canonical contract design | Backend response/request schema review | none |
| 3 | Durable persistence design | Existing storage seam and SQLite proposal | none |
| 4 | Persistence implementation | Ensemble store and restart behavior | 3 |
| 5 | API contract implementation | Typed response validation and error behavior | 2 |
| 6 | Golden vector authoring | Fixed and sampled canonical fixtures | 1, 2 |
| 7 | Golden vector verification | Python fixture tests | 6 |
| 8 | Frontend contract adapter | API types and response mapping | 2 |
| 9 | Frontend API integration | Plausible twin UI consumes backend results | 5, 8 |
| 10 | Legacy computation quarantine | Remove active frontend numerical path | 1, 9 |
| 11 | Synthetic/observed policy | Lineage policy and machine-readable fields | 2 |
| 12 | Policy enforcement | API/UI labels and tests for lineage | 11 |
| 13 | PV uncertainty envelope | Honest envelope/representative-loop behavior | 8, 9 |
| 14 | Component uncertainty inspector | Component-level uncertainty UX | 8, 9 |
| 15 | Python 3.13 repair | Async test/runtime compatibility | none |
| 16 | Frontend runtime harness | Alias-aware runtime test command | none |
| 17 | Frontend runtime tests | Contract and adapter tests | 16 |
| 18 | Full frontend lint repair | Existing lint errors without rule weakening | none |
| 19 | Backend regression verification | Full and focused Python suites | 4, 5, 15 |
| 20 | Frontend regression verification | TypeScript/build/lint/runtime checks | 9, 16, 18 |
| 21 | Browser QA | Local browser availability and manual gate | 9, 13, 14 |
| 22 | Accessibility QA | Keyboard, labels, announcements, narrow layout | 9, 14 |
| 23 | Credibility manifest | Machine-readable model/contract manifest | 1, 2, 11 |
| 24 | Credibility documentation | Human-readable limitations and evidence | 23 |
| 25 | Security/privacy review | Persistence, inputs, logs, secrets | 4, 5 |
| 26 | Performance review | Storage and ensemble timing evidence | 4, 5 |
| 27 | Adversarial numerical review | Failure modes and false-confidence audit | 1, 9, 13 |
| 28 | Release gate review | M5.5 completion decision and remaining blockers | all |

## Dispatch ledger

| # | Agent/workstream | Status | Evidence reviewed | Counted |
|---:|---|---|---|---|
| 1 | 01a0dcd0-a453 — Python 3.13 async repair | complete | `asyncio.run` repair; affected tests and full-suite report | yes |
| 2 | 01a0dcd0-a486 — canonical response contract | complete | Pydantic response models and contract tests | yes |
| 3 | 01a0dcd0-a4e6 — frontend runtime harness | complete | alias loader and 2 runtime tests | yes |
| 4 | 01a0dcd0-a4b5 — frontend lint repair | complete | lint 0 errors, 2 warnings; TypeScript pass | yes |
| 5 | 01a0dcd0-a425 — durable SQLite store | complete | restart/atomicity/security tests | yes |
| 6 | 01a0dcd2-467 — numerical authority audit | complete | Python/TypeScript formula, RNG, rounding, shape audit | yes |
| 7 | 01a0dcd9-4047 — synthetic lineage audit | complete | replay quality and LIVE-label audit | yes |
| 8 | 01a0dcdb-1a9f — credibility artifact audit | complete | version, provenance, safety, and claim audit | yes |
| 9 | 01a0dce0-f7cb — API wire-contract audit | complete | snake_case, provenance, safety, and identifier review | yes |
| 10 | 01a0dce3-01eb — PV uncertainty audit | complete | scalar-only envelope and held-baseline-shape review | yes |
| 11 | 01a0dce4-79cf — uncertainty UX/accessibility audit | complete | loading, labels, responsive, timeline, and component review | yes |
| 12 | 01a0dce6-a248 — security/privacy audit | complete | SQL, permissions, PII, CORS, and runtime-validation review | yes |
| 13 | 01a0dce9-1b61 — performance audit | complete | sample scaling, payload, SQLite, and event-loop measurements | yes |
| 14 | 01a0dceb-51cc — backend regression audit | complete | full suite, focused suite, offload and contract review | yes |
| 15 | 01a0dced-7c0f — frontend regression audit | complete | stale async state, build, lint, runtime review | yes |
| 16 | 01a0dcf0-51bf — release-documentation audit | complete | docs contradiction and scope review | yes |
| 17 | 01a0dcf2-3b2e — browser/accessibility environment audit | complete | browser/tool availability and gate wording | yes |
| 18 | 01a0dcf3-a919 — golden-vector audit | complete | fixture, reproducibility, and precision review | yes |
| 19 | 01a0dcf5-4e3a — adversarial numerical review | complete | identity, lineage, rejection, bounds, and active-import review | yes |
| 20 | 01a0dcf8-c1fd — final release gate review | complete | current gates, evidence, and M6 scope review | yes |

The lead will append one row per actual dispatch and will not claim the 20-agent
gate until at least 20 rows contain reviewed, non-duplicative evidence.

## Gate checklist

- [ ] Python owns all canonical sampling, physiology propagation, rejection,
  statistics, rounding, and provenance calculations.
- [ ] Ensemble retrieval survives process restart through the configured local
  persistence provider.
- [ ] Backend request/response contracts and golden vectors are versioned.
- [ ] Frontend renders backend results and does not run a competing ensemble.
- [ ] Observed versus synthetic lineage is explicit and cannot be visually
  confused.
- [ ] PV uncertainty and component uncertainty are either implemented from
  real canonical data or explicitly bounded as unavailable.
- [ ] Python 3.13 suite and frontend lint/runtime gates have evidence.
- [ ] Browser and accessibility checks are run or recorded as environment
  blockers; no unsupported completion claim is made.
- [ ] Credibility manifest and documentation are published in-repo.
- [ ] M6 remains not started.
