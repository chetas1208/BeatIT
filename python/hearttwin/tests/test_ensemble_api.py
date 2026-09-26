"""Focused route tests for the M5 plausible-twin ensemble API."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

import python.hearttwin.api as api_module
from python.hearttwin.api import app
from python.hearttwin.storage.ensemble_store import EnsembleStoreError

from .test_ensemble import _request, _state

client = TestClient(app)
GOLDEN_DIR = Path(__file__).parents[3] / "fixtures" / "golden" / "probabilistic"


def _ensemble_payload(baseline_vitals: dict) -> dict:
    return _request(_state(baseline_vitals), sample_count=4).model_dump(mode="json")


def _create_ensemble(baseline_vitals: dict) -> dict:
    response = client.post(
        "/api/v1/twin/ensemble",
        json=_ensemble_payload(baseline_vitals),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_create_ensemble_returns_generated_result(baseline_vitals: dict) -> None:
    body = _create_ensemble(baseline_vitals)

    assert body["id"].startswith("ensemble-")
    assert body["origin_snapshot_id"] == "snapshot-baseline"
    assert body["requested_sample_count"] == 4
    assert body["accepted_sample_count"] > 0
    assert body["samples"]
    assert body["distributions"]


def test_get_ensemble_retrieves_created_result(baseline_vitals: dict) -> None:
    created = _create_ensemble(baseline_vitals)

    response = client.get(f"/api/v1/twin/ensemble/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_ensemble_distributions_returns_distributions_and_provenance(
    baseline_vitals: dict,
) -> None:
    created = _create_ensemble(baseline_vitals)

    response = client.get(
        f"/api/v1/twin/ensemble/{created['id']}/distributions"
    )

    assert response.status_code == 200
    assert response.json() == {
        "ensemble_id": created["id"],
        "distributions": created["distributions"],
        "provenance": created["provenance"],
        "safety_disclaimer": created["safety_disclaimer"],
    }


def test_create_ensemble_rejects_invalid_request() -> None:
    response = client.post("/api/v1/twin/ensemble", json={})

    assert response.status_code == 422
    assert response.json()["detail"]


def test_create_synthetic_replay_preserves_lineage_and_warning() -> None:
    fixture = json.loads((GOLDEN_DIR / "synthetic-replay.json").read_text())

    response = client.post("/api/v1/twin/ensemble", json=fixture["input"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provenance"]["origin_quality"] == "synthetic"
    assert body["provenance"]["origin_provenance"] == fixture["input"]["origin_provenance"]
    assert body["warnings"] == [
        "Educational simulation only; not diagnosis or treatment advice."
    ]


def test_create_ensemble_rejects_observed_synthetic_replay() -> None:
    fixture = json.loads((GOLDEN_DIR / "synthetic-replay.json").read_text())
    payload = {**fixture["input"], "origin_quality": "observed"}

    response = client.post("/api/v1/twin/ensemble", json=payload)

    assert response.status_code == 422
    assert any(
        "synthetic replay provenance cannot be labeled observed" in error["msg"]
        for error in response.json()["detail"]
    )


def test_get_missing_ensemble_returns_not_found() -> None:
    response = client.get("/api/v1/twin/ensemble/ensemble-does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Ensemble not found"}


def test_get_ensemble_maps_storage_failure_to_service_unavailable(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class FailingStore:
        def get(self, _ensemble_id: str) -> None:
            raise EnsembleStoreError("database unavailable")

    monkeypatch.setattr(api_module, "_ensemble_store", FailingStore())

    response = client.get("/api/v1/twin/ensemble/ensemble-storage-failure")

    assert response.status_code == 503
    assert response.json() == {"detail": "Ensemble persistence is unavailable"}
