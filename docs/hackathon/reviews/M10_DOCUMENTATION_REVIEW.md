# M10 Contribution A27 — Release Documentation Review

Date: 2026-09-26 UTC  
Scope: release-document completeness and stale M9/M10 status language  
Disposition: **OPEN — documentation gate not closed; do not ship**

## Review method

This is a read-only audit of the release-facing documentation, milestone
ledgers, cross-document links, and status statements in the current working
tree. It does not change product behavior or normalize historical records.
The current release authority is `docs/hackathon/M10_COMPLETION.md`, together
with `docs/release/RELEASE_CHECKLIST.md` and `docs/hackathon/M10_WAR_ROOM.md`.

## What is present

The repository contains the expected categories of M10 handoff material:

- scope freeze, baseline, blockers, completion, and test matrix;
- deployment, rollback, failure-mode, and known-limitation records;
- architecture, release manifest, demo script, pitch, and judge Q&A;
- model, security, reliability, observability, accessibility, upload,
  reproducibility, retention, proxy, and scientific-integrity reviews.

These documents consistently preserve the educational/synthetic boundary and
the final **DO NOT SHIP** decision. The release checklist also leaves public
deployment, persistence restart, browser, chaos, security, and repeated demo
gates unchecked.

## Findings

| ID | Severity | Finding | Evidence | Release impact |
|---|---|---|---|---|
| DOC-01 | P0 | The top-level deployment guidance still presents a Vercel Python serverless backend as the primary deployment. M10's final architecture and deployment record instead require the exercised path to be a loopback FastAPI/Next process behind nginx or Caddy; the public reverse-proxy path is not yet exercised. | `README.md:144-146`; `docs/deployment-vercel.md:5-15`; `docs/ARCHITECTURE_FINAL.md:31-35`; `docs/deploy/DEPLOYMENT.md:3-6` | An operator can select a deployment path that M10 explicitly has not release-verified and that conflicts with the documented trace-flush/persistence boundary. Public release instructions are therefore ambiguous. |
| DOC-02 | P1 | The M10 agent ledger is a scaffold rather than an auditable completion ledger. All 50 rows have blank lifecycle fields, while 32 of the 50 referenced deliverable paths do not resolve under their planned names (excluding the one valid glob pattern). Several completed reviews use different names from the plan, such as `M10_SECURITY_REVIEW.md` versus the planned `M10_SECURITY.md`. | `docs/hackathon/M10_AGENT_PLAN.md:3,10-61`; current `docs/hackathon/reviews/M10_*` inventory | The requested reviewed-contribution gate cannot be independently reconstructed from the canonical ledger. Completed work may exist, but it must not be counted as integrated until row ownership, evidence, review, and disposition are recorded. |
| DOC-03 | P1 | M9 status records disagree with one another. M9 completion says at least 20 substantive reviewed contributions were recorded, while the M9 agent plan still marks many rows, including the test matrix and completion auditor, as `planned`. M9 preflight also says every plan entry is still planned and that current M9 tests/files are absent. | `docs/hackathon/M9_COMPLETION.md:42-48`; `docs/hackathon/M9_AGENT_PLAN.md:27-58`; `docs/hackathon/M9_PREFLIGHT.md:26-33,173-179` | Readers cannot determine which M9 gates are historical observations, current open work, or accepted completion evidence. M10 inherits those gates and must not treat either count as authoritative without reconciliation. |
| DOC-04 | P1 | `Progress.md` contains forward-looking instructions that are stale in the current milestone: it says not to start M9/M10/M10.5, while the same file later records M9 work and an active M10 final war room with an M10 **INCOMPLETE — DO NOT SHIP** decision. | `Progress.md:72-79,98-114,148-165` | The progress page gives contradictory instructions to the next operator and can cause work to be resumed at the wrong milestone. The current M10 decision is clear, but the document is not safe as a standalone status source. |
| DOC-05 | P1 | M10's war-room evidence ledger is still an instruction to append evidence rather than an evidence index. The completion report lists the work at a high level, but does not link each review, command result, owner, or unresolved gate to a single ledger entry. | `docs/hackathon/M10_WAR_ROOM.md:29-34`; `docs/hackathon/M10_COMPLETION.md:11-26` | Review completeness and final-candidate provenance require manual reconstruction across directories. This weakens the release handoff and prevents a reviewer from distinguishing a tested claim from a planned or documentation-only claim. |
| DOC-06 | P1 | M10 plan links are not path-stable. The plan names `docs/release/DEPLOYMENT.md`, but the operator document is at `docs/deploy/DEPLOYMENT.md`; it also names multiple planned model, security, demo, chaos, and performance records that do not exist at those paths. | `docs/hackathon/M10_AGENT_PLAN.md:18-61`; `docs/deploy/DEPLOYMENT.md:1`; missing-path check from the current tree | Broken links and renamed deliverables make the release package appear more complete than its navigable evidence actually is. |
| DOC-07 | P1 | Test totals are not reconciled across M10 records. The baseline records `1231 passed`, the final matrix and completion record report `1233 passed`, and the regression review records both `1231 passed` and a repeatable `1126 passed` result. None of these entries states which run supersedes the others or supplies one canonical command/result link. | `docs/hackathon/M10_BASELINE.md:3,29`; `docs/hackathon/M10_TEST_MATRIX.md:5-7`; `docs/hackathon/M10_COMPLETION.md:13-20`; `docs/hackathon/M10_REGRESSION_REVIEW.md:20` | A release reviewer cannot identify the final regression result from documentation alone. The numbers must remain qualified as run-specific until one final command, environment, timestamp, and result is declared authoritative. |
| DOC-08 | P2 | Historical boundary language is not consistently marked at the point of use. Statements such as “M10 and M10.5 are out of scope,” “M10 is not started,” and “M9/M10/M10.5 were not started” are valid for earlier plans or snapshots but are easy to read as current status beside active M10 records. | `docs/hackathon/M9_AGENT_PLAN.md:11`; `docs/hackathon/M9_COMPLETION.md:63-64`; `docs/hackathon/M8_COMPLETION.md:50`; `Decisions.md:164-166` | Historical decisions can be mistaken for current authorization or progress. This is a documentation clarity risk rather than evidence that those earlier milestones were completed. |

## Required documentation closure

Before an M10 release candidate can be called documented and reviewable, the
release commander should make the following updates in the owning documents:

1. Select one current deployment authority and mark the older Vercel-backend
   instructions as historical, superseded, or explicitly supported with the
   M10 limitations.
2. Reconcile `M10_AGENT_PLAN.md` with actual deliverable names. Fill lifecycle
   fields only for work that has substantive evidence and a review disposition;
   do not count missing, duplicate, or documentation-placeholder rows.
3. Add a dated “historical snapshot” banner to retained M9/M8 records whose
   planned/out-of-scope statements are no longer current, while preserving
   their original findings.
4. Replace the stale `Progress.md` next-actions text and link it directly to
   the M10 completion record and release checklist.
5. Turn the M10 war-room evidence ledger into an index of commands, artifacts,
   reviewers, unresolved gates, and the final decision.
6. Correct broken plan paths and reconcile the Python test totals to one
   explicitly identified final run. Keep the baseline and regression snapshots
   labelled as historical when they are not the final run.

## Final assessment

The release package is materially present and communicates the correct safety
boundary and **DO NOT SHIP** decision. It is not documentation-complete:
deployment instructions conflict, the M10 ledger is not populated, M9/M10
historical language is stale in multiple places, and test evidence is not
reconciled to one canonical run. This contribution therefore records **OPEN**
for documentation and does not authorize public deployment or patient-data
use.
