"""Simulated failure-injection tests for the NVIDIA model-pool + client (Wave 6).

Agent 30 ("Cost/Latency/Reliability Engineer"). These tests exercise the
campaign's own FAILURE MATRIX end to end —

    ONE KEY DOWN  -> other keys still serve.
    TWO KEYS DOWN -> the remaining healthy key still serves.
    ALL KEYS DOWN -> `get_healthy_key()` returns None and the caller
                     degrades cleanly (a typed, catchable exception) instead
                     of crashing or fabricating a response.

against the REAL `ModelKeyPool` (`python/hearttwin/assistant/model_pool.py`)
and the REAL `chat_completion` client (`python/hearttwin/assistant/
model_client.py`, the async/raising contract that ultimately landed this
wave), with only the HTTP transport (`httpx.AsyncClient`) mocked out — no
real network calls are made anywhere in this file. This mirrors
`test_model_pool.py`'s own established pattern: a `FakeClock` in place of
`time.monotonic`, and fake/synthetic key literals (never real key material)
set via `monkeypatch.setenv`.

Companion doc with real, billed-call measurements (latency, structured-output
success rate, real key-rotation observation):
`docs/assistant/wave6/cost-latency-reliability.md`.

Client contract note: `model_client.chat_completion` (a) retries internally,
once per remaining healthy key, up to 3 attempts total before giving up, and
(b) *raises* a typed `ModelClientError` subclass on total failure rather than
returning an `ok=False` sentinel — its own docstring is explicit that
"callers must not silently treat a failed call as a successful empty
response." So "one key down" / "two keys down" are demonstrated as a single
`chat_completion()` call **transparently succeeding** (the internal retry
absorbs the failed attempt(s) — the caller never sees them), while "all keys
down" is demonstrated as a clean, typed raise that a `try/except
ModelClientError` can catch and turn into a deterministic-fallback response
without crashing the process.

Scope note: as of this wave, `orchestrator.py` has no model-routing branch
wired in yet (confirmed by reading its module docstring — "No LLM /
model-router integration exists in this wave"). So "the caller" exercised
here is `model_client.chat_completion` itself — the real code any future
orchestrator branch would call — plus a minimal inline `try/except
ModelClientError -> fallback` shim standing in for that not-yet-written
orchestrator branch, to prove the contract a real integration must honor.
"""

from __future__ import annotations

import dataclasses
import json

import httpx
import pytest

from python.hearttwin.assistant.model_client import (
    ModelAPIError,
    ModelClientError,
    NoHealthyKeyError,
    chat_completion,
)
from python.hearttwin.assistant.model_pool import ModelKeyPool

# Synthetic, never-real key literals — same convention as test_model_pool.py.
_FAKE_KEY_1 = "nvapi-fake-reliability-key-one-should-never-appear-in-output"
_FAKE_KEY_2 = "nvapi-fake-reliability-key-two-should-never-appear-in-output"
_FAKE_KEY_3 = "nvapi-fake-reliability-key-three-should-never-appear-in-output"
_KEY_BY_SLOT = {1: _FAKE_KEY_1, 2: _FAKE_KEY_2, 3: _FAKE_KEY_3}
_ALL_FAKE_KEYS = (_FAKE_KEY_1, _FAKE_KEY_2, _FAKE_KEY_3)

_FAKE_MESSAGES = [{"role": "user", "content": "hi"}]
_FAKE_MODEL = "fake/model"


