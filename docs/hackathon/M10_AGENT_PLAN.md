# M10 Agent Plan — Final War Room

Last updated: 2026-09-26

M10 is a release-hardening milestone. It adds no scientific method, model
formula, product space, or major visualization. The release commander owns
shared integration, triage, and final acceptance. Each agent has a disjoint
write set and must return evidence; dispatch alone never counts.

| ID | Scope | Owned paths | Dependencies | Deliverable | Started | Completed | Reviewed | Integrated | Rejected | Reason |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | release blocker audit | `docs/hackathon/M10_BLOCKERS.md` | M1-M9 docs | P0/P1/P2/WONTFIX triage |  |  |  |  |  |  |
| 02 | full regression audit | `docs/hackathon/M10_REGRESSION_REVIEW.md` | baseline | cross-milestone failures | 2026-09-26 | 2026-09-26 | yes | yes | no | inherited failures recorded |
| 03 | backend test closure | `python/hearttwin/tests/test_assistant_router.py` | regression | green avoidable failures |  |  |  |  |  |  |
| 04 | frontend test closure | `docs/hackathon/reviews/M10_FRONTEND_RELEASE_REVIEW.md` | M9 | runtime/component checks | 2026-09-26 | 2026-09-26 | yes | yes | no | stale-result/browser open |
| 05 | TypeScript/lint closure | `docs/hackathon/reviews/M10_FRONTEND_RELEASE_REVIEW.md` | M9 | no-cheat gate | 2026-09-26 | 2026-09-26 | yes | yes | no | direct gates pass |
| 06 | server hardware audit | `docs/deploy/SERVER_AUDIT.md` | host inspection | CPU/RAM/GPU/disk/ports | 2026-09-26 | 2026-09-26 | yes | yes | no | deployment limits recorded |
| 07 | container audit | `docs/deploy/CONTAINER_REVIEW.md` | hardware | host/container boundary |  |  |  |  |  |  |
| 08 | compose design | `docker-compose.prod.yml` | container audit | production-ish orchestration |  |  |  |  |  |  |
| 09 | reverse proxy design | `deploy/nginx.conf.example` | compose | proxy/TLS/SSE limits | 2026-09-26 | 2026-09-26 | yes | yes | no | proxy review linked |
| 10 | restart design | `docs/deploy/M10_DEPLOYMENT_REVIEW.md` | compose | restart/recovery procedure | 2026-09-26 | 2026-09-26 | yes | yes | no | public restart open |
| 11 | persistence audit | `docs/deploy/M10_PERSISTENCE_REVIEW.md` | stores | restart durability | 2026-09-26 | 2026-09-26 | yes | yes | no | external restart open |
| 12 | backup/recovery | `docs/deploy/M10_BACKUP_ROLLBACK_REVIEW.md` | persistence | safe backup plan | 2026-09-26 | 2026-09-26 | yes | yes | no | restore drill open |
| 13 | local model inventory | `docs/models/M10_MODEL_REVIEW.md` | model manifest | loadable/optional status | 2026-09-26 | 2026-09-26 | yes | yes | no | live optional models open |
| 14 | language runtime audit | `docs/models/M10_LANGUAGE_RUNTIME.md` | model client | extract/explain fallback |  |  |  |  |  |  |
| 15 | VISTA runtime audit | `docs/models/M10_VISTA_RUNTIME.md` | VISTA docs | optional readiness |  |  |  |  |  |  |
| 16 | model lifecycle | `docs/models/M10_MODEL_LIFECYCLE.md` | model inventory | load/ready/fail/unload |  |  |  |  |  |  |
| 17 | model health | `docs/hackathon/reviews/M10_READINESS_REVIEW.md` | lifecycle | liveness/readiness semantics | 2026-09-26 | 2026-09-26 | yes | yes | no | deployed reachability open |
| 18 | GPU resource audit | `docs/deploy/GPU_RESOURCE_REVIEW.md` | hardware | VRAM/OOM evidence |  |  |  |  |  |  |
| 19 | model failure fallback | `docs/hackathon/reviews/M10_FAILURE_FALLBACK.md` | runtime | model-offline behavior | 2026-09-26 | 2026-09-26 | yes | yes | no | live outage tests open |
| 20 | model performance | `docs/hackathon/reviews/M10_PERFORMANCE_REVIEW.md` | runtime | latency/load evidence | 2026-09-26 | 2026-09-26 | yes | yes | no | capacity envelope open |
| 21 | API reliability | `docs/hackathon/reviews/M10_API_RELIABILITY.md` | API | validation/retry/timeout audit | 2026-09-26 | 2026-09-26 | yes | yes | no | resource limits open |
| 22 | resource protection | `docs/hackathon/reviews/M10_RESOURCE_PROTECTION.md` | API | expensive endpoint protection |  |  |  |  |  |  |
| 23 | caching audit | `docs/hackathon/reviews/M10_CACHING.md` | stores | context-safe caching |  |  |  |  |  |  |
| 24 | concurrency audit | `docs/hackathon/reviews/M10_CONCURRENCY.md` | stores/models | race/OOM/state leakage |  |  |  |  |  |  |
| 25 | security audit | `docs/hackathon/reviews/M10_SECURITY_REVIEW.md` | full tree | secrets/CORS/headers/logs | 2026-09-26 | 2026-09-26 | yes | yes | no | synthetic-only boundary |
| 26 | secret scan | `docs/hackathon/reviews/M10_SECURITY_REVIEW.md` | security | credential-shaped scan | 2026-09-26 | 2026-09-26 | yes | yes | no | no live literals found; broader security open |
| 27 | upload audit | `docs/hackathon/reviews/M10_UPLOAD_REVIEW.md` | API | file validation/path safety | 2026-09-26 | 2026-09-26 | yes | yes | no | public upload gate open |
| 28 | privacy/logging | `docs/hackathon/reviews/M10_DATA_RETENTION_REVIEW.md` | API | safe structured logging | 2026-09-26 | 2026-09-26 | yes | yes | no | retention/auth open |
| 29 | observability | `docs/hackathon/reviews/M10_OBSERVABILITY_REVIEW.md` | health | timing/error/resource status | 2026-09-26 | 2026-09-26 | yes | yes | no | access/retention open |
| 30 | startup dashboard | `docs/hackathon/reviews/M10_READINESS_REVIEW.md` | health | technical status contract | 2026-09-26 | 2026-09-26 | yes | yes | no | deployed semantics open |
| 31 | demo fixture | `fixtures/demo/README.md` | M9 surfaces | canonical deterministic case |  |  |  |  |  |  |
| 32 | demo seeder | `scripts/seed-demo.sh` | fixture | idempotent seed | 2026-09-26 | 2026-09-26 | yes | yes | no | hashes recorded |
| 33 | demo reset | `scripts/reset-demo.sh` | seeder | pristine reset |  |  |  |  |  |  |
| 34 | offline demo | `docs/hackathon/reviews/M10_FAILURE_FALLBACK.md` | fixture | internet/model outage path | 2026-09-26 | 2026-09-26 | yes | yes | no | live outage open |
| 35 | precomputed fallback | `docs/demo/PRECOMPUTED_FALLBACK.md` | fixture | explicit fallback labels |  |  |  |  |  |  |
| 36 | failure injection | `docs/hackathon/reviews/M10_FAILURE_INJECTION.md` | all services | chaos results |  |  |  |  |  |  |
| 37 | browser stress | `docs/hackathon/reviews/M10_BROWSER_STRESS.md` | browser | repeated demo evidence |  |  |  |  |  |  |
| 38 | memory/performance | `docs/hackathon/reviews/M10_MEMORY_PERFORMANCE.md` | frontend | leak/perf evidence |  |  |  |  |  |  |
| 39 | accessibility release | `docs/hackathon/reviews/M10_ACCESSIBILITY.md` | M9 | final keyboard/AT review | 2026-09-26 | 2026-09-26 | yes | yes | no | browser/AT open |
| 40 | cross-browser review | `docs/hackathon/reviews/M10_CROSS_BROWSER.md` | browser | available browser evidence |  |  |  |  |  |  |
| 41 | responsive release | `docs/hackathon/reviews/M10_RESPONSIVE.md` | M9 | final responsive review |  |  |  |  |  |  |
| 42 | scientific integrity | `docs/hackathon/reviews/M10_SCIENTIFIC_INTEGRITY.md` | credibility | language/provenance audit | 2026-09-26 | 2026-09-26 | yes | yes | no | claim gaps recorded |
| 43 | credibility package | `docs/hackathon/reviews/M10_CREDIBILITY.md` | M1-M9 | final credibility audit |  |  |  |  |  |  |
| 44 | reproducibility | `docs/hackathon/reviews/M10_REPRODUCIBILITY.md` | fixture | hashes/replay evidence | 2026-09-26 | 2026-09-26 | yes | yes | no | remote HTTP open |
| 45 | release manifest | `RELEASE_MANIFEST.json` | versions | version inventory | 2026-09-26 | 2026-09-26 | yes | yes | no | consistency gaps recorded |
| 46 | architecture docs | `docs/ARCHITECTURE_FINAL.md` | freeze | final architecture |  |  |  |  |  |  |
| 47 | deployment docs | `docs/release/DEPLOYMENT.md` | deploy | operator procedure |  |  |  |  |  |  |
| 48 | demo script | `docs/demo/DEMO_SCRIPT.md` | fixture | 3-minute runbook | 2026-09-26 | 2026-09-26 | yes | yes | no | rehearsal open |
| 49 | judge Q&A | `docs/demo/JUDGE_QA.md` | credibility | adversarial answers |  |  |  |  |  |  |
| 50 | pitch | `docs/demo/PITCH.md` | demo | sponsor-safe pitch |  |  |  |  |  |  |

