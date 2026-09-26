"""Restart-safe SQLite persistence for M6 Shadow Trial records."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol


class ShadowTrialStore(Protocol):
    """Minimal durable contract for immutable Shadow Trial records."""

    def save(self, trial_id: str, payload: Mapping[str, Any]) -> None:
        """Create a record, or accept an exact replay of the same record."""

    def get(self, trial_id: str) -> dict[str, Any] | None:
        """Return a record, or ``None`` when it does not exist."""


class ShadowTrialStoreError(RuntimeError):
    """Raised when a Shadow Trial cannot be persisted or decoded."""


def _validate_id(trial_id: str) -> None:
    if not isinstance(trial_id, str) or not trial_id.strip():
        raise ValueError("trial_id must be a non-empty string")


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _encode_payload(payload: Mapping[str, Any]) -> str:
    """Return the canonical JSON representation used for identity comparison."""

    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    return json.dumps(
        dict(payload),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


class SQLiteShadowTrialStore:
    """SQLite implementation with create-once, immutable trial semantics.

    A connection is opened per operation so records remain visible after
    process restarts. A repeated write is accepted only when its canonical
    JSON payload exactly matches the already persisted record.
    """

    def __init__(self, database: str | Path) -> None:
        if str(database) == ":memory:":
            raise ValueError("Shadow Trial storage requires a file-backed database")
        path = Path(database)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            path.parent.chmod(0o700)
        except OSError:
            pass
        self._database = str(path)
        self._initialize()
        try:
            path.chmod(0o600)
        except OSError:
            pass

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database, timeout=5.0)
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS shadow_trials (
                        trial_id TEXT PRIMARY KEY,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )

    def save(self, trial_id: str, payload: Mapping[str, Any]) -> None:
        _validate_id(trial_id)
        encoded = _encode_payload(payload)
        now = _timestamp()
        try:
            with closing(self._connect()) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO shadow_trials (trial_id, payload_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT (trial_id) DO NOTHING
                        """,
                        (trial_id, encoded, now, now),
                    )
                    row = connection.execute(
                        "SELECT payload_json FROM shadow_trials WHERE trial_id = ?",
                        (trial_id,),
                    ).fetchone()
                    if row is None:
                        raise ShadowTrialStoreError("shadow trial disappeared during persistence")
                    if row[0] != encoded:
                        raise ShadowTrialStoreError("shadow trial IDs are immutable")
        except sqlite3.Error as exc:
            raise ShadowTrialStoreError("unable to persist shadow trial") from exc

    def get(self, trial_id: str) -> dict[str, Any] | None:
        _validate_id(trial_id)
        try:
            with closing(self._connect()) as connection:
                row = connection.execute(
                    "SELECT payload_json FROM shadow_trials WHERE trial_id = ?",
                    (trial_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise ShadowTrialStoreError("unable to retrieve shadow trial") from exc
        if row is None:
            return None
        try:
            payload = json.loads(row[0])
        except (TypeError, json.JSONDecodeError) as exc:
            raise ShadowTrialStoreError(f"invalid persisted shadow trial: {trial_id}") from exc
        if not isinstance(payload, dict):
            raise ShadowTrialStoreError(f"persisted shadow trial is not an object: {trial_id}")
        return payload


def create_shadow_trial_store() -> ShadowTrialStore:
    provider = os.environ.get("BEATIT_ENSEMBLE_STORE", "sqlite").strip().lower()
    if provider != "sqlite":
        raise ValueError("BEATIT_ENSEMBLE_STORE must be sqlite for Shadow Trial persistence")
    return SQLiteShadowTrialStore(os.environ.get("BEATIT_ENSEMBLE_DB_PATH", "data/beatit-ensembles.sqlite3"))
