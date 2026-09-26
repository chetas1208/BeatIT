#!/usr/bin/env python3
"""Repeated-trial reliability: run a paid arm with N trials on the stratified
repeat subset (config repeat_subset_size / repeat_trials). Cost-guarded."""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))
from _bench_common import RESULTS_DIR, load_config  # noqa: E402

def main() -> int:
    import pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--confirm-cost", action="store_true")
    args = ap.parse_args()
    cfg = load_config("benchmark")
    n = int(cfg.get("repeat_subset_size", 200))
    t = int(cfg.get("repeat_trials", 3))
    if not args.confirm_cost:
        print(f"Repeated trials for {args.arm}: {n} cases x {t} trials is a "
              "PAID run. Re-run with --confirm-cost after checking "
              "runners/estimate_cost.py.")
        return 2
    idx = pd.read_parquet(RESULTS_DIR / "case_index.parquet")
    cases = idx[idx["status"].isin(["eligible", "eligible_with_warning"])] \
        .sort_values("case_id")["case_id"].head(n).tolist()
    cmd = [sys.executable, str(BENCH / "runners" / "run_direct_baseline.py"),
           "--arm", args.arm, "--cases", ",".join(cases), "--trials", str(t)]
    return subprocess.call(cmd)

if __name__ == "__main__":
    raise SystemExit(main())
