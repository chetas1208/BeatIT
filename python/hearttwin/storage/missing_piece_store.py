"""Restart-safe immutable SQLite persistence for M8 analyses."""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from python.hearttwin.missing_piece.contracts import MissingPieceResult

_MAX_ANALYSIS_ID_LENGTH = 128
_SENSITIVE_KEY_PARTS = (
    "address",
    "api_key",
    "authorization",
    "cookie",
    "dob",
    "email",
    "mrn",
    "password",
    "patient",
    "phone",
    "secret",
    "ssn",
    "token",
)


class MissingPieceStore(Protocol):
    def save(self, analysis_id: str, payload: Mapping[str, Any]) -> None: ...
    def get(self, analysis_id: str) -> dict[str, Any] | None: ...


class MissingPieceStoreError(RuntimeError):
    """Raised when an analysis cannot be persisted or decoded."""


def _validate_id(analysis_id: str) -> str:
    if not isinstance(analysis_id, str) or not analysis_id.strip():
        raise ValueError("analysis_id must be a non-empty string")
    normalized = analysis_id.strip()
    if len(normalized) > _MAX_ANALYSIS_ID_LENGTH:
        raise ValueError("analysis_id is too long")
    if any(ord(character) < 32 for character in normalized):
        raise ValueError("analysis_id must not contain control characters")
    return normalized


def _reject_sensitive_keys(value: object) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(part in normalized for part in _SENSITIVE_KEY_PARTS):
                raise MissingPieceStoreError("Missing Piece payload contains a forbidden sensitive field")
            _reject_sensitive_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_sensitive_keys(nested)


def _canonical_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    try:
        result = MissingPieceResult.model_validate(payload)
        canonical = result.model_dump(mode="json")
    except (ValidationError, TypeError, ValueError) as exc:
        raise MissingPieceStoreError("payload is not a valid Missing Piece response") from exc
    _reject_sensitive_keys(canonical)
    return canonical


def _encode(payload: Mapping[str, Any]) -> str:
    canonical = _canonical_payload(payload)
    try:
        return json.dumps(canonical, allow_nan=False, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError, OverflowError) as exc:
        raise MissingPieceStoreError("Missing Piece payload is not JSON serializable") from exc


class SQLiteMissingPieceStore:
    def __init__(self, database: str | Path) -> None:
        if str(database) == ":memory:":
            raise ValueError("Missing Piece storage requires a file-backed database")
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
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS missing_piece_results (analysis_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL, created_at TEXT NOT NULL)"
            )

    def save(self, analysis_id: str, payload: Mapping[str, Any]) -> None:
        analysis_id = _validate_id(analysis_id)
        encoded = _encode(payload)
        now = datetime.now(UTC).isoformat(timespec="microseconds")
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute(
                    "INSERT INTO missing_piece_results (analysis_id, payload_json, created_at) VALUES (?, ?, ?) ON CONFLICT (analysis_id) DO NOTHING",
                    (analysis_id, encoded, now),
                )
                row = connection.execute(
                    "SELECT payload_json FROM missing_piece_results WHERE analysis_id = ?", (analysis_id,)
                ).fetchone()
                if row is None:
                    raise MissingPieceStoreError("analysis disappeared during persistence")
                if row[0] != encoded:
                    raise MissingPieceStoreError("analysis IDs are immutable")
        except sqlite3.Error as exc:
            raise MissingPieceStoreError("unable to persist Missing Piece analysis") from exc

    def get(self, analysis_id: str) -> dict[str, Any] | None:
        analysis_id = _validate_id(analysis_id)
        try:
            with closing(self._connect()) as connection:
                row = connection.execute(
                    "SELECT payload_json FROM missing_piece_results WHERE analysis_id = ?", (analysis_id,)
                ).fetchone()
        except sqlite3.Error as exc:
            raise MissingPieceStoreError("unable to retrieve Missing Piece analysis") from exc
        if row is None:
            return None
        try:
            payload = json.loads(row[0])
            if not isinstance(payload, Mapping):
                raise TypeError("persisted payload is not an object")
            return _canonical_payload(payload)
        except (TypeError, json.JSONDecodeError, MissingPieceStoreError) as exc:
            raise MissingPieceStoreError(f"invalid persisted Missing Piece analysis: {analysis_id}") from exc


def create_missing_piece_store() -> MissingPieceStore:
    path = os.environ.get("BEATIT_MISSING_PIECE_DB_PATH", os.environ.get("BEATIT_ENSEMBLE_DB_PATH", "data/beatit-ensembles.sqlite3"))
    return SQLiteMissingPieceStore(path)


__all__ = ["MissingPieceStore", "MissingPieceStoreError", "SQLiteMissingPieceStore", "create_missing_piece_store"]
