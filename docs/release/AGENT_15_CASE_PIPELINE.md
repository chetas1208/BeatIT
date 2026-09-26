# M10.5 Agent 15 — Backend Case Pipeline Verification

**Scope:** exercise the real backend case pipeline from case creation through
extraction, operation, simulated recovery, trace retrieval, and harness
retrieval using the checked-in synthetic baseline fixture.

**Date:** 2026-09-26 UTC

**Disposition:** **PASS for the isolated local case-pipeline route contract;
OPEN for harness evaluation aggregation.**

## Isolation and safety boundary

- The probe used `fixtures/hearttwin/manual_baseline.json`.
- Redis, Weave, OpenAI, and S3 were disabled through empty environment values.
- Artifacts used a temporary directory that was removed automatically.
- No repository data, fixtures, databases, services, credentials, or
  production code were modified.
- The case used synthetic educational notes and baseline vitals only.

## Executed verification

The API was exercised through FastAPI's `TestClient`, not by calling pipeline
functions directly. The one-shot probe performed this sequence:

```text
POST /api/v1/cases
POST /api/v1/cases/{case_id}/extract
POST /api/v1/cases/{case_id}/operate
POST /api/v1/cases/{case_id}/simulate-recovery
GET  /api/v1/cases/{case_id}/trace
GET  /api/v1/cases/{case_id}/harness
```

The probe also submitted an unsafe create request containing a diagnosis
request and asserted that the safety guard rejected it.

## Results

| Surface | Result | Evidence |
| --- | --- | --- |
| Create | PASS | HTTP 200; case ID and disclaimer returned |
| Extract | PASS | HTTP 200; status `extracted`; 6 validated fields |
| Operate | PASS | HTTP 200; status `operated`; deterministic baseline metrics matched |
| Recovery | PASS | HTTP 200; 4 bounded scenario records and simulation note returned |
| Trace | PASS | HTTP 200; 60 trace records with stages, tools, evaluation, start, and finish events |
| Harness stages | PASS | HTTP 200; 9 stage results and trace counts returned |
| Safety disclaimer | PASS | Success responses included the canonical educational disclaimer |
| Unsafe request boundary | PASS | Diagnosis-requesting create returned HTTP 422 |

## Deterministic baseline evidence

The operation state exposed the expected provenance-bearing measurements:

| Metric | Expected fixture | Observed |
| --- | ---: | ---: |
| Stroke volume | 70.0 ml | 70.0 ml |
| Ejection fraction | 58.33% | 58.3333% |
| Cardiac output | 5.04 L/min | 5.04 L/min |

The state contained **23 source-map entries**. Every non-null measurement
checked in the response carried `value`, `unit`, `source`, and `confidence`.
The fixture SHA-256 was:

```text
1e448677700a64058df5038dd60f8f5a6516dc2df9bff5eb5e71f6fbd335b5ca
```

## Trace and harness evidence

The trace endpoint returned these event kinds:

```text
agent_stage, eval_scores, run_finish, run_start, tool_call
```

The local trace fallback was correctly reported as not configured for Weave;
this probe makes no public Weave claim.

The harness endpoint returned stage results and trace counters, but its
`eval_scores` object was empty even though the operation/recovery responses and
trace records contained evaluation data. This is an integration gap in the
harness projection, not a failure of the underlying evaluator.

## Verification command

The evidence above came from an inline Python probe run from the repository
root with a temporary artifact root. It completed with exit code 0 and printed
only route statuses, deterministic metrics, counts, fixture hash, and the
open finding; no secret values or patient data were printed.

## Risks and release boundary

- This verifies the isolated in-process/local fallback path only.
- Redis-backed case persistence, external artifact storage, public deployment,
  reverse proxy behavior, restart recovery, and browser rendering remain
  separate release gates.
- The empty harness `eval_scores` projection should be repaired and reverified
  before claiming the harness is a complete evaluation surface.
- The results do not support clinical, diagnostic, or treatment claims.
