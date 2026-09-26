"""Tests for the provider-neutral model-key pool (python/hearttwin/assistant/model_pool.py).

No real network calls are made anywhere — the pool itself never makes an HTTP
request (that's a later wave's model-router job), and these tests only ever
touch env vars and a fake clock.
"""

from __future__ import annotations

import json

import pytest

from python.hearttwin.assistant.model_pool import (
    DEFAULT_INITIAL_BACKOFF_SECONDS,
    ModelKeyPool,
    ModelRole,
    get_model_id,
)

_FAKE_KEY_1 = "nvapi-fake-key-one-should-never-appear-in-output"
_FAKE_KEY_2 = "nvapi-fake-key-two-should-never-appear-in-output"
_FAKE_KEY_3 = "nvapi-fake-key-three-should-never-appear-in-output"


class FakeClock:
    """Deterministic stand-in for time.monotonic — advance() instead of sleep()."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


# ---------------------------------------------------------------------------
# Zero keys configured — the normal state until real keys are supplied.
# ---------------------------------------------------------------------------


def test_zero_keys_configured_reports_empty_pool(monkeypatch):
    for n in (1, 2, 3):
        monkeypatch.delenv(f"MODEL_API_KEY_{n}", raising=False)

    pool = ModelKeyPool()

    assert pool.get_healthy_key() is None
    health = pool.get_pool_health()
    assert health == {"configured_count": 0, "healthy_count": 0, "keys": []}


def test_zero_keys_report_calls_do_not_raise(monkeypatch):
    for n in (1, 2, 3):
        monkeypatch.delenv(f"MODEL_API_KEY_{n}", raising=False)
    pool = ModelKeyPool()

    from python.hearttwin.assistant.model_pool import KeyHandle

    stale_handle = KeyHandle(slot=1, api_key="irrelevant", base_url="http://x")
    # Reporting against a handle that doesn't match any configured slot must
    # be a no-op, never an exception (defensive against a stale/racy caller).
    pool.report_success(stale_handle)
    pool.report_failure(stale_handle, status_code=429)


# ---------------------------------------------------------------------------
# Round-robin across configured keys.
# ---------------------------------------------------------------------------


def test_round_robin_across_three_keys(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY_1", _FAKE_KEY_1)
    monkeypatch.setenv("MODEL_API_KEY_2", _FAKE_KEY_2)
    monkeypatch.setenv("MODEL_API_KEY_3", _FAKE_KEY_3)

    pool = ModelKeyPool(clock=FakeClock())

    slots_seen = [pool.get_healthy_key().slot for _ in range(6)]
    assert slots_seen == [1, 2, 3, 1, 2, 3]


def test_partial_configuration_round_robins_only_configured_slots(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY_1", _FAKE_KEY_1)
    monkeypatch.delenv("MODEL_API_KEY_2", raising=False)
    monkeypatch.setenv("MODEL_API_KEY_3", _FAKE_KEY_3)

    pool = ModelKeyPool(clock=FakeClock())

    health = pool.get_pool_health()
    assert health["configured_count"] == 2
    slots_seen = [pool.get_healthy_key().slot for _ in range(4)]
    assert slots_seen == [1, 3, 1, 3]


def test_key_handle_carries_base_url(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY_1", _FAKE_KEY_1)
    monkeypatch.setenv("MODEL_POOL_BASE_URL", "https://example-nim.internal/v1")

    pool = ModelKeyPool(clock=FakeClock())
    handle = pool.get_healthy_key()
    assert handle.base_url == "https://example-nim.internal/v1"
    assert handle.api_key == _FAKE_KEY_1


# ---------------------------------------------------------------------------
# Quarantine on failure + exponential backoff.
# ---------------------------------------------------------------------------


def test_429_quarantines_immediately_and_skips_key(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY_1", _FAKE_KEY_1)
    monkeypatch.setenv("MODEL_API_KEY_2", _FAKE_KEY_2)
    clock = FakeClock()
    pool = ModelKeyPool(clock=clock)

    handle_1 = pool.get_healthy_key()
    assert handle_1.slot == 1
    pool.report_failure(handle_1, status_code=429)

    # Key 1 is quarantined immediately (single 429 is definitive) — next call
    # must return key 2, not round-robin back onto the quarantined key.
    handle_2 = pool.get_healthy_key()
    assert handle_2.slot == 2


def test_non_rate_limit_failures_need_threshold_before_quarantine(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY_1", _FAKE_KEY_1)
    monkeypatch.setenv("MODEL_API_KEY_2", _FAKE_KEY_2)
    clock = FakeClock()
    pool = ModelKeyPool(clock=clock, failure_threshold=3)

    handle_1 = pool.get_healthy_key()
    assert handle_1.slot == 1
    pool.report_failure(handle_1)  # 1 of 3 — not quarantined yet
    pool.report_failure(handle_1)  # 2 of 3 — not quarantined yet

    health = pool.get_pool_health()
    assert health["keys"][0]["quarantined"] is False

    pool.report_failure(handle_1)  # 3 of 3 — now quarantined
    health = pool.get_pool_health()
    assert health["keys"][0]["quarantined"] is True


def test_quarantine_expires_after_backoff_duration(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY_1", _FAKE_KEY_1)
    clock = FakeClock()
    pool = ModelKeyPool(clock=clock)

    handle = pool.get_healthy_key()
    pool.report_failure(handle, status_code=429)
    assert pool.get_healthy_key() is None  # still quarantined

    clock.advance(DEFAULT_INITIAL_BACKOFF_SECONDS - 0.01)
    assert pool.get_healthy_key() is None  # not quite expired

    clock.advance(0.02)
    revived = pool.get_healthy_key()
    assert revived is not None and revived.slot == 1


def test_backoff_doubles_on_repeated_quarantine(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY_1", _FAKE_KEY_1)
    clock = FakeClock()
    pool = ModelKeyPool(clock=clock, max_backoff_seconds=1000.0)

    handle = pool.get_healthy_key()
    pool.report_failure(handle, status_code=429)  # 1st quarantine: 2s
    clock.advance(DEFAULT_INITIAL_BACKOFF_SECONDS + 0.01)
    handle = pool.get_healthy_key()
    assert handle is not None

    pool.report_failure(handle, status_code=429)  # 2nd quarantine: 4s
    clock.advance(DEFAULT_INITIAL_BACKOFF_SECONDS + 0.01)
    assert pool.get_healthy_key() is None  # 2s not enough this time
    clock.advance(DEFAULT_INITIAL_BACKOFF_SECONDS + 0.01)
    handle = pool.get_healthy_key()
    assert handle is not None

    pool.report_failure(handle, status_code=429)  # 3rd quarantine: 8s
    clock.advance(4.0 + 0.01)
    assert pool.get_healthy_key() is None  # 4s still not enough
    clock.advance(4.0 + 0.01)
    assert pool.get_healthy_key() is not None


def test_backoff_caps_at_max(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY_1", _FAKE_KEY_1)
    clock = FakeClock()
    pool = ModelKeyPool(clock=clock, max_backoff_seconds=5.0)

    handle = pool.get_healthy_key()
    # Drive many repeated quarantines — backoff must never exceed the cap.
    for _ in range(10):
        pool.report_failure(handle, status_code=429)
        clock.advance(5.01)
        handle = pool.get_healthy_key()
        assert handle is not None

    health = pool.get_pool_health()
    assert health["keys"][0]["quarantine_count"] == 10


def test_report_success_clears_failure_state(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY_1", _FAKE_KEY_1)
    clock = FakeClock()
    pool = ModelKeyPool(clock=clock, failure_threshold=3)

    handle = pool.get_healthy_key()
    pool.report_failure(handle)
    pool.report_failure(handle)
    pool.report_success(handle)

    health = pool.get_pool_health()
    assert health["keys"][0]["consecutive_failures"] == 0
    assert health["keys"][0]["quarantine_count"] == 0
    assert health["keys"][0]["quarantined"] is False


# ---------------------------------------------------------------------------
# Model-role defaults (provisional, per NVIDIA_MODEL_RESEARCH.md).
# ---------------------------------------------------------------------------


def test_model_role_defaults_are_populated(monkeypatch):
    for role in ModelRole:
        monkeypatch.delenv(role.value.upper() + "_MODEL_ID", raising=False)

    assert get_model_id(ModelRole.FAST) == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert get_model_id(ModelRole.DEEP) == "nvidia/nemotron-3-super-120b-a12b"
    assert get_model_id(ModelRole.SAFETY) == "nvidia/nemotron-3.5-content-safety"


def test_model_role_env_override(monkeypatch):
    monkeypatch.setenv("FAST_MODEL_ID", "nvidia/some-other-fast-model")
    assert get_model_id(ModelRole.FAST) == "nvidia/some-other-fast-model"


# ---------------------------------------------------------------------------
# Secret-safety: get_pool_health() must never leak a key value.
# ---------------------------------------------------------------------------


def test_pool_health_never_contains_key_values(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY_1", _FAKE_KEY_1)
    monkeypatch.setenv("MODEL_API_KEY_2", _FAKE_KEY_2)
    monkeypatch.setenv("MODEL_API_KEY_3", _FAKE_KEY_3)
    clock = FakeClock()
    pool = ModelKeyPool(clock=clock)

    handle = pool.get_healthy_key()
    pool.report_failure(handle, status_code=429)
    pool.report_success(handle)

    health = pool.get_pool_health()
    serialized = json.dumps(health)
    for fake_key in (_FAKE_KEY_1, _FAKE_KEY_2, _FAKE_KEY_3):
        assert fake_key not in serialized


def test_key_handle_repr_never_contains_key_value(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY_1", _FAKE_KEY_1)
    pool = ModelKeyPool(clock=FakeClock())
    handle = pool.get_healthy_key()

    assert _FAKE_KEY_1 not in repr(handle)
    assert _FAKE_KEY_1 not in str(handle)
