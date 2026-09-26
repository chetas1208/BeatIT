"""Lazy registry for optional local model artifacts.

Only metadata and filesystem existence are inspected here. Loading a model is
an explicit operation supplied by the caller, so API startup never allocates
GPU memory or imports optional ML frameworks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Callable, TypeVar

from python.hearttwin.models.schemas import ModelSpec, ModelStatus

T = TypeVar("T")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MANIFEST = _REPO_ROOT / "models" / "manifest.json"


class ModelRegistry:
    def __init__(self, manifest_path: Path | None = None) -> None:
        self.manifest_path = manifest_path or _DEFAULT_MANIFEST
        self._models: dict[str, ModelSpec] | None = None
        self._loaded: dict[str, Any] = {}
        self._lock = RLock()

    def _read_specs(self) -> dict[str, ModelSpec]:
        if self._models is not None:
            return self._models
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        entries = payload.get("models", payload) if isinstance(payload, dict) else {}
        specs: dict[str, ModelSpec] = {}
        for capability, raw in entries.items():
            if not isinstance(raw, dict):
                continue
            specs[capability] = ModelSpec(
                capability=capability,
                runtime=str(raw.get("runtime", "unknown")),
                path_env=str(raw.get("path_env", "")),
                required=bool(raw.get("required", False)),
                default_path=raw.get("default_path"),
                model_id=raw.get("model_id"),
                notes=raw.get("notes"),
            )
        self._models = specs
        return specs

    def get_model(self, capability: str) -> ModelSpec | None:
        return self._read_specs().get(capability)

    def resolve_model_path(self, capability: str) -> Path | None:
        """Resolve one capability path using the same rules as status/load."""
        spec = self.get_model(capability)
        return spec.configured_path(os.environ.get("BEATIT_MODEL_ROOT", "")) if spec else None

    def status(self, capability: str | None = None) -> dict[str, ModelStatus]:
        specs = self._read_specs()
        if capability is not None:
            specs = {capability: specs[capability]} if capability in specs else {}
        result: dict[str, ModelStatus] = {}
        for name, spec in specs.items():
            path = self.resolve_model_path(name)
            configured = bool(path)
            available = bool(path and (path.is_file() or (path.is_dir() and (path / "config.json").is_file())))
            error = None if available or not configured else "checkpoint_not_found"
            result[name] = ModelStatus(
                capability=name,
                runtime=spec.runtime,
                configured=configured,
                available=available,
                loaded=name in self._loaded,
                path=str(path) if path else None,
                required=spec.required,
                error=error,
                metadata={"model_id": spec.model_id, "notes": spec.notes},
            )
        return result

    def load(self, capability: str, loader: Callable[[Path], T]) -> T:
        """Load one capability on demand and cache the result.

        ``loader`` is injected by an imaging or language adapter; the registry
        itself remains independent of torch, MONAI, and transformer APIs.
        """
        with self._lock:
            if capability in self._loaded:
                return self._loaded[capability]
            spec = self.get_model(capability)
            if spec is None:
                raise KeyError(f"unknown model capability: {capability}")
            path = self.resolve_model_path(capability)
            if path is None or not (path.is_file() or path.is_dir()):
                raise FileNotFoundError(f"model checkpoint unavailable for {capability}")
            loaded = loader(path)
            self._loaded[capability] = loaded
            return loaded

    def unload(self, capability: str) -> bool:
        with self._lock:
            return self._loaded.pop(capability, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._loaded.clear()


_REGISTRY: ModelRegistry | None = None


def get_model_registry() -> ModelRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ModelRegistry()
    return _REGISTRY
