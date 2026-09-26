# M10 Failure and Fallback Review

**Contribution:** A14<br>
**Scope:** optional language, Weave, Redis, VISTA-3D, and internet-off behavior<br>
**Review date:** 2026-09-26 UTC<br>
**Production-code changes:** none<br>
**Disposition:** **PASS for the synthetic deterministic fallback path; OPEN for
configured-provider outage, network-isolation, and deployed persistence tests.**

## Executive finding

The deterministic cardiac pipeline can run without an external language model,
Weave credentials, Redis, VISTA-3D, or internet access. The fallback outputs are
labelled as fallback/local/disabled and do not replace missing measurements with
invented clinical values. Laya routing falls back to deterministic heuristics;
language-model stages use the existing deterministic agent logic; Weave retains
local sanitized traces; unconfigured Redis uses process-local storage; and
VISTA returns a warning-carrying disabled/unavailable/failed result rather than
fabricating a segmentation.

This is not a blanket production-resilience pass. The repository has multiple
intentional contracts for a configured-but-broken Redis connection: core case
storage surfaces the Redis error, while non-critical evaluator/memory writes
are best-effort and return failure. A configured live provider, an actual
network namespace with egress disabled, a Redis outage during a running API,
and a deployed restart were not verified in this review.

## Fallback contract by dependency

| Dependency | Missing or disabled | Failure after configuration | Release interpretation |
|---|---|---|---|
| Language provider | Provider factory reports `disabled`; agent stages use deterministic logic. Laya methods return `source="fallback"`. | Typed model-client failures are catchable; Laya catches timeout, connection, HTTP, and malformed-response errors and falls back. | Deterministic demo is usable. Live-language claims require provider smoke evidence. |
| Weave | `TraceSink` keeps local sanitized run/stage/tool events; status is `not_configured`. | Failed initialization/publish adds a warning while local trace recording remains available. | Local observability is available; this does not satisfy the public-Weave prize gate. |
| Redis | Case storage uses process-local memory when `REDIS_URL` is absent; case-memory indexing still ranks local vectors. | Core `store_case`/`get_case` operations surface configured Redis errors; non-critical `set_json` and case-memory writes are best-effort. | No silent loss may be claimed for configured core persistence; restart durability needs deployment evidence. |
| VISTA-3D | Explicitly disabled unless enabled and an endpoint is configured. | Health or submission failure returns `unavailable`/`failed` with warnings; no segmentation-derived values are invented. | The twin remains usable without imaging; live segmentation is unverified. |
| Internet | With provider URLs/keys absent, the tested path makes no optional network call. | Mocked timeout/connection/error paths degrade safely. | Environment-stripped offline behavior passes; OS-level egress isolation is unverified. |

## Source-backed behavior reviewed

### Optional language

`python/hearttwin/tools/env_config.py` and the intelligence factory treat an
incomplete provider configuration as disabled. The deterministic agents do not
require a language provider for extraction, validation, state construction,
operation, recovery, or evaluation. The Wave 6 model client instead raises a
typed `NoHealthyKeyError` or `ModelAPIError` on total failure; callers must
catch that contract rather than treating an empty response as successful.

`python/hearttwin/assistant/laya_adapter.py` is separately env-gated. When
`LAYA_ENABLED` or `LAYA_BASE_URL` is absent, it does not construct an HTTP
client. Any configured-call exception or schema mismatch returns a deterministic
decision with `source="fallback"` and a warning. The adapter exposes only
bounded routing decisions, not clinical authority.

### Weave

`python/hearttwin/tools/weave_trace.py` always records local run events before
or alongside the optional publish operation. Without `WANDB_API_KEY`, the
status is `not_configured`; with an initialization or publish failure, the
status/warnings identify the problem while local traces remain available.
`_sanitize` redacts PII, uploaded bytes, and long content before local or remote
trace publication. A local trace is not evidence that a public Weave project
received a trace.

### Redis

`python/hearttwin/tools/storage.py` intentionally uses `_MEMORY_STORE` only
when Redis is not configured. This avoids hiding a configured persistence outage
for core case reads/writes. In contrast, `python/hearttwin/tools/case_memory.py`
always retains an in-process index and treats Redis indexing/hydration as
best-effort; its cosine ranking remains deterministic offline. The evaluator's
non-critical JSON writes use the same best-effort policy. Operators must inspect
the readiness/status response and persistence logs before claiming durable
multi-process state.

### VISTA-3D

`python/hearttwin/tools/vista3d_client.py` requires both the enable flag and an
API base, health-checks before submission, and returns immediately with a
metadata-only queued result when submission succeeds. Disabled, unreachable,
non-202, malformed, and exception paths carry a warning and never turn a
missing mask into a chamber volume. The local adapter in
`python/hearttwin/imaging/vista3d.py` likewise reports unsupported input,
missing input, missing runner, missing checkpoint, or runner failure without
pretending that segmentation completed.

## Runnable evidence

All commands below ran from `/home/923873155/BeatIT`; no secrets were printed.

### Focused regression suite

```text
python -m pytest -q \
  python/hearttwin/tests/test_openai_fallbacks.py \
  python/hearttwin/tests/test_weave_trace_fallback.py \
  python/hearttwin/tests/test_vista3d_client.py \
  python/hearttwin/tests/test_laya_adapter.py \
  python/hearttwin/tests/test_redis_memory.py \
  python/hearttwin/tests/test_api_routes.py

61 passed, 43 warnings in 3.47s
```

