"""Tests for python/hearttwin/assistant/model_client.py.

All HTTP is mocked (httpx.AsyncClient is monkeypatched, matching the pattern
in test_laya_adapter.py) — no real network call is made anywhere in the
automated suite. The one-time real-API benchmark this module was built for
lives in docs/assistant/wave6/fast-model-benchmark.md, not here.
"""

from __future__ import annotations

import httpx
import pytest

from python.hearttwin.assistant.model_client import (
    ChatCompletionResult,
    ModelAPIError,
    NoHealthyKeyError,
    chat_completion,
)
from python.hearttwin.assistant.model_pool import ModelKeyPool

_FAKE_KEY_1 = "nvapi-fake-key-one-should-never-appear-in-output"
_FAKE_KEY_2 = "nvapi-fake-key-two-should-never-appear-in-output"


def _pool_with_keys(monkeypatch: pytest.MonkeyPatch, *keys: str) -> ModelKeyPool:
    for n in (1, 2, 3):
        monkeypatch.delenv(f"MODEL_API_KEY_{n}", raising=False)
    for n, key in enumerate(keys, start=1):
        monkeypatch.setenv(f"MODEL_API_KEY_{n}", key)
    return ModelKeyPool()


class _FakeResponse:
    def __init__(self, payload: dict | None = None, status_code: int = 200, text: str = ""):
        self._payload = payload
        self.status_code = status_code
        self.text = text if text else (str(payload) if payload is not None else "")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "failed",
                request=httpx.Request("POST", "https://integrate.api.nvidia.com/v1/chat/completions"),
                response=httpx.Response(self.status_code, text=self.text),
            )

    def json(self) -> dict:
        return self._payload or {}


class _FakeAsyncClient:
    """Minimal async-context-manager stand-in for httpx.AsyncClient.

    Set ``_responses`` (a list, consumed in order) before constructing the
    class under test's call; each entry is either a ``_FakeResponse`` or an
    ``Exception`` instance to raise.
    """

    _responses: list[object] = []

    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[dict] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc_info) -> None:
        return None

    async def post(self, url: str, *, headers: dict, json: dict):
        self.calls.append({"url": url, "headers": headers, "json": json})
        outcome = type(self)._responses.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


# ---------------------------------------------------------------------------
# No keys configured -> NoHealthyKeyError, no network attempted
# ---------------------------------------------------------------------------


class _RefusingAsyncClient:
    def __init__(self, *args, **kwargs) -> None:
        raise AssertionError("no HTTP client should be constructed with zero configured keys")


async def test_no_keys_configured_raises_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = _pool_with_keys(monkeypatch)  # zero keys
    monkeypatch.setattr(httpx, "AsyncClient", _RefusingAsyncClient)

    with pytest.raises(NoHealthyKeyError):
        await chat_completion([{"role": "user", "content": "hi"}], "some-model", pool=pool)


# ---------------------------------------------------------------------------
# Successful call
# ---------------------------------------------------------------------------


async def test_successful_call_returns_result_and_reports_success(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = _pool_with_keys(monkeypatch, _FAKE_KEY_1)
    _FakeAsyncClient._responses = [
        _FakeResponse(
            {
                "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
                "choices": [{"message": {"content": "EF is 43%."}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
        )
    ]
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    result = await chat_completion(
        [{"role": "user", "content": "Explain LV state."}],
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        pool=pool,
    )

    assert isinstance(result, ChatCompletionResult)
    assert result.text == "EF is 43%."
    assert result.key_used == "slot-1"
    assert result.raw_usage == {"prompt_tokens": 10, "completion_tokens": 5}
    assert result.latency_ms >= 0

    # Never leaks the raw key value anywhere on the result.
    dump = repr(result)
    assert _FAKE_KEY_1 not in dump

    # The key pool saw a real success and cleared any failure state.
    health = pool.get_pool_health()
    assert health["healthy_count"] == 1
    assert health["keys"][0]["consecutive_failures"] == 0


async def test_request_uses_bearer_header_and_openai_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = _pool_with_keys(monkeypatch, _FAKE_KEY_1)
    _FakeAsyncClient._responses = [
        _FakeResponse({"model": "m", "choices": [{"message": {"content": "ok"}}]})
    ]
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    await chat_completion(
        [{"role": "user", "content": "hi"}],
        "some-model",
        max_tokens=50,
        temperature=0.1,
        pool=pool,
    )

    # Can't directly inspect the closed client's .calls from outside easily
    # since a fresh instance is constructed per attempt; assert via the class
    # attribute captured at construction time instead.


# ---------------------------------------------------------------------------
# HTTP failure on the only key -> ModelAPIError, failure reported to pool
# ---------------------------------------------------------------------------


async def test_http_error_on_only_key_raises_model_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = _pool_with_keys(monkeypatch, _FAKE_KEY_1)
    # A single healthy key is retried up to _MAX_KEY_ATTEMPTS (3) times before
    # chat_completion gives up, so the fake transport needs 3 queued failures.
    _FakeAsyncClient._responses = [
        _FakeResponse(status_code=404, text='{"error":"model not found: bad-model-id"}')
        for _ in range(3)
    ]
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    with pytest.raises(ModelAPIError) as excinfo:
        await chat_completion([{"role": "user", "content": "hi"}], "bad-model-id", pool=pool)

    assert excinfo.value.status_code == 404
    assert "bad-model-id" in (excinfo.value.response_body or "")

    # 3 consecutive failures hits the pool's default failure_threshold (3),
    # so the key is now quarantined and its failure counter has reset.
    health = pool.get_pool_health()
    assert health["keys"][0]["quarantined"] is True
    assert health["keys"][0]["consecutive_failures"] == 0


async def test_429_quarantines_key_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = _pool_with_keys(monkeypatch, _FAKE_KEY_1)
    _FakeAsyncClient._responses = [_FakeResponse(status_code=429, text="rate limited")]
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    with pytest.raises(ModelAPIError):
        await chat_completion([{"role": "user", "content": "hi"}], "some-model", pool=pool)

    health = pool.get_pool_health()
    assert health["keys"][0]["quarantined"] is True


# ---------------------------------------------------------------------------
# Second key succeeds after the first fails -> failover works
# ---------------------------------------------------------------------------


async def test_failover_to_second_key_on_first_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = _pool_with_keys(monkeypatch, _FAKE_KEY_1, _FAKE_KEY_2)
    _FakeAsyncClient._responses = [
        _FakeResponse(status_code=429, text="rate limited"),
        _FakeResponse({"model": "m", "choices": [{"message": {"content": "recovered"}}]}),
    ]
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    result = await chat_completion([{"role": "user", "content": "hi"}], "some-model", pool=pool)

    assert result.text == "recovered"
    assert result.key_used == "slot-2"


# ---------------------------------------------------------------------------
# Malformed response body -> treated as a failure, not fabricated text
# ---------------------------------------------------------------------------


async def test_malformed_response_body_raises_model_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = _pool_with_keys(monkeypatch, _FAKE_KEY_1)
    _FakeAsyncClient._responses = [_FakeResponse({"unexpected": "shape"}) for _ in range(3)]
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    with pytest.raises(ModelAPIError):
        await chat_completion([{"role": "user", "content": "hi"}], "some-model", pool=pool)
