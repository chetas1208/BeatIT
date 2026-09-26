#!/usr/bin/env python3
"""Project the cost of the paid model arms before spending, from measured pilot
tokens (falling back to packet-size estimates). Prints the projection, compares
it to the configured cap, and NEVER spends. The full paid run requires explicit
cost confirmation (config require_cost_confirmation).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))
from _bench_common import (  # noqa: E402
    CASES_DIR, PRICING, RESULTS_DIR, cost_usd, load_config, read_jsonl,
)

PAID_ARMS = {
    "sonnet_45_case_only": ("claude-sonnet-4-5-20250929", "case_only"),
    "sonnet_46_case_only": ("claude-sonnet-4-6", "case_only"),
    "sonnet_45_evidence_grounded": ("claude-sonnet-4-5-20250929", "evidence"),
    "sonnet_46_evidence_grounded": ("claude-sonnet-4-6", "evidence"),
}


def _pilot_tokens(mode: str) -> tuple[float, float, int]:
    """mean (input, output) tokens from any pilot trials of this mode."""
    ins, outs = [], []
    for arm, (model, m) in PAID_ARMS.items():
        if m != mode:
            continue
        for r in read_jsonl(RESULTS_DIR / "raw" / f"{arm}.ndjson"):
            u = r.get("usage") or {}
            if u.get("input_tokens") and r.get("status") in ("ok", "repaired",
                                                              "schema_failure"):
                ins.append(u["input_tokens"])
                outs.append(u.get("output_tokens", 0))
    if ins:
        return sum(ins) / len(ins), sum(outs) / len(outs), len(ins)
    # fallback estimate: measured pilot showed ~8.3k in / ~6.6k out (case),
    # ~13k in / ~6.6k out (evidence).
    return (8300.0, 6600.0, 0) if mode == "case_only" else (13300.0, 6600.0, 0)


def main() -> int:
    import pandas as pd

    cfg = load_config("benchmark")
    cap = float(cfg.get("max_cost_usd", 500))
    require = bool(cfg.get("require_cost_confirmation", True))
    repeat_n = int(cfg.get("repeat_subset_size", 200))
    repeat_t = int(cfg.get("repeat_trials", 3))

    idx = pd.read_parquet(RESULTS_DIR / "case_index.parquet")
    n_eligible = int(idx["status"].isin(
        ["eligible", "eligible_with_warning"]).sum())

    model = "claude-sonnet-4-6"  # both models priced identically
    tok = {m: _pilot_tokens(m) for m in ("case_only", "evidence")}

    def per_call(mode):
        i, o, _ = tok[mode]
        return cost_usd(model, {"input_tokens": i, "output_tokens": o})

    projection = {"n_eligible_cases": n_eligible, "cap_usd": cap,
                  "measured_from_pilot": {m: {"input": tok[m][0],
                                              "output": tok[m][1],
                                              "n_pilot": tok[m][2]}
                                          for m in tok},
                  "arms": {}, "totals": {}}

    full_total = 0.0
    for arm, (mdl, mode) in PAID_ARMS.items():
        pc = per_call(mode)
        arm_cost = pc * n_eligible
        full_total += arm_cost
        projection["arms"][arm] = {
            "model": mdl, "mode": mode,
            "cost_per_call_usd": round(pc, 4),
            "full_pass_cost_usd": round(arm_cost, 2),
        }

    # repeat trials: extra (repeat_t - 1) trials on repeat_n cases, all 4 arms
    repeat_extra = 0.0
    for arm, (mdl, mode) in PAID_ARMS.items():
        repeat_extra += per_call(mode) * repeat_n * (repeat_t - 1)

    grand = full_total + repeat_extra
    projection["totals"] = {
        "full_4arm_pass_usd": round(full_total, 2),
        "repeat_trials_extra_usd": round(repeat_extra, 2),
        "grand_total_usd": round(grand, 2),
        "grand_total_batch_api_usd": round(grand * 0.5, 2),
        "exceeds_cap": grand > cap,
    }

    (RESULTS_DIR / "aggregate" / "cost_estimate.json").write_text(
        json.dumps(projection, indent=2))

    print("=== Cost projection (paid model arms) ===")
    print(f"Eligible cases: {n_eligible}   Cap: ${cap:.0f}   "
          f"require_confirmation: {require}")
    print(f"Measured/est tokens — case_only: "
          f"{tok['case_only'][0]:.0f} in / {tok['case_only'][1]:.0f} out "
          f"(pilot n={tok['case_only'][2]}); evidence: "
          f"{tok['evidence'][0]:.0f} in / {tok['evidence'][1]:.0f} out "
          f"(pilot n={tok['evidence'][2]})")
    print()
    for arm, d in projection["arms"].items():
        print(f"  {arm:32s} ${d['cost_per_call_usd']:.4f}/call  "
              f"-> ${d['full_pass_cost_usd']:.2f} full pass")
    print()
    t = projection["totals"]
    print(f"Full 4-arm pass:        ${t['full_4arm_pass_usd']:.2f}")
    print(f"+ repeat trials:        ${t['repeat_trials_extra_usd']:.2f}")
    print(f"GRAND TOTAL (Messages): ${t['grand_total_usd']:.2f}")
    print(f"GRAND TOTAL (Batch API, half): ${t['grand_total_batch_api_usd']:.2f}")
    print()
    if t["exceeds_cap"]:
        print(f"!! Projected ${t['grand_total_usd']:.2f} EXCEEDS the "
              f"${cap:.0f} cap.")
        print("   Options: (a) raise max_cost_usd, (b) reduce cases "
              "(--limit N), (c) run fewer arms, (d) use Batch API for the "
              "quality/cost pass (half price, non-interactive latency).")
    else:
        print(f"Within cap. Full paid run still requires explicit "
              f"--confirm-cost (require_cost_confirmation={require}).")
    print("\nNo spend performed. CareGuard Arm E + ablations are free/"
          "deterministic and can run now via run_core_benchmark.sh.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
