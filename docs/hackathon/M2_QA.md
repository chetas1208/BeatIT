# BeatIT M2 QA

Agent 10 owns the deterministic M2 integration checks under
`web/lib/heart/__tests__/`.

## Coverage

| Area | Deterministic checks |
| --- | --- |
| Registry | Unique component IDs; chamber, valve, electrical, functional, and AHA-17 counts |
| AHA and coronary mapping | AHA segment lookup; LAD/LCX/RCA lookup; case-normalized `lcx`; finding-ID resolution; unknown territory behavior |
| Selection | Select, hover, focus, mode derivation, clear operations, and complete reset |
| Picking | Nested semantic parent lookup, event lookup, and cycle termination |
| Patient binding | Measured metrics, localized findings, related state, availability, and unsupported missing values |
| Provenance | Extracted, directly observed, derived, and unavailable evidence paths |
| Reports | Anatomy/patient separation, metric sections, safety notice, unknown component behavior |
| Missing data | Null state, null findings, empty metrics, explicit limitations, and no fabricated values |

Fixtures use fixed timestamps, IDs, values, confidence, source names, and random seeds. No clock, random number generator, network, browser, or patient data is used.

## Files

- `web/lib/heart/__tests__/fixtures.ts` — reusable deterministic cardiac state and finding fixtures.
- `web/lib/heart/__tests__/registry-and-selection.test.ts` — registry, AHA/territory, picking, and interaction checks.
- `web/lib/heart/__tests__/patient-report.test.ts` — binding, provenance, report, safety, and missing-data checks.

## Validation

Focused lint passes:

```text
./node_modules/.bin/eslint lib/heart/__tests__ --max-warnings=0
exit=0
```

The repository has no configured frontend test runner or TypeScript test execution script. The tests use the Node standard `node:test` and `node:assert/strict` APIs so they do not add dependencies; they are included in the existing TypeScript project and are type-checked with it.

Full frontend type-check now passes. The inherited CareGuard type debt was repaired by using the canonical store `caseId` and adding a typed packaged-bundle loader to the API client.

No diagnostics were reported for the new M2 QA files before the existing CareGuard diagnostics.

The existing backend suite was also run:

```text
664 passed, 1 skipped, 10 failed
```

All ten failures are pre-existing Python 3.13 event-loop compatibility failures in `test_evaluator_agent.py` and `test_validator_agent.py` (`asyncio.get_event_loop()` raises after the test suite has closed the loop). The M2 QA changes are TypeScript tests and fixtures only; they do not touch the backend.

## Blockers

1. Add or authorize a TypeScript test runner if executable frontend test runs are required. No dependency was added within this bounded QA task.
2. Add a frontend test runner if executable TypeScript test runs are required; the tests are currently type-checked but not wired to a repository script.

No production source files were changed by Agent 10.