def _make_fake_async_client(down_slots: set[int], call_log: list[int]):
    """Fake `httpx.AsyncClient` that fails (simulated 429) for the given slots.

    Identifies which configured key is being used by comparing the request's
    Authorization header against the known *fake* per-slot literals declared
    above (never a real key) — the same "compare against a named fake
    constant" pattern `test_model_pool.py` already uses. `call_log` records
    which slot served each attempt (non-secret — an int) so tests can assert
    distribution and attempt counts without ever inspecting a key value.

    Uses real `httpx.Request`/`httpx.Response` objects (only the network
    transport is faked) so `model_client.py`'s own `response.raise_for_status()`
    / `.json()` / `.text` handling runs unmodified against a realistic shape.
    """

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):  # noqa: ANN001
            auth = (headers or {}).get("Authorization", "")
            slot = next(
                (s for s, k in _KEY_BY_SLOT.items() if auth == f"Bearer {k}"), None
            )
            assert slot is not None, "fake client saw an unrecognized Authorization header"
            call_log.append(slot)
            request = httpx.Request("POST", url)
            if slot in down_slots:
                return httpx.Response(429, text="simulated rate limit (429)", request=request)
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "simulated ok response"}}],
                    "usage": {"total_tokens": 7},
                    "model": _FAKE_MODEL,
                },
                request=request,
            )

    return _FakeAsyncClient


def _setup_three_key_pool(monkeypatch) -> ModelKeyPool:
    monkeypatch.setenv("MODEL_API_KEY_1", _FAKE_KEY_1)
    monkeypatch.setenv("MODEL_API_KEY_2", _FAKE_KEY_2)
    monkeypatch.setenv("MODEL_API_KEY_3", _FAKE_KEY_3)
    return ModelKeyPool()


async def _call_or_fallback(pool: ModelKeyPool) -> dict:
    """Stand-in for the orchestrator branch that does not exist yet.

    This is exactly the shape a future orchestrator model-routing branch
    needs: try the real model client, and on any `ModelClientError` degrade
    to BeatIT's deterministic tools instead of propagating the exception.
    """

    try:
        result = await chat_completion(_FAKE_MESSAGES, _FAKE_MODEL, pool=pool)
        return {"source": "model", "text": result.text, "key_used": result.key_used}
    except ModelClientError:
        return {"source": "deterministic_fallback"}


# ---------------------------------------------------------------------------
# Scenario 1: ONE KEY DOWN -> other keys still serve.
# ---------------------------------------------------------------------------


async def test_one_key_down_other_keys_still_serve(monkeypatch):
    pool = _setup_three_key_pool(monkeypatch)
    call_log: list[int] = []
    monkeypatch.setattr("httpx.AsyncClient", _make_fake_async_client({1}, call_log))

    # A single call must transparently succeed — the internal retry absorbs
    # the one failed attempt against the down key; the caller never sees it.
    first = await chat_completion(_FAKE_MESSAGES, _FAKE_MODEL, pool=pool)
    assert first.key_used != "slot-1"
    assert 1 in call_log  # key 1 really was tried and really did fail once
    assert call_log[0] == 1

    # Subsequent traffic must never land on the down key again.
    results = [await chat_completion(_FAKE_MESSAGES, _FAKE_MODEL, pool=pool) for _ in range(3)]
    assert all(r.key_used in ("slot-2", "slot-3") for r in results)

    health = pool.get_pool_health()
    assert health["configured_count"] == 3
    assert health["healthy_count"] == 2
    slot1 = next(k for k in health["keys"] if k["slot"] == 1)
    assert slot1["quarantined"] is True


# ---------------------------------------------------------------------------
# Scenario 2: TWO KEYS DOWN -> the remaining healthy key still serves.
# ---------------------------------------------------------------------------


async def test_two_keys_down_remaining_key_still_serves(monkeypatch):
    pool = _setup_three_key_pool(monkeypatch)
    call_log: list[int] = []
    monkeypatch.setattr("httpx.AsyncClient", _make_fake_async_client({1, 2}, call_log))

    # A single call must still transparently succeed, via the third key,
    # even though it took 3 internal attempts (the pool's max) to get there.
    first = await chat_completion(_FAKE_MESSAGES, _FAKE_MODEL, pool=pool)
    assert first.key_used == "slot-3"
    assert call_log == [1, 2, 3]

    # Once 1 and 2 are quarantined, every further call resolves in one
    # attempt, always via slot 3.
    call_log.clear()
    results = [await chat_completion(_FAKE_MESSAGES, _FAKE_MODEL, pool=pool) for _ in range(3)]
    assert all(r.key_used == "slot-3" for r in results)
    assert call_log == [3, 3, 3]

    health = pool.get_pool_health()
    assert health["healthy_count"] == 1
    quarantined_slots = {k["slot"] for k in health["keys"] if k["quarantined"]}
    assert quarantined_slots == {1, 2}


