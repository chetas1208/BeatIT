# Failure Modes and Degradation

| Failure | Expected behavior | Evidence status |
|---|---|---|
| Language model unavailable | deterministic core and safe clarification/fallback remain available | code/tests pass; live kill test open |
| VISTA unavailable | procedural semantic heart remains available; imaging capability is optional | documented; live kill test open |
| Internet unavailable | local fixtures and deterministic computation remain available | in-process smoke passed; network isolation open |
| Backend restart | launcher restarts processes; durable artifact recovery depends on configured store | launcher exists; full restart evidence open |
| Database/Redis unavailable | explicit degraded/error state; no fake ready claim | readiness contract exists; fault injection open |
| Slow request | bounded client/model/API timeouts should return safe error/fallback | source audit; load evidence open |
| Invalid upload | request validation and artifact boundaries reject unsafe input | existing tests; final upload audit open |

Fallback results must carry their existing synthetic/precomputed labels. A
fallback is never presented as a fresh computation.
