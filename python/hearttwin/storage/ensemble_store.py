"""Durable provider-neutral storage for computed twin ensembles.

The application layer owns the ensemble schema. This module only persists and
retrieves a JSON-compatible record by its stable ensemble identifier, allowing
the backing provider to be replaced without changing API code.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol


class EnsembleStore(Protocol):
    """Minimal persistence contract required by ensemble API consumers."""

    def save(self, ensemble_id: str, payload: Mapping[str, Any]) -> None:
        """Atomically create or replace an ensemble record."""

    def get(self, ensemble_id: str) -> dict[str, Any] | None:
        """Return an ensemble record, or ``None`` when it does not exist."""


class EnsembleStoreError(RuntimeError):
    """Raised when a persisted ensemble cannot be decoded safely."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS twin_ensembles (
    ensemble_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _validate_id(ensemble_id: str) -> None:
    if not isinstance(ensemble_id, str) or not ensemble_id.strip():
        raise ValueError("ensemble_id must be a non-empty string")


class SQLiteEnsembleStore:
    """SQLite implementation of :class:`EnsembleStore`.

    A connection is opened per operation so separate processes and application
    restarts observe the same database. SQLite's transaction context and a
    single upsert statement make replacement atomic; failed serialization or
    database writes leave the prior record unchanged.
    """

    def __init__(self, database: str | Path) -> None:
        self._database = str(database)
        if self._database == ":memory:":
            raise ValueError("SQLiteEnsembleStore requires a file-backed database")
        database_path = Path(self._database)
        database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            database_path.parent.chmod(0o700)
        except OSError:
            pass
        self._database = str(database_path)
        self._initialize()
        try:
            database_path.chmod(0o600)
        except OSError:
            pass

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database, timeout=5.0)
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(_SCHEMA)

    def save(self, ensemble_id: str, payload: Mapping[str, Any]) -> None:
        """Atomically create or replace a JSON-compatible ensemble record."""

        _validate_id(ensemble_id)
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")

        # Serialize before opening a write transaction. A non-JSON value can
        # therefore never partially modify an existing record.
        encoded = json.dumps(dict(payload), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        timestamp = _timestamp()

        try:
            with closing(self._connect()) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO twin_ensembles
                            (ensemble_id, payload_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT (ensemble_id) DO UPDATE SET
                            payload_json = excluded.payload_json,
                            updated_at = excluded.updated_at
                        """,
                        (ensemble_id, encoded, timestamp, timestamp),
                    )
        except sqlite3.Error as exc:
            raise EnsembleStoreError("unable to persist ensemble") from exc

    def get(self, ensemble_id: str) -> dict[str, Any] | None:
        """Return a decoded ensemble record, or ``None`` if it is absent."""

        _validate_id(ensemble_id)
        try:
            with closing(self._connect()) as connection:
                row = connection.execute(
                    "SELECT payload_json FROM twin_ensembles WHERE ensemble_id = ?",
                    (ensemble_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise EnsembleStoreError("unable to retrieve ensemble") from exc

        if row is None:
            return None
        try:
            payload = json.loads(row[0])
        except (TypeError, json.JSONDecodeError) as exc:
            raise EnsembleStoreError(f"invalid persisted ensemble: {ensemble_id}") from exc
        if not isinstance(payload, dict):
            raise EnsembleStoreError(f"persisted ensemble is not an object: {ensemble_id}")
        return payload


def create_ensemble_store() -> EnsembleStore:
    """Create the restart-safe local provider used by the API."""
    provider = os.environ.get("BEATIT_ENSEMBLE_STORE", "sqlite").strip().lower()
    if provider != "sqlite":
        raise ValueError("BEATIT_ENSEMBLE_STORE must be sqlite; memory storage is not durable")
    return SQLiteEnsembleStore(os.environ.get("BEATIT_ENSEMBLE_DB_PATH", "data/beatit-ensembles.sqlite3"))