# ---------------------------------------------------------------------------
# Scenario 3: ALL KEYS DOWN -> get_healthy_key() is None and the caller
# degrades cleanly (typed exception, no crash) instead of pretending to serve.
# ---------------------------------------------------------------------------


async def test_all_keys_down_live_failure_raises_typed_model_api_error(monkeypatch):
    """All 3 keys fail live within one call's internal retry loop."""

    pool = _setup_three_key_pool(monkeypatch)
    call_log: list[int] = []
    monkeypatch.setattr("httpx.AsyncClient", _make_fake_async_client({1, 2, 3}, call_log))

    with pytest.raises(ModelAPIError) as excinfo:
        await chat_completion(_FAKE_MESSAGES, _FAKE_MODEL, pool=pool)

    assert excinfo.value.status_code == 429
    assert call_log == [1, 2, 3]  # every configured key was genuinely tried, exactly once

    health = pool.get_pool_health()
    assert health["healthy_count"] == 0
    assert pool.get_healthy_key() is None


async def test_all_keys_already_quarantined_raises_without_any_network_call(monkeypatch):
    """All 3 keys already down before the call -> no HTTP attempt at all."""

    pool = _setup_three_key_pool(monkeypatch)
    call_log: list[int] = []
    monkeypatch.setattr("httpx.AsyncClient", _make_fake_async_client({1, 2, 3}, call_log))

    # Pre-exhaust the pool directly (429 on each slot), independent of the client.
    for _ in range(3):
        handle = pool.get_healthy_key()
        pool.report_failure(handle, status_code=429)
    assert pool.get_healthy_key() is None

    with pytest.raises(NoHealthyKeyError):
        await chat_completion(_FAKE_MESSAGES, _FAKE_MODEL, pool=pool)

    # No HTTP attempt is made when the pool was already fully quarantined.
    assert call_log == []


async def test_all_keys_down_caller_degrades_to_deterministic_fallback(monkeypatch):
    """The exact FAILURE MATRIX wording: caller falls back, does not crash."""

    pool = _setup_three_key_pool(monkeypatch)
    call_log: list[int] = []
    monkeypatch.setattr("httpx.AsyncClient", _make_fake_async_client({1, 2, 3}, call_log))

    for _ in range(3):
        handle = pool.get_healthy_key()
        pool.report_failure(handle, status_code=429)

    outcome = await _call_or_fallback(pool)  # must not raise out of this helper
    assert outcome == {"source": "deterministic_fallback"}


# ---------------------------------------------------------------------------
# Secret safety: none of the above simulated-failure exercise ever leaks a
# raw key value through the pool's or client's observability surface.
# ---------------------------------------------------------------------------


async def test_failure_injection_never_leaks_key_values(monkeypatch):
    pool = _setup_three_key_pool(monkeypatch)
    call_log: list[int] = []
    monkeypatch.setattr("httpx.AsyncClient", _make_fake_async_client({1, 2}, call_log))

    results = [await chat_completion(_FAKE_MESSAGES, _FAKE_MODEL, pool=pool) for _ in range(3)]

    monkeypatch.setattr("httpx.AsyncClient", _make_fake_async_client({1, 2, 3}, call_log))
    with pytest.raises(ModelAPIError) as excinfo:
        # Force one more live failure cycle to also capture exception text.
        fresh_pool = _setup_three_key_pool(monkeypatch)
        await chat_completion(_FAKE_MESSAGES, _FAKE_MODEL, pool=fresh_pool)

    serialized_health = json.dumps(pool.get_pool_health())
    serialized_results = json.dumps([dataclasses.asdict(r) for r in results])
    exception_text = str(excinfo.value) + str(excinfo.value.response_body)

    for fake_key in _ALL_FAKE_KEYS:
        assert fake_key not in serialized_health
        assert fake_key not in serialized_results
        assert fake_key not in exception_text
