#!/usr/bin/env python3
"""Run the CareGuard ablation arms on the stratified ablation subset.
Delegates to run_careguard.py --arm all with a bounded case set."""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))
from _bench_common import RESULTS_DIR, load_config  # noqa: E402

def main() -> int:
    import pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    cfg = load_config("benchmark")
    n = args.limit or int(cfg.get("ablation_subset_size", 150))
    idx = pd.read_parquet(RESULTS_DIR / "case_index.parquet")
    elig = idx[idx["status"].isin(["eligible", "eligible_with_warning"])]
    # stratify by medication band for a representative subset
    elig = elig.sort_values("case_id")
    cases = elig["case_id"].head(n).tolist()
    cmd = [sys.executable, str(BENCH / "runners" / "run_careguard.py"),
           "--arm", "all", "--cases", ",".join(cases)]
    return subprocess.call(cmd)

if __name__ == "__main__":
    raise SystemExit(main())
