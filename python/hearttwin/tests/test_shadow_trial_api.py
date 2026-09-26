"""Route-level checks for the persisted M6 Shadow Trial contract."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

import python.hearttwin.api as api_module
from python.hearttwin.api import app
from python.hearttwin.safety import DISCLAIMER
from python.hearttwin.storage.shadow_trial_store import ShadowTrialStoreError, SQLiteShadowTrialStore

from .test_ensemble import _request, _state


client = TestClient(app)


@pytest.fixture
def isolated_shadow_store(monkeypatch, tmp_path):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(api_module, "_shadow_trial_store", SQLiteShadowTrialStore(tmp_path / "shadow-trials.sqlite3"))


def _create_baseline(baseline_vitals: dict) -> dict:
    response = client.post(
        "/api/v1/twin/ensemble",
        json=_request(_state(baseline_vitals), seed=31, sample_count=4).model_dump(mode="json"),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _scenario(origin_snapshot_id: str) -> dict:
    return {
        "id": "afterload-120",
        "label": "Bounded afterload hypothetical",
        "origin_snapshot_id": origin_snapshot_id,
        "parameters": [
            {
                "parameter": "afterload_index",
                "value": 1.2,
                "baseline": 1.0,
                "delta": 0.2,
                "unit": "index",
            }
        ],
    }


def test_shadow_trial_create_and_retrieve_routes(baseline_vitals: dict, isolated_shadow_store) -> None:  # type: ignore[no-untyped-def]
    baseline = _create_baseline(baseline_vitals)
    response = client.post(
        "/api/v1/shadow-trials",
        json={"baseline_ensemble_id": baseline["id"], "scenario": _scenario(baseline["origin_snapshot_id"])},
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "complete"
    assert result["requested_pairs"] == 4
    assert result["valid_pairs"] == 4
    assert result["definition"]["baseline_ensemble_id"] == baseline["id"]
    assert result["safety_disclaimer"] == DISCLAIMER

    fetched = client.get(f"/api/v1/shadow-trials/{result['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == result
    assert fetched.json()["safety_disclaimer"] == DISCLAIMER

    effects = client.get(f"/api/v1/shadow-trials/{result['id']}/effects")
    assert effects.status_code == 200
    assert effects.json()["effect_distributions"]
    assert effects.json()["safety_disclaimer"] == DISCLAIMER

    sample_id = result["paired_results"][0]["sample_id"]
    pair = client.get(f"/api/v1/shadow-trials/{result['id']}/pairs/{sample_id}")
    assert pair.status_code == 200
    assert pair.json()["pair"]["sample_id"] == sample_id
    assert pair.json()["safety_disclaimer"] == DISCLAIMER


def test_shadow_trial_missing_baseline_and_bad_bounds_are_explicit(baseline_vitals: dict, isolated_shadow_store) -> None:  # type: ignore[no-untyped-def]
    missing = client.post(
        "/api/v1/shadow-trials",
        json={
            "baseline_ensemble_id": "ensemble-does-not-exist",
            "scenario": {"id": "s1", "label": "No baseline"},
        },
    )
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Baseline ensemble not found", "safety_disclaimer": DISCLAIMER}

    baseline = _create_baseline(baseline_vitals)
    invalid = _scenario(baseline["origin_snapshot_id"])
    invalid["parameters"][0]["value"] = 2.5
    invalid["parameters"][0]["delta"] = 1.5
    response = client.post(
        "/api/v1/shadow-trials",
        json={"baseline_ensemble_id": baseline["id"], "scenario": invalid},
    )
    assert response.status_code == 422
    assert "within" in response.json()["detail"]


def test_shadow_trial_retrieval_missing_resources_are_404() -> None:
    for path, detail in (
        ("/api/v1/shadow-trials/trial-does-not-exist", "Shadow Trial not found"),
        ("/api/v1/shadow-trials/trial-does-not-exist/effects", "Shadow Trial not found"),
        (
            "/api/v1/shadow-trials/trial-does-not-exist/pairs/sample-0",
            "Shadow Trial not found",
        ),
    ):
        response = client.get(path)
        assert response.status_code == 404
        assert response.json() == {"detail": detail, "safety_disclaimer": DISCLAIMER}


def test_shadow_trial_repeated_create_is_idempotent(
    baseline_vitals: dict,
    isolated_shadow_store,
) -> None:  # type: ignore[no-untyped-def]
    baseline = _create_baseline(baseline_vitals)
    payload = {
        "baseline_ensemble_id": baseline["id"],
        "scenario": _scenario(baseline["origin_snapshot_id"]),
    }

    first = client.post("/api/v1/shadow-trials", json=payload)
    second = client.post("/api/v1/shadow-trials", json=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json() == first.json()


def test_shadow_trial_create_maps_persistence_failure_to_service_unavailable(
    baseline_vitals: dict,
    isolated_shadow_store,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    baseline = _create_baseline(baseline_vitals)

    class FailingStore:
        def save(self, _trial_id: str, _payload: dict) -> None:
            raise ShadowTrialStoreError("database unavailable")

        def get(self, _trial_id: str) -> None:
            return None

    monkeypatch.setattr(api_module, "_shadow_trial_store", FailingStore())

    response = client.post(
        "/api/v1/shadow-trials",
        json={
            "baseline_ensemble_id": baseline["id"],
            "scenario": _scenario(baseline["origin_snapshot_id"]),
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Shadow Trial persistence is unavailable",
        "safety_disclaimer": DISCLAIMER,
    }


def test_shadow_trial_validation_errors_keep_safety_disclaimer(isolated_shadow_store) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/api/v1/shadow-trials", json={"baseline_ensemble_id": "missing"})

    assert response.status_code == 422
    assert response.json()["safety_disclaimer"] == DISCLAIMER
    assert response.json()["detail"]


def test_shadow_trial_read_routes_reject_malformed_persisted_payload(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class MalformedStore:
        def get(self, _trial_id: str) -> dict:
            return {"id": "tampered", "safety_disclaimer": "tampered"}

    monkeypatch.setattr(api_module, "_shadow_trial_store", MalformedStore())
    response = client.get("/api/v1/shadow-trials/tampered/effects")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Shadow Trial persistence is unavailable",
        "safety_disclaimer": DISCLAIMER,
    }
