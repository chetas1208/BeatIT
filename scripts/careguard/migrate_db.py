#!/usr/bin/env python
"""Create the durable CareGuard Postgres tables (idempotent).

Loads the repo .env, then runs the migration. No-op (clean exit) when
DATABASE_URL is unset. Run: python scripts/careguard/migrate_db.py
"""

from __future__ import annotations

import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


async def _run() -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except Exception:  # noqa: BLE001
        pass
    from python.hearttwin.careguard.db import migrate, pool

    if not pool.is_configured():
        print("DATABASE_URL not set — CareGuard runs on Redis/in-memory; nothing to migrate.")
        return 0
    result = await migrate.migrate()
    print(f"CareGuard DB migration: {result}")
    await pool.close_pool()
    return 0 if result.get("migrated") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