This covers the full deterministic pipeline without an OpenAI key, local trace
creation and PII redaction, disabled/missing/unreachable VISTA, unconfigured and
failing Laya, Redis memory fallback, and API fallback/status assertions.

### Environment-stripped offline probe

The following probe explicitly removed the optional credentials and endpoint
variables before importing the adapters. It exercised one local trace, a local
case round trip, a Laya decision, and the local VISTA adapter:

```text
env -u OPENAI_API_KEY -u WANDB_API_KEY -u REDIS_URL \
  -u VISTA3D_ENABLED -u VISTA3D_API_BASE -u VISTA3D_API_KEY \
  -u LAYA_ENABLED -u LAYA_BASE_URL python - <<'PY'
import asyncio
from python.hearttwin.assistant.laya_adapter import LayaAdapter
from python.hearttwin.imaging.vista3d import Vista3DSegmenter
from python.hearttwin.tools import redis_client
from python.hearttwin.tools.storage import get_case, store_case
from python.hearttwin.tools.weave_trace import get_trace_sink, get_traces

async def main():
    sink = get_trace_sink()
    run_id = sink.start_run("m10-offline-probe", "fallback", {})
    sink.finish_run(run_id, "success", {"mode": "offline"})
    await store_case("m10-offline-case", {"case_id": "m10-offline-case", "status": "created"})
    case = await get_case("m10-offline-case")
    decision = await LayaAdapter().needs_simulation("run an educational simulation")
    volume = type("Volume", (), {"modality": "CT", "path": "/does/not/exist"})()
    vista = Vista3DSegmenter().segment_volume(volume)
    print({"weave_status": sink.weave_info(run_id)["status"],
           "local_trace_events": len(get_traces("m10-offline-probe")),
           "redis_configured": redis_client.is_configured(),
           "case_round_trip": case["status"] if case else None,
           "language_source": decision.source,
           "vista_completed": vista.completed,
           "vista_warning": vista.warnings[0] if vista.warnings else None})

asyncio.run(main())
PY

{'weave_status': 'not_configured',
 'local_trace_events': 2,
 'redis_configured': False,
 'case_round_trip': 'created',
 'language_source': 'fallback',
 'vista_completed': False,
 'vista_warning': 'input volume not found'}
```

The result proves the adapter behavior in a credential-free process, not
network-level isolation.

### Explicit optional-endpoint failures

```text
python -m pytest -q \
  python/hearttwin/tests/test_laya_adapter.py::test_timeout_falls_back \
  python/hearttwin/tests/test_vista3d_client.py::test_segment_cardiac_does_not_raise_on_failure \
  python/hearttwin/tests/test_model_reliability.py::test_all_keys_down_caller_degrades_to_deterministic_fallback

3 passed in 0.12s
```

These tests use fake HTTP transport or an intentionally unreachable local
endpoint; they do not contact a real provider and do not prove behavior under
an actual public-network outage.

### Demo preflight

```text
./scripts/demo-preflight.sh

READY    python
READY    node
READY    curl
READY    demo fixture
READY    ensemble golden
READY    Shadow Trial golden
READY    model manifest
SKIP     HTTP checks (set E2E_BASE_URL)
DEMO READY
```

The preflight result confirms the local deterministic fixture path. Its HTTP
checks were skipped because `E2E_BASE_URL` was not set.

## Safety and data-handling observations

- Fallback status is exposed as metadata/warnings rather than silently
  represented as a live provider success.
- The deterministic physics core remains the source of cardiac calculations;
  optional providers do not receive authority to invent missing measurements.
- Trace sanitization removes obvious PII and raw uploaded bytes before local or
  Weave publication in the reviewed path.
- VISTA failure results explicitly state that segmentation was skipped or
  unavailable; they do not produce a synthetic mask.
- Local Redis fallback is process memory, not durable or multi-user storage.
  It must not be used for patient data or presented as restart-persistent state.

## Unverified tests and release blockers

The following tests were not run or cannot be claimed from this audit:

1. A real language provider outage after successful startup, including its
   timeout budget, retry exhaustion, safety validation, and API error envelope.
2. Weave initialization failure with a real installed Weave client and a
   configured key, plus proof that a public trace is visible after flush.
3. A configured Redis server becoming unreachable during `store_case`,
   `get_case`, SSE/event publication, and process restart; socket deadlines and
   bounded request behavior remain open as recorded by the API reliability
   review.
4. A live VISTA health response, non-202 submission, job polling timeout, and
   cleanup behavior against the deployment-specific service.
5. True internet-off execution using a network namespace/firewall or equivalent
   egress denial. The environment-stripped probe only removes configuration.
6. Reverse-proxy, deployed-host, multi-worker, restart, and cross-process
   persistence verification.
7. Browser-visible fallback/error states and accessibility behavior under the
   provider-offline condition.

## Final gate decision

**Fallback gate: PASS for the local synthetic deterministic demo.**

**Production resilience gate: OPEN.** M10 may state that the optional
dependencies degrade safely in the verified local paths, but it must not claim
live-provider reliability, public Weave delivery, durable Redis persistence,
VISTA service availability, or true internet-off isolation until the unverified
tests above have deployment-specific evidence.
