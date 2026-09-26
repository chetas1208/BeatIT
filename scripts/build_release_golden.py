#!/usr/bin/env python3
"""Build a compact, secret-free release golden manifest from checked-in fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures/golden/release_demo"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    files = {
        "patient": "fixtures/hearttwin/manual_baseline.json",
        "events": "fixtures/hearttwin/ecg_synthetic_normal.csv",
        "snapshot": "fixtures/golden/probabilistic/synthetic-replay.json",
        "ensemble": "fixtures/golden/probabilistic/synthetic-replay.json",
        "scenario": "fixtures/golden/shadow_trials/synthetic-demo-case.json",
        "shadow_trial": "fixtures/golden/shadow_trials/synthetic-demo-case.json",
        "report": "fixtures/hearttwin/report_baseline.txt",
        "echo": "fixtures/hearttwin/echo_metadata_baseline.json",
    }
    checksums = {key: digest(ROOT / relative) for key, relative in files.items()}
    payload = {
        "dataset_version": "m10.5-release-demo-v1",
        "patient_id": "BeatIT-Demo-Patient-001",
        "synthetic": True,
        "provenance_classification": "synthetic_demo",
        "safety_boundary": "educational simulation only; not diagnosis or treatment",
        "source_files": files,
        "checksums": checksums,
        "capabilities": [
            "temporal_twin", "deterministic_physiology", "probabilistic_ensemble",
            "shadow_trial", "split_heart", "missing_piece", "report", "provenance",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n")
    print("RELEASE GOLDEN PASS")
    print(f"SOURCE COUNT PASS {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
