"""Tests for the process-local M8 sensitivity cache."""

from __future__ import annotations

from python.hearttwin.missing_piece.sensitivity_cache import clear_sensitivity_cache, get_or_compute


def test_cache_returns_same_object_for_identical_config() -> None:
    clear_sensitivity_cache()
    calls = {"count": 0}

    def compute() -> dict[str, int]:
        calls["count"] += 1
        return {"value": 1}

    config = {"ensemble_id": "ens-1", "target_metric": "stroke_volume_ml", "step": 0.05}
    first = get_or_compute(config, compute, engine_version="m8-test")
    second = get_or_compute(config, compute, engine_version="m8-test")

    assert first is second
    assert calls["count"] == 1


def test_cache_invalidates_on_engine_version_change() -> None:
    clear_sensitivity_cache()
    calls = {"count": 0}

    def compute() -> int:
        calls["count"] += 1
        return calls["count"]

    config = {"ensemble_id": "ens-2", "target_metric": "ef"}
    assert get_or_compute(config, compute, engine_version="v1") == 1
    assert get_or_compute(config, compute, engine_version="v2") == 2
    assert calls["count"] == 2
