"""Focused durability and transaction tests for the SQLite ensemble store."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from python.hearttwin.storage.ensemble_store import SQLiteEnsembleStore


def test_missing_record_returns_none(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteEnsembleStore(tmp_path / "nested" / "ensembles.sqlite3")

    assert store.get("missing") is None


def test_save_and_get_round_trip_uses_parameterized_values(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteEnsembleStore(tmp_path / "ensembles.sqlite3")
    payload = {
        "origin_snapshot_id": "snapshot-'quoted'",
        "samples": [{"id": "sample-1", "outputs": {"ef": 0.61}}],
        "warnings": ["synthetic input"],
    }

    store.save("ensemble-'quoted'", payload)

    assert store.get("ensemble-'quoted'") == payload


def test_save_replaces_record_atomically(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteEnsembleStore(tmp_path / "ensembles.sqlite3")
    store.save("ensemble-1", {"version": 1, "samples": [1, 2]})

    store.save("ensemble-1", {"version": 2, "samples": [3]})

    assert store.get("ensemble-1") == {"version": 2, "samples": [3]}


def test_failed_serialization_does_not_replace_existing_record(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteEnsembleStore(tmp_path / "ensembles.sqlite3")
    original = {"version": 1}
    store.save("ensemble-1", original)

    with pytest.raises(TypeError):
        store.save("ensemble-1", {"invalid": object()})

    assert store.get("ensemble-1") == original


def test_record_survives_store_recreation(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "ensembles.sqlite3"
    SQLiteEnsembleStore(database).save("ensemble-1", {"persisted": True, "count": 2})

    restarted_store = SQLiteEnsembleStore(database)

    assert restarted_store.get("ensemble-1") == {"persisted": True, "count": 2}


def test_record_survives_separate_python_process(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "ensembles.sqlite3"
    repository_root = Path(__file__).resolve().parents[3]
    environment = os.environ.copy()
    pythonpath = [str(repository_root)]
    if environment.get("PYTHONPATH"):
        pythonpath.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(pythonpath)
    payload = {"persisted": True, "count": 2}

    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "from python.hearttwin.storage.ensemble_store import SQLiteEnsembleStore; "
                "SQLiteEnsembleStore(sys.argv[1]).save('ensemble-process', "
                "{'persisted': True, 'count': 2})"
            ),
            str(database),
        ],
        cwd=repository_root,
        env=environment,
        check=True,
    )

    reader = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; import sys; "
                "from python.hearttwin.storage.ensemble_store import SQLiteEnsembleStore; "
                "print(json.dumps(SQLiteEnsembleStore(sys.argv[1]).get('ensemble-process'), "
                "sort_keys=True))"
            ),
            str(database),
        ],
        cwd=repository_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(reader.stdout) == payload


def test_in_memory_database_is_rejected_to_preserve_durability() -> None:
    with pytest.raises(ValueError, match="file-backed"):
        SQLiteEnsembleStore(":memory:")


@pytest.mark.parametrize("invalid_id", ["", "   ", None])
def test_ids_must_be_non_empty_strings(tmp_path, invalid_id) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteEnsembleStore(tmp_path / "ensembles.sqlite3")

    with pytest.raises(ValueError):
        store.get(invalid_id)
