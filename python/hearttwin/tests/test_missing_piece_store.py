from __future__ import annotations

import pytest

from python.hearttwin.missing_piece.contracts import (
    MissingPieceProvenance,
    MissingPieceResult,
)
from python.hearttwin.safety import DISCLAIMER
from python.hearttwin.storage.missing_piece_store import (
    MissingPieceStoreError,
    SQLiteMissingPieceStore,
)


def _payload() -> dict[str, object]:
    return MissingPieceResult(
        target_metric="stroke_volume_ml",
        limitations=["Local deterministic sensitivity only."],
        provenance=MissingPieceProvenance(
            analysis_id="analysis-1",
            sensitivity_method="finite_difference",
            ranking_method="evidence-priority-score-v1",
            assumptions=["Synthetic test fixture."],
        ),
    ).model_dump(mode="json")


def test_missing_piece_store_is_restart_safe_and_immutable(tmp_path) -> None:
    database = tmp_path / "missing-piece.sqlite3"
    payload = _payload()
    SQLiteMissingPieceStore(database).save("analysis-1", payload)
    reopened = SQLiteMissingPieceStore(database)
    assert reopened.get("analysis-1") == payload
    reopened.save("analysis-1", payload)
    with pytest.raises(MissingPieceStoreError):
        different = dict(payload)
        different["target_metric"] = "ejection_fraction_pct"
        reopened.save("analysis-1", different)


def test_missing_piece_store_returns_copy_and_rejects_sensitive_or_invalid_payload(tmp_path) -> None:
    database = tmp_path / "missing-piece.sqlite3"
    store = SQLiteMissingPieceStore(database)
    payload = _payload()
    store.save(" analysis-1 ", payload)

    loaded = store.get("analysis-1")
    assert loaded is not None
    loaded["completeness"] = {"changed": True}
    assert store.get("analysis-1") == payload

    with pytest.raises(MissingPieceStoreError):
        store.save("analysis-2", {**payload, "safety_disclaimer": "not canonical"})
    with pytest.raises(MissingPieceStoreError):
        store.save("analysis-3", {**payload, "completeness": {"patient_email": "redacted"}})
    with pytest.raises(MissingPieceStoreError):
        store.save("analysis-4", {**payload, "unexpected": "field"})

    assert payload["safety_disclaimer"] == DISCLAIMER


def test_missing_piece_store_rejects_memory_database() -> None:
    with pytest.raises(ValueError):
        SQLiteMissingPieceStore(":memory:")
