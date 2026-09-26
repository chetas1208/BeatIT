#!/usr/bin/env python3
"""Top-level benchmark orchestrator.

Phases (each is idempotent and resumable):
  prep    verify_models + build_case_index + build_reference_set
  free    CareGuard Arm E + ablations over eligible cases (no spend)
  paid    Sonnet 4.5/4.6 arms A-D (requires --confirm-cost; honors cost cap)
  grade   grade all present arms, aggregate, statistics
  report  charts + MD/HTML/PDF + demo summary

Examples:
  run_benchmark.py --phase prep
  run_benchmark.py --phase free --limit 200
  run_benchmark.py --phase grade --phase report
  run_benchmark.py --phase paid --arms all --confirm-cost
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
PY = sys.executable

PAID_ARMS = [
    "sonnet_45_case_only", "sonnet_46_case_only",
    "sonnet_45_evidence_grounded", "sonnet_46_evidence_grounded",
]


def run(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    return subprocess.call(cmd)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", action="append", required=True,
                    choices=["prep", "free", "paid", "grade", "report"])
    ap.add_argument("--arms", default="all")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--confirm-cost", action="store_true")
    args = ap.parse_args()

    r = BENCH / "runners"
    a = BENCH / "analysis"

    for phase in args.phase:
        if phase == "prep":
            if run([PY, str(r / "verify_models.py")]) != 0:
                print("Model verification failed — aborting.")
                return 2
            run([PY, str(r / "build_case_index.py")])
            run([PY, str(BENCH / "reference" / "build_reference_set.py")])

        elif phase == "free":
            cmd = [PY, str(r / "run_careguard.py"), "--arm", "all"]
            if args.limit:
                cmd += ["--limit", str(args.limit)]
            run(cmd)

        elif phase == "paid":
            run([PY, str(r / "estimate_cost.py")])
            if not args.confirm_cost:
                print("\nPAID phase requires --confirm-cost after reviewing the "
                      "projection above. No spend performed.")
                return 3
            arms = PAID_ARMS if args.arms == "all" else args.arms.split(",")
            for arm in arms:
                cmd = [PY, str(r / "run_direct_baseline.py"), "--arm", arm]
                if args.limit:
                    cmd += ["--limit", str(args.limit)]
                run(cmd)

        elif phase == "grade":
            run([PY, str(a / "run_analysis.py")])

        elif phase == "report":
            run([PY, str(a / "generate_charts.py")])
            run([PY, str(a / "generate_report.py")])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
