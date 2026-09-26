"""Bedrock OpenAI model registry — domain code requests roles, not raw profile IDs."""

from __future__ import annotations

import os
from enum import Enum


class ModelRole(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"
    SAFETY = "safety"


_ROLE_ENV: dict[ModelRole, str] = {
    ModelRole.FAST: "MODEL_FAST",
    ModelRole.BALANCED: "MODEL_BALANCED",
    ModelRole.DEEP: "MODEL_DEEP",
    ModelRole.SAFETY: "MODEL_SAFETY",
}

# Hypothesis defaults — benchmark before locking (Wave 3).
_ROLE_DEFAULTS: dict[ModelRole, str] = {
    ModelRole.FAST: "global.openai.gpt-5.6-luna",
    ModelRole.BALANCED: "global.openai.gpt-5.6-terra",
    ModelRole.DEEP: "global.openai.gpt-5.6-sol",
    ModelRole.SAFETY: "openai.gpt-oss-safeguard-20b",
}

# Legacy orchestrator aliases (Wave 6) map onto the registry.
_LEGACY_ROLE_MAP: dict[str, ModelRole] = {
    "fast": ModelRole.FAST,
    "deep": ModelRole.DEEP,
    "safety": ModelRole.SAFETY,
}


def get_model_id(role: ModelRole | str) -> str:
    if isinstance(role, str):
        role = _LEGACY_ROLE_MAP.get(role.lower(), ModelRole(role.lower()))
    env_name = _ROLE_ENV[role]
    return os.environ.get(env_name, _ROLE_DEFAULTS[role]).strip()


def model_registry_health() -> dict[str, object]:
    """Non-secret registry snapshot for status endpoints."""
    configured: dict[str, bool] = {}
    for role in ModelRole:
        env_name = _ROLE_ENV[role]
        raw = os.environ.get(env_name, "").strip()
        configured[role.value] = bool(raw and not raw.startswith("REPLACE_WITH_"))
    return {
        "roles": list(ModelRole),
        "configured_via_env": configured,
        "defaults": {role.value: _ROLE_DEFAULTS[role] for role in ModelRole},
    }
