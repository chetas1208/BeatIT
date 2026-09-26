#!/usr/bin/env python3
"""Verify the generated 500-profile cohort without regenerating it."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "data" / "synthetic_cohort_500"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit("COHORT VERIFY FAILED: manifest missing")
    manifest = json.loads(manifest_path.read_text())
    profiles = sorted((root / "profiles").glob("BEATIT-SYN-*.json"))
    profile_ids = [json.loads(path.read_text())["profile_id"] for path in profiles]
    checksums = json.loads((root / "checksums.json").read_text())
    checksum_failures = [name for name, expected in checksums.items() if sha256(root / name) != expected]
    invariant_failures: list[str] = []
    provenance_failures: list[str] = []
    for profile_path in profiles:
        profile = json.loads(profile_path.read_text())
        if profile.get("synthetic") is not True or profile.get("provenance", {}).get("source_type") != "synthetic":
            provenance_failures.append(profile_path.name)
        result_path = root / "derived" / profile_path.name
        result = json.loads(result_path.read_text())
        state = result.get("state", {})
        measurements = state.get("measurements", {})
        def value(name: str) -> float:
            return float(measurements[name]["value"])
        try:
            edv, esv = value("edv_ml"), value("esv_ml")
            ef, sv, co = value("ejection_fraction_pct"), value("stroke_volume_ml"), value("cardiac_output_l_min")
            hr = value("heart_rate_bpm")
            if not all(math.isfinite(x) for x in (edv, esv, ef, sv, co, hr)):
                raise ValueError("non-finite metric")
            if not (edv > esv > 0 and abs(sv - (edv - esv)) < 0.02 and abs(ef - (sv / edv * 100.0)) < 0.02):
                raise ValueError("volume/EF invariant")
        except (KeyError, TypeError, ValueError) as exc:
            invariant_failures.append(f"{profile_path.name}:{exc}")
    with sqlite3.connect(root / "beatit_cohort.sqlite3") as conn:
        persisted = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
        successful = conn.execute("SELECT COUNT(*) FROM profiles WHERE status IN ('success', 'warning')").fetchone()[0]
    restart = subprocess.run(
        [sys.executable, "-c", "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute('SELECT COUNT(*) FROM profiles').fetchone()[0])", str(root / "beatit_cohort.sqlite3")],
        check=False,
        capture_output=True,
        text=True,
    )
    restart_count = restart.stdout.strip()
    checks = {
        "profiles": len(profiles) == 500,
        "unique_ids": len(set(profile_ids)) == 500 and set(profile_ids) == {f"BEATIT-SYN-{i:04d}" for i in range(1, 501)},
        "synthetic": manifest.get("synthetic") is True,
        "manifest_count": manifest.get("profile_count") == 500,
        "fhir": manifest.get("fhir_valid") == 500,
        "ingestion": manifest.get("beatit_ingestion_success") == 500 and successful == 500,
        "database": persisted == 500,
        "restart_readback": restart.returncode == 0 and restart_count == "500",
        "provenance": not provenance_failures,
        "physiological_invariants": not invariant_failures,
        "checksums": not checksum_failures,
    }
    for name, passed in checks.items():
        print(f"{name.upper():<24} {'PASS' if passed else 'FAIL'}")
    if not all(checks.values()):
        if checksum_failures:
            print("CHECKSUM FAILURES", ",".join(checksum_failures[:5]))
        if invariant_failures:
            print("INVARIANT FAILURES", ",".join(invariant_failures[:5]))
        if provenance_failures:
            print("PROVENANCE FAILURES", ",".join(provenance_failures[:5]))
        raise SystemExit("COHORT VERIFY FAILED")
    print("COHORT READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
