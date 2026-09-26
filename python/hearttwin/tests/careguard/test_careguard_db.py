"""Durable DB layer degrades safely when Postgres is unconfigured (hermetic)."""

from __future__ import annotations

import pytest

from python.hearttwin.careguard.db import pool
from python.hearttwin.careguard.db.repository import (
    NullRepository,
    PostgresRepository,
    get_repository,
    reset_repository,
)


def test_db_unconfigured_when_no_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert pool.is_configured() is False


def test_repository_is_null_when_unconfigured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_repository()
    repo = get_repository()
    assert isinstance(repo, NullRepository)


@pytest.mark.asyncio
async def test_null_repository_noops(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    repo = NullRepository()
    assert await repo.save_case({"case_id": "x"}) is False
    assert await repo.get_case("x") is None
    assert await repo.append_audit_event({"event_id": "e"}) is False
    assert await repo.get_audit_trail("x") == []
    assert await repo.save_feedback("x", {"feedback_id": "f"}) is False


@pytest.mark.asyncio
async def test_get_pool_returns_none_when_unconfigured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert await pool.get_pool() is None
    assert await pool.ping() is False


def test_repository_is_postgres_when_configured(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("CAREGUARD_DB_ENABLED", "true")
    reset_repository()
    assert isinstance(get_repository(), PostgresRepository)
    reset_repository()
