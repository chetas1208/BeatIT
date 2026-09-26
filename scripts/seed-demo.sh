#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

echo "== BeatIT deterministic demo seed =="
python scripts/create_synthetic_fixtures.py
python scripts/run_local_smoke.py

mkdir -p data/demo
python - <<'PY'
import hashlib, json
from pathlib import Path

root = Path.cwd()
paths = [
    root / "fixtures/hearttwin/manual_baseline.json",
    root / "fixtures/golden/probabilistic/fixed-only.json",
    root / "fixtures/golden/shadow_trials/synthetic-demo-case.json",
]
state = {
    "version": "m10-demo-v1",
    "fixture_status": "synthetic_demo",
    "files": {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    },
    "deterministic_core": "ready",
    "fallback_label": "PRECOMPUTED DEMO RESULT only when an expensive optional path is unavailable",
}
(root / "data/demo/state.json").write_text(json.dumps(state, indent=2) + "\n")
manifest = {
    "dataset_version": "m10.5-demo-v1",
    "generated_at_utc": "2026-09-26T00:00:00Z",
    "synthetic": True,
    "patient_id": "BeatIT-Demo-Patient-001",
    "source": "checked-in synthetic fixtures",
    "provenance_classification": "synthetic_demo",
    "fixture_ids": [path.stem for path in paths],
    "checksums": state["files"],
}
(root / "data/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Wrote data/demo/state.json")
print("Wrote data/manifest.json")
PY

echo "DEMO READY"
