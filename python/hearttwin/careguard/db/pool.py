"""Lazy, reusable async Postgres connection pool (psycopg3).

One pool per process, opened on first use and reused — warm connections avoid a
per-request TLS handshake to Neon. Safe when unconfigured: returns None.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from python.hearttwin.tools.env_config import env_bool

_POOL: Any | None = None
_POOL_DSN: str | None = None


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "").strip()


def is_configured() -> bool:
    return env_bool("CAREGUARD_DB_ENABLED", True) and bool(database_url())


def _pool_min() -> int:
    try:
        return max(0, int(os.environ.get("CAREGUARD_DB_POOL_MIN", "1")))
    except ValueError:
        return 1


def _pool_max() -> int:
    try:
        return max(1, int(os.environ.get("CAREGUARD_DB_POOL_MAX", "8")))
    except ValueError:
        return 8


async def get_pool() -> Optional[Any]:
    """Return the shared open async pool, or None if unconfigured/unavailable."""
    global _POOL, _POOL_DSN
    if not is_configured():
        return None
    dsn = database_url()
    if _POOL is not None and _POOL_DSN == dsn:
        return _POOL
    try:
        from psycopg_pool import AsyncConnectionPool
    except ImportError:
        return None
    if _POOL is not None:
        try:
            await _POOL.close()
        except Exception:  # noqa: BLE001
            pass
    # open=False + explicit open() so we control lifecycle inside the event loop.
    pool = AsyncConnectionPool(dsn, min_size=_pool_min(), max_size=_pool_max(), open=False)
    await pool.open(wait=True, timeout=10.0)
    _POOL, _POOL_DSN = pool, dsn
    return _POOL


async def close_pool() -> None:
    global _POOL, _POOL_DSN
    if _POOL is not None:
        try:
            await _POOL.close()
        finally:
            _POOL, _POOL_DSN = None, None


async def ping() -> bool:
    pool = await get_pool()
    if pool is None:
        return False
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT 1")
        row = await cur.fetchone()
        return bool(row and row[0] == 1)
