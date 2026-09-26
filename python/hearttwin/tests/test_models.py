from __future__ import annotations

import json
from pathlib import Path

import pytest

from python.hearttwin.models.registry import ModelRegistry


def test_registry_reports_missing_model_without_loading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"models": {"language": {
        "runtime": "test", "path_env": "TEST_MODEL_PATH", "required": False,
    }}}))
    monkeypatch.delenv("TEST_MODEL_PATH", raising=False)
    registry = ModelRegistry(manifest)
    status = registry.status()["language"]
    assert status.configured is False
    assert status.available is False
    assert status.loaded is False


def test_registry_loads_lazily_and_caches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checkpoint = tmp_path / "model.bin"
    checkpoint.write_bytes(b"fixture")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"models": {"language": {
        "runtime": "test", "path_env": "TEST_MODEL_PATH", "required": False,
    }}}))
    monkeypatch.setenv("TEST_MODEL_PATH", str(checkpoint))
    registry = ModelRegistry(manifest)
    calls: list[Path] = []
    loader = lambda path: calls.append(path) or {"loaded": True}
    assert registry.status()["language"].loaded is False
    assert registry.load("language", loader) == {"loaded": True}
    assert registry.load("language", loader) == {"loaded": True}
    assert calls == [checkpoint]
    assert registry.status()["language"].loaded is True
    assert registry.unload("language") is True


def test_registry_missing_checkpoint_fails_independently(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"models": {"segmentation": {
        "runtime": "test", "path_env": "UNSET_MODEL_PATH", "required": False,
    }}}))
    with pytest.raises(FileNotFoundError):
        ModelRegistry(manifest).load("segmentation", lambda path: path)


def test_registry_resolves_relative_paths_from_model_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "models"
    root.mkdir()
    checkpoint = root / "weights.bin"
    checkpoint.write_bytes(b"fixture")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"models": {"segmentation": {
        "runtime": "test", "path_env": "RELATIVE_MODEL_PATH", "required": False,
    }}}))
    monkeypatch.setenv("BEATIT_MODEL_ROOT", str(root))
    monkeypatch.setenv("RELATIVE_MODEL_PATH", "weights.bin")
    registry = ModelRegistry(manifest)
    assert registry.resolve_model_path("segmentation") == checkpoint
    assert registry.status()["segmentation"].available is True
