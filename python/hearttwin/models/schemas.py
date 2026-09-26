"""Small, serializable contracts for local model discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelSpec:
    capability: str
    runtime: str
    path_env: str
    required: bool = False
    default_path: str | None = None
    model_id: str | None = None
    notes: str | None = None

    def configured_path(self, model_root: str | None = None) -> Path | None:
        """Resolve an explicitly configured path without touching model bytes."""
        import os

        configured = os.environ.get(self.path_env, "").strip()
        candidate = configured or self.default_path
        if not candidate:
            return None
        path = Path(candidate).expanduser()
        if not path.is_absolute() and model_root:
            path = Path(model_root).expanduser() / path
        return path


@dataclass(frozen=True)
class ModelStatus:
    capability: str
    runtime: str
    configured: bool
    available: bool
    loaded: bool
    path: str | None = None
    required: bool = False
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "runtime": self.runtime,
            "configured": self.configured,
            "available": self.available,
            "loaded": self.loaded,
            "path": self.path,
            "required": self.required,
            "error": self.error,
            "metadata": self.metadata,
        }
