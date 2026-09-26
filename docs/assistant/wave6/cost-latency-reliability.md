# Cost / Latency / Reliability — NVIDIA Model Integration (Wave 6, Agent 30)

> Agent 30, "Cost/Latency/Reliability Engineer". Real, billed API calls were
> used sparingly (8 logical calls, ~5-8 budget) to measure end-to-end
> reliability of the real HTTP layer (`model_client.py`); everything about
> the pool's *internal* state-machine logic (round-robin order, backoff
> math, quarantine thresholds) was already proven by Wave 2's
> `test_model_pool.py` and is not re-tested here. Failure injection
> (one/two/three keys down) is **simulated** via mocked HTTP, per the task's
> explicit instruction not to burn real quota chasing a real rate limit.
>
> Methodology follows the precedent set by
> `docs/assistant/wave5/laya-evaluation.md` (Agent 22): real numbers, exact
> units, explicit call counts, and no fabricated metrics for anything not
> actually measured.

## Bottom line

- **Real latency was measured for both roles.** `model_client.py` does
  **not** use streaming (`httpx.AsyncClient(...).post()`, no `stream=True`
  anywhere in the module) — so every "latency" number below is **total
  round-trip wall-clock time to the full response body**, not a real
  token-level TTFT. No TTFT number is reported because none was actually
  measured; NVIDIA Build's endpoint is OpenAI-compatible and such endpoints
  commonly support `stream: true`, but this was not tested here (out of
  budget) and is irrelevant while `model_client.py` never sets it.
- **Structured-output (JSON) compliance was 100% once a response was
  actually returned** — 2/2 real JSON-format responses (1 fast, 1 deep)
  parsed as valid JSON directly, no markdown fencing needed. But the FAST
  model's *response-return rate* for the structured task was only 50%
  (1/2) — the other attempt was consumed entirely by a client-side timeout
  before any content came back at all (see below), not a JSON-formatting
  failure.
