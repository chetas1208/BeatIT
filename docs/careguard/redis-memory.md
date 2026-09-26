# CareGuard Redis Memory

Reuses DualBeat's `redis_client` (standard `REDIS_URL`). All keys are namespaced under
`careguard:*` — existing DualBeat keys are never touched or renamed.

Keys: `careguard:case:{id}:{fhir|context|multimorbidity|guidelines|drug-labels|
contraindications|candidates|simulation|critic|feedback|audit|medication-safety|...}`,
`careguard:run:{id}:{state|lock|stages}`, and shared caches
`careguard:guideline:{source}:{version}:{chunk}`, `careguard:drug-label:{rxcui}:{ver}`.

Used for staged workflow state, idempotency, distributed locks (SET NX EX), approved
guideline/label cache, redacted agent memory, and audit events — all with TTL.

**Never stored:** raw identifiable FHIR bundles, raw notes/reports, raw prompts, model
reasoning, imaging, secrets, or unredacted PHI (audit events are redacted before write).

**Redis unavailable:** a bounded in-process fallback serves the active request only;
`persistence_note()` discloses "not persisted", cross-request memory is disabled, and no
false clinical conclusion is produced. `verify:careguard` and `test_careguard_isolation`
exercise the fallback.
