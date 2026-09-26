#!/usr/bin/env python3
"""Exercise the real FastAPI contract against temporary durable stores."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    fixture = json.loads((ROOT / "fixtures/golden/probabilistic/synthetic-replay.json").read_text())
    with tempfile.TemporaryDirectory(prefix="beatit-m105-api-") as directory:
        os.environ["BEATIT_ENSEMBLE_DB_PATH"] = str(Path(directory) / "artifacts.sqlite3")
        os.environ["BEATIT_MISSING_PIECE_DB_PATH"] = str(Path(directory) / "missing-piece.sqlite3")
        from python.hearttwin.api import app

        with TestClient(app) as client:
            checks: list[tuple[str, int]] = []
            for path in ("/api/health/live", "/api/health/ready", "/api/v1/system-check", "/api/v1/models/status"):
                response = client.get(path)
                checks.append((path, response.status_code))
                response.raise_for_status()

            ensemble = client.post("/api/v1/twin/ensemble", json=fixture["input"])
            ensemble.raise_for_status()
            ensemble_body = ensemble.json()
            ensemble_id = ensemble_body["id"]
            scenario = {
                "id": "m105-demo-afterload",
                "label": "Synthetic educational hypothetical",
                "origin_snapshot_id": ensemble_body["origin_snapshot_id"],
                "parameters": [{
                    "parameter": "afterload_index",
                    "value": 1.2,
                    "baseline": 1.0,
                    "delta": 0.2,
                    "unit": "index",
                }],
            }
            trial = client.post("/api/v1/shadow-trials", json={"baseline_ensemble_id": ensemble_id, "scenario": scenario})
            trial.raise_for_status()
            trial_body = trial.json()
            trial_id = trial_body["id"]
            missing = client.post("/api/v1/missing-piece", json={
                "baseline_ensemble_id": ensemble_id,
                "target_metric": "stroke_volume_ml",
                "available_evidence_types": ["repeat_ecg", "repeat_echo"],
            })
            missing.raise_for_status()
            missing_body = missing.json()
            report = client.get(f"/api/v1/twin/ensemble/{ensemble_id}")
            report.raise_for_status()
            trial_reload = client.get(f"/api/v1/shadow-trials/{trial_id}")
            trial_reload.raise_for_status()
            missing_reload = client.get(f"/api/v1/missing-piece/{missing_body['provenance']['analysis_id']}")
            missing_reload.raise_for_status()

            if trial_reload.json() != trial_body or missing_reload.json() != missing_body:
                raise SystemExit("API E2E FAILED: persisted response changed on reload")
            print("API E2E PASS")
            print(f"ENDPOINT CHECKS PASS {len(checks)}")
            print(f"ENSEMBLE PASS {ensemble_id}")
            print(f"SHADOW_TRIAL PASS {trial_id} pairs={trial_body['requested_pairs']}")
            print(f"MISSING_PIECE PASS {missing_body['provenance']['analysis_id']}")
            print("PERSISTED READBACK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
