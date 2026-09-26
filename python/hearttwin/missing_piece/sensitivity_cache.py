"""Process-local cache for repeated M8 sensitivity configurations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from typing import Any, TypeVar

T = TypeVar("T")

_CACHE: dict[str, Any] = {}
ENGINE_VERSION_KEY = "engine_version"


def _config_digest(config: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(config), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def get_or_compute(
    config: Mapping[str, Any],
    compute: Callable[[], T],
    *,
    engine_version: str,
) -> T:
    """Return a cached result when ensemble, target, and policy match."""

    digest = _config_digest({ENGINE_VERSION_KEY: engine_version, **dict(config)})
    cached = _CACHE.get(digest)
    if cached is not None:
        return cached
    result = compute()
    _CACHE[digest] = result
    return result


def clear_sensitivity_cache() -> None:
    """Drop cached entries (tests and model-version bumps)."""

    _CACHE.clear()
