"""Measure local M6 paired-trial stages over a synthetic fixed baseline."""

from __future__ import annotations

import json
import platform
import tempfile
import time
from pathlib import Path

from python.hearttwin.ensemble import EnsembleRequest, run_ensemble
from python.hearttwin.shadow_trial_engine import ScenarioDefinition, ScenarioParameterChange, run_shadow_trial
from python.hearttwin.storage.shadow_trial_store import SQLiteShadowTrialStore

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/golden/probabilistic/fixed-only.json"
COUNTS = (50, 100, 250, 500, 1000)


def timed(function):  # type: ignore[no-untyped-def]
    started = time.perf_counter_ns()
    value = function()
    return value, (time.perf_counter_ns() - started) / 1_000_000


def main() -> None:
    source = json.loads(FIXTURE.read_text())
    rows = []
    for count in COUNTS:
        input_payload = {**source["input"], "sample_count": count}
        request = EnsembleRequest.model_validate(input_payload)
        baseline, generation_ms = timed(lambda: run_ensemble(request))
        scenario = ScenarioDefinition(
            id="afterload-plus-15",
            label="Afterload experiment +15%",
            origin_snapshot_id=baseline["origin_snapshot_id"],
            parameters=[ScenarioParameterChange(parameter="afterload_index", baseline=1.0, value=1.15, delta=0.15, unit="index")],
        )
        trial, warmup_ms = timed(lambda: run_shadow_trial(baseline, scenario, metrics=["ejection_fraction_pct", "stroke_volume_ml", "cardiac_output_l_min"]))
        core = []
        encoded = []
        persistence = []
        with tempfile.TemporaryDirectory(prefix="beatit-m6-") as directory:
            store = SQLiteShadowTrialStore(Path(directory) / "shadow.sqlite3")
            payload = trial.model_dump(mode="json")
            for _ in range(3):
                result, elapsed = timed(lambda: run_shadow_trial(baseline, scenario, metrics=["ejection_fraction_pct", "stroke_volume_ml", "cardiac_output_l_min"]))
                core.append(elapsed)
                _, encode_elapsed = timed(lambda: json.dumps(result.model_dump(mode="json"), sort_keys=True, separators=(",", ":")))
                encoded.append(encode_elapsed)
                _, save_elapsed = timed(lambda: store.save(result.id, payload))
                persistence.append(save_elapsed)
            reloaded, reload_ms = timed(lambda: store.get(trial.id))
            payload_bytes = len(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
        rows.append({
            "requested_pairs": count,
            "valid_pairs": trial.valid_pairs,
            "invalid_pairs": trial.invalid_pairs,
            "baseline_generation_ms": round(generation_ms, 3),
            "warmup_shadow_ms": round(warmup_ms, 3),
            "shadow_core_ms": [round(value, 3) for value in core],
            "json_encode_ms": [round(value, 3) for value in encoded],
            "sqlite_save_ms": [round(value, 3) for value in persistence],
            "sqlite_reload_ms": round(reload_ms, 3),
            "payload_bytes": payload_bytes,
            "trial_id": trial.id,
            "fingerprint": trial.fingerprint,
            "reload_matches": reloaded == payload,
        })
    print(json.dumps({"benchmark": "m6-shadow-trial", "fixture": str(FIXTURE.relative_to(ROOT)), "python": platform.python_version(), "platform": platform.platform(), "counts": list(COUNTS), "rows": rows}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
