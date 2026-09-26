#!/usr/bin/env python3
"""Re-run trials that ended in api_failure or schema_failure for a paid arm.
Reads results/raw/<arm>.ndjson, finds failed (case,trial), and re-invokes
run_direct_baseline for just those cases (resumable, cost-guarded)."""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))
from _bench_common import RESULTS_DIR, read_jsonl  # noqa: E402

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    args = ap.parse_args()
    rows = read_jsonl(RESULTS_DIR / "raw" / f"{args.arm}.ndjson")
    failed = sorted({r["case_id"] for r in rows
                     if r.get("status") in ("api_failure", "schema_failure")})
    if not failed:
        print(f"No failed trials for {args.arm}.")
        return 0
    print(f"Re-running {len(failed)} failed cases for {args.arm} ...")
    # remove failed rows so the resumable runner redoes them
    keep = [r for r in rows if r.get("status") not in
            ("api_failure", "schema_failure")]
    from _bench_common import write_jsonl
    write_jsonl(RESULTS_DIR / "raw" / f"{args.arm}.ndjson", keep)
    cmd = [sys.executable, str(BENCH / "runners" / "run_direct_baseline.py"),
           "--arm", args.arm, "--cases", ",".join(failed)]
    return subprocess.call(cmd)

if __name__ == "__main__":
    raise SystemExit(main())
