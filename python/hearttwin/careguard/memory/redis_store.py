"""CareGuard namespaced store over DualBeat's Redis client, with safe fallback.

Policy (mirrors DualBeat's no-silent-fallback rule):
  * REDIS_URL set + CareGuard redis flag on → use real Redis; surface persistence.
  * Otherwise → bounded in-process dict, and callers disclose "not persisted".

Only redacted / deidentified structured payloads should be written here. Raw
FHIR bundles, raw notes, raw prompts, and PHI must never be passed in.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

from python.hearttwin.careguard import feature_flags as flags
from python.hearttwin.careguard.config import redis_ttl_seconds
from python.hearttwin.tools import redis_client

# Bounded in-process fallback (active-request scope; not cross-request durable).
_FALLBACK: dict[str, str] = {}
_FALLBACK_MAX = 2048
_LOCKS: dict[str, float] = {}


def redis_configured() -> bool:
    """True only when a REDIS_URL exists AND the CareGuard redis flag is on."""
    return flags.redis_enabled() and redis_client.is_configured()


def backend() -> str:
    return "redis" if redis_configured() else "in_process_fallback"


def persistence_note() -> str:
    if redis_configured():
        return "Persisted to namespaced Redis."
    return (
        "Redis unavailable — CareGuard is using a bounded in-process fallback for this "
        "request only. Cross-request memory is disabled and nothing is persisted."
    )


def _fallback_set(key: str, value: str) -> None:
    if key not in _FALLBACK and len(_FALLBACK) >= _FALLBACK_MAX:
        _FALLBACK.pop(next(iter(_FALLBACK)))
    _FALLBACK[key] = value


async def set_json(key: str, value: Any, *, ttl: Optional[int] = None) -> bool:
    """Write a JSON value. Returns True if written to real Redis, False if fallback."""
    payload = json.dumps(value, default=str)
    if redis_configured():
        client = redis_client.get_client()
        if client is not None:
            await client.set(key, payload, ex=ttl or redis_ttl_seconds())
            return True
    _fallback_set(key, payload)
    return False


async def get_json(key: str) -> Optional[Any]:
    if redis_configured():
        client = redis_client.get_client()
        if client is not None:
            raw = await client.get(key)
            return json.loads(raw) if raw else None
    raw = _FALLBACK.get(key)
    return json.loads(raw) if raw else None


async def append_json(key: str, value: Any, *, ttl: Optional[int] = None) -> bool:
    """Append to a JSON list stored at ``key`` (used for audit/stage streams)."""
    current = await get_json(key)
    items = current if isinstance(current, list) else []
    items.append(value)
    return await set_json(key, items, ttl=ttl)


async def get_list(key: str) -> list[Any]:
    current = await get_json(key)
    return current if isinstance(current, list) else []


async def acquire_lock(key: str, *, ttl: int = 60) -> bool:
    """Best-effort distributed lock. Redis: SET NX EX. Fallback: process dict."""
    if redis_configured():
        client = redis_client.get_client()
        if client is not None:
            ok = await client.set(key, "1", nx=True, ex=ttl)
            return bool(ok)
    now = time.monotonic()
    exp = _LOCKS.get(key)
    if exp and exp > now:
        return False
    _LOCKS[key] = now + ttl
    return True


async def release_lock(key: str) -> None:
    if redis_configured():
        client = redis_client.get_client()
        if client is not None:
            try:
                await client.delete(key)
            except Exception:  # noqa: BLE001 — lock release is best-effort
                pass
            return
    _LOCKS.pop(key, None)


async def health() -> dict[str, Any]:
    """Redis reachability for system-check (never raises here)."""
    if not flags.redis_enabled():
        return {"enabled": False, "configured": False, "reachable": False, "backend": "disabled"}
    configured = redis_client.is_configured()
    reachable = False
    error = None
    if configured:
        try:
            reachable = await asyncio.wait_for(redis_client.ping(), timeout=2.0)
        except Exception as exc:  # noqa: BLE001 — report, don't crash system-check
            error = type(exc).__name__
    return {
        "enabled": True,
        "configured": configured,
        "reachable": reachable,
        "backend": backend(),
        "error": error,
    }


def reset_fallback() -> None:
    """Clear the in-process fallback + locks (tests)."""
    _FALLBACK.clear()
    _LOCKS.clear()
