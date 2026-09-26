"""Request-scoped in-process cache to avoid repeated expensive source calls
within a single review (spec §17). Not cross-request; not durable.
"""

from __future__ import annotations

from typing import Any, Callable

_STORE: dict[str, Any] = {}


def get_or_compute(key: str, compute: Callable[[], Any]) -> Any:
    if key in _STORE:
        return _STORE[key]
    val = compute()
    _STORE[key] = val
    return val


def clear() -> None:
    _STORE.clear()
