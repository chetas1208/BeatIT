"""Route-level checks for persisted M8 Missing Piece analyses."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import python.hearttwin.api as api_module
from python.hearttwin.api import app
from python.hearttwin.safety import DISCLAIMER
from python.hearttwin.storage.ensemble_store import create_ensemble_store
from python.hearttwin.storage.missing_piece_store import SQLiteMissingPieceStore

from .test_ensemble import _request, _state

client = TestClient(app)


@pytest.fixture
def isolated_missing_piece_store(monkeypatch, tmp_path):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("BEATIT_ENSEMBLE_DB_PATH", str(tmp_path / "ensemble.sqlite3"))
    monkeypatch.setenv("BEATIT_MISSING_PIECE_DB_PATH", str(tmp_path / "missing-piece.sqlite3"))
    monkeypatch.setattr(api_module, "_ensemble_store", create_ensemble_store())
    monkeypatch.setattr(
        api_module,
        "_missing_piece_store",
        SQLiteMissingPieceStore(tmp_path / "missing-piece.sqlite3"),
    )


def _create_baseline(baseline_vitals: dict) -> dict:
    response = client.post(
        "/api/v1/twin/ensemble",
        json=_request(_state(baseline_vitals), seed=31, sample_count=6).model_dump(mode="json"),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_missing_piece_create_and_subresource_routes(baseline_vitals: dict, isolated_missing_piece_store) -> None:  # type: ignore[no-untyped-def]
    baseline = _create_baseline(baseline_vitals)
    created = client.post(
        "/api/v1/missing-piece",
        json={
            "baseline_ensemble_id": baseline["id"],
            "target_metric": "stroke_volume_ml",
            "available_evidence_types": ["repeat_ecg"],
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    analysis_id = body["provenance"]["analysis_id"]
    assert body["safety_disclaimer"] == DISCLAIMER
    assert body["dominant_uncertainty_drivers"]

    fetched = client.get(f"/api/v1/missing-piece/{analysis_id}")
    assert fetched.status_code == 200
    assert fetched.json()["provenance"]["analysis_id"] == analysis_id

    drivers = client.get(f"/api/v1/missing-piece/{analysis_id}/drivers")
    assert drivers.status_code == 200
    drivers_body = drivers.json()
    assert drivers_body["target_metric"] == "stroke_volume_ml"
    assert drivers_body["dominant_uncertainty_drivers"] == body["dominant_uncertainty_drivers"]
    assert drivers_body["safety_disclaimer"] == DISCLAIMER

    ranking = client.get(f"/api/v1/missing-piece/{analysis_id}/evidence-ranking")
    assert ranking.status_code == 200
    ranking_body = ranking.json()
    assert ranking_body["evidence_ranking"] == body["evidence_ranking"]
    assert ranking_body["safety_disclaimer"] == DISCLAIMER
