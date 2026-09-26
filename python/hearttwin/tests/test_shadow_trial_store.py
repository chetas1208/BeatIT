from __future__ import annotations

import pytest

from python.hearttwin.storage.shadow_trial_store import SQLiteShadowTrialStore, ShadowTrialStoreError


def test_shadow_trial_round_trip_survives_new_store(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "shadow.sqlite3"
    payload = {"id": "trial-1", "paired_results": [], "status": "complete"}
    SQLiteShadowTrialStore(database).save("trial-1", payload)
    assert SQLiteShadowTrialStore(database).get("trial-1") == payload


def test_same_payload_replay_is_idempotent_and_order_independent(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteShadowTrialStore(tmp_path / "shadow.sqlite3")
    store.save("trial-1", {"fingerprint": "same", "metadata": {"b": 2, "a": 1}})

    store.save("trial-1", {"metadata": {"a": 1, "b": 2}, "fingerprint": "same"})

    assert store.get("trial-1") == {
        "fingerprint": "same",
        "metadata": {"b": 2, "a": 1},
    }


def test_different_payload_cannot_overwrite_existing_trial(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteShadowTrialStore(tmp_path / "shadow.sqlite3")
    original = {"fingerprint": "same", "version": 1}
    store.save("trial-1", original)

    with pytest.raises(ShadowTrialStoreError, match="immutable"):
        store.save("trial-1", {"fingerprint": "different", "version": 2})

    assert store.get("trial-1") == original


def test_invalid_payload_cannot_replace_existing_trial(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteShadowTrialStore(tmp_path / "shadow.sqlite3")
    original = {"fingerprint": "same"}
    store.save("trial-1", original)

    with pytest.raises(TypeError):
        store.save("trial-1", {"invalid": object()})

    assert store.get("trial-1") == original


def test_non_finite_payload_cannot_be_persisted(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteShadowTrialStore(tmp_path / "shadow.sqlite3")

    with pytest.raises(ValueError, match="Out of range float values"):
        store.save("trial-1", {"delta": float("nan")})

    assert store.get("trial-1") is None


def test_persisted_json_is_canonical_and_restart_safe(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "shadow.sqlite3"
    payload = {"z": 3, "a": [1, {"y": 2, "x": 1}]}
    SQLiteShadowTrialStore(database).save("trial-1", payload)

    restarted_store = SQLiteShadowTrialStore(database)
    restarted_store.save("trial-1", {"a": [1, {"x": 1, "y": 2}], "z": 3})

    assert restarted_store.get("trial-1") == payload


def test_payload_must_be_a_mapping(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteShadowTrialStore(tmp_path / "shadow.sqlite3")

    with pytest.raises(TypeError, match="payload must be a mapping"):
        store.save("trial-1", ["not", "a", "mapping"])  # type: ignore[arg-type]


def test_shadow_trial_memory_storage_is_rejected() -> None:
    with pytest.raises(ValueError, match="file-backed"):
        SQLiteShadowTrialStore(":memory:")
