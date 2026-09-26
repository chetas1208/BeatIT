#!/usr/bin/env python3
"""Repeatable local failure-injection probe (synthetic inputs only)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/golden/probabilistic/synthetic-replay.json"

_OVERRIDES = {
    "INTELLIGENCE_PROVIDER": "disabled",
    "MODEL_ENABLED": "false",
    "VISTA3D_ENABLED": "false",
    "CAREGUARD_VISTA_ENABLED": "false",
}


def _apply_overrides() -> dict[str, str | None]:
    saved: dict[str, str | None] = {}
    for key, value in _OVERRIDES.items():
        saved[key] = os.environ.get(key)
        os.environ[key] = value
    for key in list(os.environ):
        if key.startswith(("OPENAI_", "REDIS_", "UPSTASH_", "WANDB_")):
            saved[key] = os.environ.pop(key, None)
    return saved


def _restore(saved: dict[str, str | None]) -> None:
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def main() -> int:
    fixture = json.loads(FIXTURE.read_text())
    saved = _apply_overrides()
    failures: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="beatit-failure-") as directory:
            os.environ["BEATIT_ENSEMBLE_DB_PATH"] = str(Path(directory) / "ens.sqlite3")
            os.environ["BEATIT_MISSING_PIECE_DB_PATH"] = str(Path(directory) / "mp.sqlite3")

            from fastapi.testclient import TestClient

            import python.hearttwin.api as api_module
            from python.hearttwin.storage.shadow_trial_store import ShadowTrialStoreError

            with TestClient(api_module.app) as client:
                intel = client.get("/api/v1/intelligence/status")
                if intel.status_code != 200 or intel.json().get("enabled") is not False:
                    failures.append("model_disabled")
                if not intel.json().get("safety_disclaimer"):
                    failures.append("model_disabled_disclaimer")

                sys_check = client.get("/api/v1/system-check")
                if sys_check.status_code != 200:
                    failures.append("offline_system_check")

                missing = client.get("/api/v1/twin/ensemble/ensemble-does-not-exist")
                if missing.status_code != 404:
                    failures.append("invalid_ensemble")

                created = client.post("/api/v1/twin/ensemble", json=fixture["input"])
                if created.status_code != 200:
                    failures.append("ensemble_create")
                else:
                    ensemble_id = created.json()["id"]
                    origin = created.json()["origin_snapshot_id"]
                    bad = client.post(
                        "/api/v1/shadow-trials",
                        json={
                            "baseline_ensemble_id": ensemble_id,
                            "scenario": {
                                "id": "bad-afterload",
                                "label": "bounds test",
                                "origin_snapshot_id": origin,
                                "parameters": [{
                                    "parameter": "afterload_index",
                                    "value": 2.5,
                                    "baseline": 1.0,
                                    "delta": 1.5,
                                    "unit": "index",
                                }],
                            },
                        },
                    )
                    if bad.status_code != 422:
                        failures.append("invalid_scenario")

                class FailingGetStore:
                    def get(self, _trial_id: str) -> None:
                        raise ShadowTrialStoreError("database unavailable")

                    def save(self, _trial_id: str, _payload: dict) -> None:
                        return None

                original_store = api_module._shadow_trial_store
                api_module._shadow_trial_store = FailingGetStore()
                try:
                    unavailable = client.get("/api/v1/shadow-trials/trial-backend-unavailable")
                finally:
                    api_module._shadow_trial_store = original_store
                if unavailable.status_code != 503:
                    failures.append("backend_unavailable")
                body = unavailable.json()
                if body.get("detail") != "Shadow Trial persistence is unavailable":
                    failures.append("backend_unavailable_detail")
                if not body.get("safety_disclaimer"):
                    failures.append("backend_unavailable_disclaimer")
    finally:
        _restore(saved)

    if failures:
        print("FAILURE INJECTION FAIL", ",".join(failures))
        return 1
    print("FAILURE INJECTION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
