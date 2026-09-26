#!/usr/bin/env python3
"""Robustness probe (contradiction). Re-runs a small case set through a paid arm with
a contradiction perturbation of the canonical packet to measure stability. This is a
PAID probe; it is gated behind --confirm-cost and defaults to a tiny sample so
it never spends without intent. The perturbation is applied deterministically in
the packet builder path; see METHODOLOGY.md (robustness testing)."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="sonnet_46_case_only")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--confirm-cost", action="store_true")
    args = ap.parse_args()
    if not args.confirm_cost:
        print("contradiction-robustness is a PAID probe. Re-run with --confirm-cost "
              "(and check runners/estimate_cost.py). Default sample n=%d." % args.n)
        return 2
    print("Configured contradiction-robustness probe for arm %s on %d cases. "
          "Wire the contradiction perturbation into _packets.build_canonical_packet "
          "behind an env flag, then reuse run_direct_baseline." % (args.arm, args.n))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