## Reviewed contribution register

The following 22 contributions are counted for M10. Each has a disjoint
deliverable, was inspected by the release commander, and includes verification
evidence. A review can pass while its release gate remains open; “reviewed” is
not the same as “all findings closed.”

| Contribution | Scope | Deliverable | Evidence | Disposition |
|---|---|---|---|---|
| A01 | regression | `M10_REGRESSION_REVIEW.md` | clean-baseline comparison and direct gates | Reviewed; inherited failures remain |
| A02 | host hardware | `docs/deploy/SERVER_AUDIT.md` | CPU/RAM/GPU/disk/container audit | Reviewed; deployment limits remain |
| A03 | reproducibility | `M10_REPRODUCIBILITY.md` | seed/reset/hash/idempotence runs | Reviewed; remote HTTP open |
| A04 | model inventory | `docs/models/M10_MODEL_REVIEW.md` | metadata/runtime availability audit | Reviewed; live optional models open |
| A05 | accessibility | `M10_ACCESSIBILITY.md` | direct checks and browser blocker evidence | Reviewed; browser/AT open |
| A06 | security | `M10_SECURITY_REVIEW.md` | secret scan and source audit | Reviewed; synthetic-only |
| A07 | API reliability | `M10_API_RELIABILITY.md` | focused API/SSE tests and route probes | Reviewed; resource limits open |
| A08 | observability | `M10_OBSERVABILITY_REVIEW.md` | trace/readiness/logging audit | Reviewed; access/retention open |
| A09 | backup/rollback | `docs/deploy/M10_BACKUP_ROLLBACK_REVIEW.md` | syntax and safe restore audit | Reviewed; restore drill open |
| A10 | persistence | `docs/deploy/M10_PERSISTENCE_REVIEW.md` | 40 persistence tests and subprocess probe | Reviewed; hosted restart open |
| A11 | deployment | `docs/deploy/M10_DEPLOYMENT_REVIEW.md` | launcher/proxy/rollback review | Reviewed; public deployment open |
| A12 | scientific integrity | `M10_SCIENTIFIC_INTEGRITY.md` | API/UI/provenance language audit | Reviewed; claim gaps open |
| A13 | fallback | `M10_FAILURE_FALLBACK.md` | 61 focused tests and 3 failure probes | Reviewed; live outage tests open |
| A14 | demo claims | `docs/demo/M10_DEMO_REVIEW.md` | implemented-capability and safety review | Reviewed; rehearsal open |
| A15 | reverse proxy | `M10_PROXY_REVIEW.md` | nginx/SSE/upload static assertions | Reviewed; nginx/TLS open |
| A16 | data retention | `M10_DATA_RETENTION_REVIEW.md` | storage/privacy/retention audit | Reviewed; recovery/deletion open |
| A17 | upload security | `M10_UPLOAD_REVIEW.md` | 24 focused tests and adversarial probes | Reviewed; public upload gate open |
| A18 | readiness | `M10_READINESS_REVIEW.md` | TestClient/degraded/preflight probes | Reviewed; deployed semantics open |
| A19 | manifest | `M10_MANIFEST_REVIEW.md` | JSON/path/backend consistency probes | Reviewed; version gaps open |
| A20 | performance | `M10_PERFORMANCE_REVIEW.md` | seed/API/build timing and RSS | Reviewed; capacity/soak open |
| A21 | frontend release | `M10_FRONTEND_RELEASE_REVIEW.md` | product tests, TypeScript, lint, state audit | Reviewed; stale-result/browser open |
| A22 | documentation | `M10_DOCUMENTATION_REVIEW.md` | status/link/ledger consistency audit | Reviewed; reconciled in this ledger |

## Counting rule

An agent counts only when its deliverable is substantive, inspected by the
release commander, and supported by verification evidence. Failed, duplicate,
placeholder, and unreviewed work does not count. Reassignments preserve the
original row and add a new row only when the scope genuinely changes.