- **Real key rotation was directly observed**: across the 6 real calls made
  on one shared `ModelKeyPool` instance, the 3 configured keys split their
  successful completions **exactly evenly — slot-1: 2, slot-2: 2, slot-3:
  2** — round-robin working as designed under real load. `get_pool_health()`
  showed `configured_count: 3, healthy_count: 3` both before and after, with
  zero keys ever crossing the quarantine threshold (see "Incidental real
  failures" for why that's notable, not just "nothing happened").
- **All 3 simulated failure-injection scenarios PASS against the campaign's
  FAILURE MATRIX** (`python/hearttwin/tests/test_model_reliability.py`, 6
  automated tests, all mocked HTTP, zero real calls, all passing).
- **No real HTTP 429 was observed anywhere in this task.** The only real
  failure incidentally observed was a client-side **30-second request
  timeout**, hit 3 times (all on the FAST model) — a genuinely useful,
  unplanned reliability finding, reported honestly below rather than
  invented as a 429.
- **No raw key value appears anywhere** in this document, the measurement
  scripts (scratchpad-only, not committed), or the new test file — verified
  by direct string search (see "Secret-safety confirmation").

## Client and model IDs used

`python/hearttwin/assistant/model_client.py` existed by the time this task
needed it (it did not exist at task start; two sibling agents' work
converged on it mid-wave — see that file's own docstring). The version used
here is the **async, raising** contract: `chat_completion(messages, model,
*, max_tokens, temperature, pool, timeout_seconds) -> ChatCompletionResult`,
which retries internally up to 3 times (once per remaining healthy key)
before raising `ModelAPIError` (an attempted-and-failed total loss) or
`NoHealthyKeyError` (pool already fully quarantined, zero attempts made).

Model IDs (cross-checked against sibling docs, not guessed):

- **FAST**: `nvidia/nemotron-3.5-lightning-30b-a3b` — confirmed live and
  accepted by `docs/assistant/wave6/fast-model-benchmark.md` (Agent 26, 8
  real calls, all HTTP 200) and independently reconfirmed by this task's own
  real calls below.
- **DEEP**: `nvidia/nemotron-3-super-120b-a12b` — confirmed live and
  accepted by `docs/assistant/wave6/deep-model-benchmark.md` (Agent 27) and
  independently reconfirmed here.

Both are the unmodified `model_pool.py` defaults (`FAST_MODEL_ID`/
`DEEP_MODEL_ID` in `.env`) — no fallback ID was ever needed by any of the
three wave-6 agents who made real calls against them.

## Real call budget and methodology

**8 logical (billed-intent) calls made, 7 succeeded, 1 failed outright.**
Because `chat_completion` retries internally on failure, actual real HTTP
requests sent to NVIDIA totaled **12** (reconstructed honestly below from
the gap between `ChatCompletionResult.latency_ms`, which — this is worth
flagging as its own finding — is computed fresh *per attempt* inside
`model_client.py`'s retry loop and therefore **under-reports** true
end-to-end latency whenever an internal retry occurred, vs. this task's own
wall-clock measurement wrapped around the entire `chat_completion()` call,
which is what's reported as "latency" throughout this document unless noted
otherwise).

All calls shared **one `ModelKeyPool()` instance** (reads the real
`MODEL_API_KEY_1/2/3` from `.env` via `python-dotenv`) so key-rotation state
would accumulate realistically, except the one extra follow-up call (#8),
which used a fresh pool instance since it was added purely to get a
structured-output data point for the FAST model and didn't need shared
rotation state.

| # | Label | Model | max_tokens | timeout | Real HTTP attempts | Outcome | Wall-clock latency |
|---|---|---|---|---|---|---|---|
| 1 | `fast_latency_1` | FAST | 60 | 30s | 2 (1 timeout, 1 success) | ok, slot-2 | 32,034.9 ms |
| 2 | `fast_structured_1` | FAST | 120 | 30s | 3 (all timeout) | **failed** (`ModelAPIError`) | 90,265.4 ms |
| 3 | `deep_latency_1` | DEEP | 250 | 60s | 1 | ok, slot-3 | 4,010.3 ms |
| 4 | `deep_structured_1` | DEEP | 500 | 60s | 1 | ok, slot-1 | 1,593.5 ms |
| 5 | `fast_rotation_2` | FAST | 60 | 30s | 2 (1 timeout, 1 success) | ok, slot-3 | 56,150.0 ms |
| 6 | `fast_rotation_3` | FAST | 60 | 30s | 1 | ok, slot-1 | 21,517.2 ms |
| 7 | `fast_rotation_4` | FAST | 60 | 30s | 1 | ok, slot-2 | 4,128.0 ms |
| 8 | `fast_structured_2` (extra, fresh pool) | FAST | 300 | 45s | 1 | ok, slot-1 | 29,544.6 ms |

Prompts used: a minimal, non-clinical connectivity sentence for the
"latency" rows ("Reply with exactly one short sentence confirming you
received this test message.") and a strict JSON-only instruction for the
"structured" rows (three required keys, explicitly no markdown fences, no
clinical content in either — this script bypasses BeatIT's own
conversation pipeline entirely, so keeping prompts clinically-inert avoids
any ambiguity about golden-rule-4 relevance).

## Real latency results

**Deep model (`nemotron-3-super-120b-a12b`), n=2 real calls, both single-attempt, no retries:**

| Task | Latency | Notes |
|---|---|---|
| Plain latency | 4,010.3 ms | Clean answer, no truncation: *"I received your test message."* |
| Structured JSON | 1,593.5 ms | Valid JSON, parsed directly, no fencing |

Consistent with the sibling deep-model-benchmark.md's own ~4-5s baseline
finding for this model (n=1 there, n=2 here, same ballpark).

**Fast model (`nemotron-3.5-lightning-30b-a3b`), n=6 real attempts (5 successful "outer" calls + 1 outright failure):**

| Task | Latency | Outcome |
|---|---|---|
| `fast_latency_1` | 32,034.9 ms | ok (1 internal retry) |
| `fast_structured_1` | 90,265.4 ms | **failed** — 3/3 keys timed out |
| `fast_rotation_2` | 56,150.0 ms | ok (1 internal retry) |
| `fast_rotation_3` | 21,517.2 ms | ok (single attempt) |
| `fast_rotation_4` | 4,128.0 ms | ok (single attempt) |
| `fast_structured_2` | 29,544.6 ms | ok (single attempt) |

Of the 5 *successful* fast calls: min 4,128 ms, max 56,150 ms, mean
~28,675 ms, median ~29,545 ms — **highly variable, and on this small sample
the FAST model was on average an order of magnitude slower than the DEEP
model**, the opposite of what the role names imply. This independently
corroborates `docs/assistant/wave6/fast-model-benchmark.md`'s own finding
of "4.3s-28.6s across near-identical short prompts, with no clear
correlation to token count" on this same model/tier — two independent real
measurement runs (Agent 26's and this one) landed on the same conclusion.

**Chain-of-thought preamble note (corroborating, not duplicating, the
sibling finding):** of the 4 fast calls made at the smallest budget (60
tokens), 3 came back as an unfinished internal "Here's a thinking
process:..." monologue with no final answer ever reached, and 1
(`fast_rotation_2`) answered cleanly ("Received.") within the same 60-token
budget — i.e. this is a frequent but not deterministic behavior at low
`max_tokens` (consistent with `temperature=0.2`, not 0, in
`model_client.py`'s default), not the unconditional 100% the sibling's
6-call sample happened to show. Either way, the practical conclusion is the
same as the sibling's: **do not budget a "fast" role call assuming the
model text will be free of chain-of-thought preamble.**

## Structured-output success rate

| Model | Attempts | Returned content | Valid JSON given content | Notes |
|---|---|---|---|---|
| DEEP | 1 | 1/1 (100%) | 1/1 (100%) | Clean on first try, default 500-token budget, 60s timeout |
| FAST | 2 | 1/2 (50%) | 1/1 (100%) | First attempt (120 tokens, 30s timeout) returned **zero** content — exhausted all 3 keys via timeout, an infrastructure failure, not malformed JSON. Second attempt (300 tokens, 45s timeout) succeeded, valid JSON, no fencing. |

Both real JSON payloads returned, verbatim:

- DEEP: `{"model_family": "gpt-4", "can_follow_json_instructions": true, "one_word_confidence": "certain"}`
  (note: the model self-reported an inaccurate `model_family` value — not a
  JSON-format problem, a content-accuracy one, out of scope for this task's
  reliability focus but worth flagging for whoever tunes prompts later.)
- FAST: `{"model_family": "Nemotron", "can_follow_json_instructions": true, "one_word_confidence": "high"}`

**Honest read:** structured-output *format* compliance is excellent (2/2)
once a response comes back at all; the real risk this task's data surfaces
is *getting a response back within a normal timeout budget* for the FAST
model, not JSON formatting.

## Key rotation under real load

Across the 6 real calls sharing one `ModelKeyPool` instance, successful
completions by slot: **slot-1: 2, slot-2: 2, slot-3: 2** — perfectly even,
confirming round-robin distribution holds under real network conditions
(including the 2 calls that needed an internal retry past a timed-out key).
`pool.get_pool_health()` immediately after that run:

```json
{
  "configured_count": 3,
  "healthy_count": 3,
  "keys": [
    {"slot": 1, "quarantined": false, "consecutive_failures": 0, "quarantine_count": 0},
    {"slot": 2, "quarantined": false, "consecutive_failures": 0, "quarantine_count": 0},
    {"slot": 3, "quarantined": false, "consecutive_failures": 0, "quarantine_count": 0}
  ]
}
```

No raw key value appears here or anywhere else — only slot indices and
booleans/counts, matching `get_pool_health()`'s own documented contract.

## Incidental real failures observed (not deliberately triggered)

**No real HTTP 429 was observed** in any of the 12 real HTTP attempts made
across this task's two measurement scripts — consistent with
`fast-model-benchmark.md`'s own 8/8-success run and `deep-model-benchmark.md`'s
7/8-success run (its one non-billed failure was a transient 503, also not a
429). Per the task's explicit instruction, no attempt was made to trigger a
real rate limit deliberately, so this is reported as "not observed," not "does
not exist."

**What *was* incidentally observed: 3 real client-side 30-second request
timeouts, all on the FAST model, across 2 of the 8 logical calls** —
`fast_structured_1` exhausted all 3 keys this way (each 30s timeout, one per
key, per `chat_completion`'s internal retry loop), and 2 other fast calls
(`fast_latency_1`, `fast_rotation_2`) each hit exactly one timeout before
succeeding on their next internal attempt. Because a 30s timeout is a
generic (non-429) failure, `model_pool.py`'s design correctly required 3
*consecutive* failures on the *same* key before quarantining it — since no
single key ever failed 3 times in a row within this run (the pool's own
round-robin moved on to a different key before any one key could
accumulate 3 hits), **none of these real timeouts actually quarantined a
key**, and every key's `consecutive_failures` was reset to 0 by a later
real success on that same key before this run ended. This is the
quarantine threshold working exactly as designed (tolerate an isolated
blip, don't overreact) — but it also means a real, if narrow, gap is worth
flagging: **if all 3 keys became simultaneously and persistently slow at
once (not just one isolated blip each), this same tolerant design would
have to actually observe 3 consecutive failures per key before reacting,
by which point every configured key would already have timed out 3 times
each (9 real failed requests) before the pool "gives up" on any of them.**
Not a bug — a real, quantified characteristic of the current threshold=3
design worth knowing.

**Integration recommendation (observation only — `model_client.py` was not
modified per this task's file-ownership constraint):** the FAST model's own
observed real latency distribution here (median ~21-30s even on clean
successes) sits uncomfortably close to `model_client.py`'s default 30s
`timeout_seconds`, meaning a meaningful fraction of genuinely-in-progress
(not failed) FAST model calls will be misclassified as failures by the
client's own timeout, not by the server actually rejecting them. Combined
with `fast-model-benchmark.md`'s independent latency findings, this is a
second, independent real-data point suggesting the FAST role's model
choice and/or `model_client.py`'s default timeout deserve a follow-up
look before this path is wired into `orchestrator.py`.

## Simulated failure-injection scenarios vs. the FAILURE MATRIX

All three scenarios are automated, mocked-HTTP tests in
`python/hearttwin/tests/test_model_reliability.py` (6 tests total, 0 real
calls, reusing `test_model_pool.py`'s established `FakeClock`/fake-key-literal
pattern, extended to also fake `httpx.AsyncClient` since `model_client.py`
is now the real async HTTP layer). All 6 pass:

```
python/hearttwin/tests/test_model_reliability.py::test_one_key_down_other_keys_still_serve PASSED
python/hearttwin/tests/test_model_reliability.py::test_two_keys_down_remaining_key_still_serves PASSED
python/hearttwin/tests/test_model_reliability.py::test_all_keys_down_live_failure_raises_typed_model_api_error PASSED
python/hearttwin/tests/test_model_reliability.py::test_all_keys_already_quarantined_raises_without_any_network_call PASSED
python/hearttwin/tests/test_model_reliability.py::test_all_keys_down_caller_degrades_to_deterministic_fallback PASSED
python/hearttwin/tests/test_model_reliability.py::test_failure_injection_never_leaks_key_values PASSED
6 passed in 0.04s
```

| FAILURE MATRIX case | Verdict | Evidence |
|---|---|---|
| **ONE KEY DOWN → other keys still serve** | **PASS** | `test_one_key_down_other_keys_still_serve`: with key 1 simulated as permanently rate-limited, a single `chat_completion()` call **transparently succeeds** (the internal retry absorbs the one failed attempt against key 1 — the caller never sees an exception). Every subsequent call lands only on keys 2/3; `get_pool_health()` shows `healthy_count: 2`, key 1 quarantined. |
| **TWO KEYS DOWN → remaining key still serves** | **PASS** | `test_two_keys_down_remaining_key_still_serves`: with keys 1 and 2 down, a single call still transparently succeeds via key 3 (taking all 3 internal attempts to get there); every further call resolves in one attempt, always via key 3. `healthy_count: 1`. |
| **ALL KEYS DOWN → `get_healthy_key()` is `None`, caller degrades, no crash** | **PASS** | Two angles, both green: (1) `test_all_keys_down_live_failure_raises_typed_model_api_error` — all 3 keys fail live within one call's internal retry loop → raises `ModelAPIError` (a typed, catchable exception), never an unhandled crash; `get_healthy_key()` confirmed `None` afterward. (2) `test_all_keys_already_quarantined_raises_without_any_network_call` — pool pre-exhausted → raises `NoHealthyKeyError` with **zero** network attempts. (3) `test_all_keys_down_caller_degrades_to_deterministic_fallback` — a minimal `try/except ModelClientError` shim (standing in for the orchestrator branch that doesn't exist yet — see below) returns `{"source": "deterministic_fallback"}` cleanly, proving the exact contract a real integration must honor. |

**Scope honesty note (updated mid-task):** at the start of this task,
`orchestrator.py` had no model-routing branch wired in (its module
docstring said "No LLM / model-router integration exists in this wave").
**A concurrent sibling agent wired one in during this same wave**, and by
the time this task finished, `orchestrator.py` contained exactly the
`try: result = await chat_completion(...) except ModelClientError: return
<fallback AssistantResponse>` pattern this section's
`_call_or_fallback` test shim was built to prove out — independently
confirming this task's failure-injection verdicts now describe real,
integrated production behavior, not just a hypothetical stand-in. (Read
directly, not modified: `orchestrator.py` remains untouched by this task
per its file-ownership constraint; the full suite was re-run after that
concurrent change landed — see "Files touched" below.)

Full suite regression check: `python3 -m pytest python/hearttwin/ -q` →
**1231 passed, 5 skipped, 6 xfailed** (re-run at the end of this task, after
a concurrent sibling agent's real `orchestrator.py` model-routing
integration landed mid-wave — see "Scope honesty note" above). This task's
own new test file did not touch or break anything (no existing test was
modified).

## Secret-safety confirmation

- `test_model_reliability.py` uses only synthetic literals
  (`nvapi-fake-reliability-key-{one,two,three}-should-never-appear-in-output`)
  for `monkeypatch.setenv`, exactly mirroring `test_model_pool.py`'s and
  `test_model_client.py`'s own established convention — never real key
  material.
- `test_failure_injection_never_leaks_key_values` explicitly asserts none of
  the 3 fake literals appear in `get_pool_health()`'s JSON, in any
  `ChatCompletionResult`'s serialized fields, or in a raised exception's
  message/`response_body`.
- The two real-call measurement scripts (scratchpad-only, not committed to
  the repo) never printed, logged, or included a raw key value in their JSON
  output — verified directly: `grep -c "nvapi-" <stderr log>` → `0`, and the
  captured stdout JSON above contains only `slot-N` identifiers, latencies,
  and model text.
- This document itself contains zero key values, by construction (every
  reference above is a slot index or an aggregate count).

## Files touched

- **Added:** `docs/assistant/wave6/cost-latency-reliability.md` (this file).
- **Added:** `python/hearttwin/tests/test_model_reliability.py` (6 tests, all
  mocked, no real calls).
- **Not touched:** `model_pool.py`, `model_client.py`, `orchestrator.py`,
  `cardiac_state.py`, `hemodynamics.py`, `recovery_sim.py`,
  `shadow_trial_*.py`, `api.py`, `copilot.py`, `careguard/*` — none were
  modified, per this task's file-ownership constraint. The two ad-hoc
  real-call measurement scripts used to produce the numbers above live only
  in this session's scratchpad directory, not in the repo.
