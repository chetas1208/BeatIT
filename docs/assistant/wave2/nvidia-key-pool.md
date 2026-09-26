# Model-Key Pool — Design Note (Wave 2)

Implements the "reliability pool" described in `GLOBAL_ARCHITECTURE.md`'s
MODEL ROUTER section: three model API keys pooled for health-aware rotation,
rate-limit failover, and temporary quarantine — not three model personalities.

Code: `python/hearttwin/assistant/model_pool.py`.
Tests: `python/hearttwin/tests/test_model_pool.py`.

This module deliberately does **not** make the actual chat-completion HTTP
call. It only answers "which key do I use right now" and "how do I record
whether it worked." A later wave's model-router will call
`ModelKeyPool.get_healthy_key()`, make its own OpenAI-compatible request
(`https://integrate.api.nvidia.com/v1`, `Authorization: Bearer nvapi-...` —
see `docs/assistant/NVIDIA_MODEL_RESEARCH.md`), and then call
`report_success`/`report_failure` on the pool.

## Env vars

Extends the existing `.env.example` provider-neutral convention
(`MODEL_API_KEY` / `MODEL_BASE_URL` / `MODEL_NAME` for the single-model
runtime) rather than introducing NVIDIA-specific names into the public config
surface:

| Var | Purpose | Default |
|---|---|---|
| `MODEL_API_KEY_1` / `_2` / `_3` | Up to 3 pooled keys. Any subset may be set; unset slots are simply not part of the pool. | unset (pool has 0 configured keys) |
| `MODEL_POOL_BASE_URL` | Shared base URL for all configured keys (all three NVIDIA Build keys share one endpoint today; kept configurable, not hardcoded, per the research doc's own caveat that this could change). | `https://integrate.api.nvidia.com/v1` |
| `FAST_MODEL_ID` | Model ID for the fast/agentic role. | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| `DEEP_MODEL_ID` | Model ID for the deep-reasoning role. | `nvidia/nemotron-3-super-120b-a12b` |
| `SAFETY_MODEL_ID` | Model ID for the safety/guardrail role. | `nvidia/nemotron-3.5-content-safety` |

**The `FAST_MODEL_ID`/`DEEP_MODEL_ID`/`SAFETY_MODEL_ID` defaults are
provisional shortlist candidates from Wave 1's research pass, not a locked
routing table.** They are not benchmarked against any real BeatIT task
(cardiac-state explanation, PV-loop narration, physician briefs, tool
planning). Wave 6 owns empirical selection and may change any of these
defaults; nothing in `model_pool.py` enforces or depends on the specific
strings beyond passing them through.

None of these vars were added to `.env.example` by this change — Wave 2's
task scope was code + tests + this note only; whoever wires the pool into a
real router should add the above to `.env.example` at that point, still with
`REPLACE_WITH_...` placeholders for the three keys, never a real value.

## Quarantine / backoff algorithm

Per-key state machine (`_KeySlot`), reset independently per key:

- **Selection**: `get_healthy_key()` round-robins only over keys whose
  `quarantined_until` has passed (compared against an injectable clock,
  `time.monotonic` by default). Returns `None` if zero keys are configured or
  all configured keys are currently quarantined — callers must treat `None`
  as "no generative model available, fall back to deterministic tools only"
  (the FALLBACK TREE's "All NVIDIA unavailable → canonical BeatIT tools still
  work").
- **On success** (`report_success`): clears `consecutive_failures`,
  `quarantine_count`, and any pending quarantine for that key — a real
  success fully closes the breaker.
- **On failure** (`report_failure(key_handle, status_code=None)`):
  - A `429` (rate limit) is treated as an unambiguous signal and quarantines
    the key **immediately** (first failure).
  - Any other failure only quarantines after `failure_threshold`
    (default **3**) *consecutive* failures on that key, so one transient
    network blip doesn't pull a key out of rotation.
  - Quarantine duration is exponential backoff, doubling each time the *same*
    key is quarantined again: `min(max_backoff, initial_backoff * 2 **
    quarantine_count)`, with `initial_backoff = 2s`, `max_backoff = 300s`
    (5 minutes), both overridable via constructor args (not env vars — this
    is an internal reliability parameter, not user-facing config).
  - Sequence for one repeatedly-failing key: 2s → 4s → 8s → 16s → ... → capped
    at 300s.

## Observability

`get_pool_health()` returns only non-secret data — configured/healthy counts
and, per key, referenced by its 1-based env-var slot index only:
`quarantined` (bool), `quarantined_until` (epoch-relative to the clock in
use, or `None` if healthy), `consecutive_failures`, `quarantine_count`. No
key value, prefix, or hash of a key ever appears in this output, in a
`KeyHandle`'s `repr()`/`str()`, or in any exception path in this module —
verified by `test_pool_health_never_contains_key_values` and
`test_key_handle_repr_never_contains_key_value` in the test file, which
assert the fake key strings used in the tests are absent from the serialized
health output and from the handle's repr/str.

## Deliberately out of scope for this file

- The actual OpenAI-compatible HTTP call (future model-router wave).
- Per-key base-URL overrides (a single shared base URL covers today's
  confirmed topology; the base URL is still a constructor/env parameter, not
  hardcoded, so this is a config change if it's ever needed).
- Persisting quarantine state across process restarts — the pool is
  in-memory per process, matching this module's "pure decision, no I/O"
  scope. A future wave can layer Redis-backed shared quarantine state on top
  if multi-process consistency becomes necessary; not needed for the
  reliability behavior described in `GLOBAL_ARCHITECTURE.md`.
