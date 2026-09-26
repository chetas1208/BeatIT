# M10.5 Agent 28 — Offline Demo Verification

**Date:** 2026-09-26 UTC
**Scope:** optional-provider shutdown, deterministic seed, local API demo flow,
and release-demo fixture verification
**Disposition:** **PASS for the isolated offline/local demo path; public
deployment remains unverified**

## Offline boundary

The checks ran with a clean environment and these optional paths explicitly
disabled:

```text
MODEL_ENABLED=false
INTELLIGENCE_PROVIDER=disabled
OPENAI_ENABLED=false
MODEL_API_KEY= MODEL_BASE_URL= MODEL_NAME= OPENAI_API_KEY=
REDIS_URL= HEARTTWIN_REDIS_MEMORY_ENABLED=false
HEARTTWIN_TRACE_MODE=local_only WANDB_API_KEY= WANDB_ENTITY= WANDB_PROJECT=
VISTA3D_ENABLED=false VISTA3D_API_BASE= VISTA3D_API_KEY=
CAREGUARD_ENABLED=false CAREGUARD_VISTA_ENABLED=false LAYA_ENABLED=false
AWS_ENABLED=false BLOB_READ_WRITE_TOKEN=
```

The API probe used temporary SQLite and artifact paths. It did not use Redis,
Weave, OpenAI or generic model providers, VISTA-3D, CareGuard, LAYA, S3, or
blob storage. All inputs were checked-in synthetic demo values.

## Deterministic seed

Command:

```text
./scripts/seed-demo.sh
```

Result:

```text
All fixtures already up to date.
[config] openai_configured=False weave=False redis=False vista3d_enabled=False
[extract] validated_fields=6
[operate] EF=58.3 CO=5.04 has_pv_loop=True
[recovery] scenarios=4
[evaluator] overall_score=0.9
RESULT: OK
DEMO READY
```

The seed wrote the existing synthetic demo state and manifest. No fixture
content changed during this verification.

## API verification

The real FastAPI application was loaded in-process with temporary persistence.
These routes returned HTTP 200 and retained `safety_disclaimer`:

```text
/api/v1/health/live
/api/v1/health/ready
/api/v1/system-check
/api/v1/models/status
/api/v1/intelligence/status
```

Readiness reported the deterministic twin as ready and optional integrations
as degraded or optional. The system check returned `status=ok`, with honest
fallback integration states:

```text
openai=fallback
intelligence=disabled
weave=local_fallback
redis=memory_fallback
vista3d=disabled
checks=10, all ok
```

The demo case flow also passed through the actual API routes:

```text
POST /api/v1/cases
POST /api/v1/cases/{case_id}/extract
POST /api/v1/cases/{case_id}/operate
POST /api/v1/cases/{case_id}/simulate-recovery
GET  /api/v1/cases/{case_id}/harness
```

Observed deterministic outputs:

```text
validated fields: 6
ejection fraction: 58.30%
cardiac output: 5.04 L/min
PV loop: present
recovery scenarios: 4
harness: HTTP 200
Weave enabled: false
Redis configured: false
```

## Demo preflight and fixture integrity

```text
./scripts/demo-preflight.sh
```

```text
READY python
READY node
READY curl
READY demo fixture
READY ensemble golden
READY Shadow Trial golden
READY model manifest
SKIP HTTP checks (E2E_BASE_URL was intentionally unset)
DEMO READY
```

```text
./scripts/verify-demo.sh
```

```text
DEMO FIXTURES PASS
SYNTHETIC DATASET PASS m10.5-demo-v1
FIXTURE COUNT PASS 3
RELEASE GOLDEN PASS m10.5-release-demo-v1
DEMO VERIFY PASS
```

## Result

**PASS** — the deterministic offline demo remains runnable without optional
providers or external services, and fallback status is exposed honestly.

This does not verify browser/WebGL behavior, a public reverse proxy or TLS,
remote deployment, external-provider outage behavior, Redis/PostgreSQL
durability, backup/restore, or deployed restart persistence.

No production or test files were modified by this contribution; only this
release evidence document was created.
