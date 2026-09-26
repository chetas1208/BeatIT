"""Tests for Bedrock model role registry (``assistant.model_pool`` import path)."""

from __future__ import annotations

import pytest

from python.hearttwin.assistant.model_pool import ModelRole, get_model_id, model_registry_health


def test_default_fast_balanced_deep_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    for env in ("MODEL_FAST", "MODEL_BALANCED", "MODEL_DEEP", "MODEL_SAFETY"):
        monkeypatch.delenv(env, raising=False)
    assert get_model_id(ModelRole.FAST) == "global.openai.gpt-5.6-luna"
    assert get_model_id(ModelRole.BALANCED) == "global.openai.gpt-5.6-terra"
    assert get_model_id(ModelRole.DEEP) == "global.openai.gpt-5.6-sol"
    assert "safeguard" in get_model_id(ModelRole.SAFETY)


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_FAST", "global.openai.gpt-5.6-sol")
    assert get_model_id(ModelRole.FAST) == "global.openai.gpt-5.6-sol"


def test_registry_health_has_no_secrets() -> None:
    health = model_registry_health()
    assert "fast" in health["defaults"]
    assert "roles" in health
