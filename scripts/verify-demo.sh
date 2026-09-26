#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python - <<'PY'
import hashlib
import json
from pathlib import Path

root = Path.cwd()
state_path = root / "data/demo/state.json"
manifest_path = root / "data/manifest.json"
golden_path = root / "fixtures/golden/release_demo/manifest.json"
if not state_path.exists() or not manifest_path.exists() or not golden_path.exists():
    raise SystemExit("DEMO VERIFY FAILED: seed state, data manifest, or release golden manifest is missing")

state = json.loads(state_path.read_text())
manifest = json.loads(manifest_path.read_text())
golden = json.loads(golden_path.read_text())
if state.get("fixture_status") != "synthetic_demo":
    raise SystemExit("DEMO VERIFY FAILED: state is not synthetic_demo")
if manifest.get("synthetic") is not True or manifest.get("provenance_classification") != "synthetic_demo":
    raise SystemExit("DEMO VERIFY FAILED: manifest is not synthetic")
if golden.get("synthetic") is not True or golden.get("provenance_classification") != "synthetic_demo":
    raise SystemExit("DEMO VERIFY FAILED: release golden manifest is not synthetic")

for relative, expected in state["files"].items():
    path = root / relative
    if not path.exists():
        raise SystemExit(f"DEMO VERIFY FAILED: missing fixture {relative}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"DEMO VERIFY FAILED: checksum mismatch for {relative}")
    if manifest.get("checksums", {}).get(relative) != actual:
        raise SystemExit(f"DEMO VERIFY FAILED: manifest mismatch for {relative}")

print("DEMO FIXTURES PASS")
print(f"SYNTHETIC DATASET PASS {manifest['dataset_version']}")
print(f"FIXTURE COUNT PASS {len(state['files'])}")
print(f"RELEASE GOLDEN PASS {golden['dataset_version']}")
PY

echo "DEMO VERIFY PASS"
