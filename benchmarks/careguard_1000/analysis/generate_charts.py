#!/usr/bin/env python3
"""Render benchmark charts from results/aggregate/metrics.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))
from _bench_common import RESULTS_DIR  # noqa: E402

ARM_ORDER = [
    "sonnet_45_case_only", "sonnet_46_case_only",
    "sonnet_45_evidence_grounded", "sonnet_46_evidence_grounded",
    "careguard_full", "careguard_no_critic", "careguard_no_retrieval",
    "careguard_no_multimorbidity", "careguard_no_deterministic_conflict_engine",
]
SHORT = {
    "sonnet_45_case_only": "S4.5 case",
    "sonnet_46_case_only": "S4.6 case",
    "sonnet_45_evidence_grounded": "S4.5 ev",
    "sonnet_46_evidence_grounded": "S4.6 ev",
    "careguard_full": "CG full",
    "careguard_no_critic": "CG -critic",
    "careguard_no_retrieval": "CG -retr",
    "careguard_no_multimorbidity": "CG -multi",
    "careguard_no_deterministic_conflict_engine": "CG -engine",
}


def main() -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    metrics_path = RESULTS_DIR / "aggregate" / "metrics.json"
    if not metrics_path.exists():
        print("no metrics.json — run run_analysis.py first")
        return 1
    agg = json.loads(metrics_path.read_text())
    arms = [a for a in ARM_ORDER if a in agg]
    labels = [SHORT.get(a, a) for a in arms]
    charts_dir = RESULTS_DIR / "charts"

    def bar(values, title, fname, ylabel, pct=True):
        fig, ax = plt.subplots(figsize=(9, 4.2))
        xs = range(len(arms))
        vals = [(v * 100 if (pct and v is not None) else v) or 0
                for v in values]
        colors = ["#64748b" if a.startswith("sonnet") else "#7c3aed"
                  for a in arms]
        ax.bar(xs, vals, color=colors)
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_ylabel(ylabel)
        for i, v in enumerate(vals):
            ax.text(i, v, f"{v:.0f}" if pct else f"{v:.2f}",
                    ha="center", va="bottom", fontsize=7)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(charts_dir / fname, dpi=130)
        plt.close(fig)
        print(f"  wrote {fname}")

    def get(a, *path):
        node = agg[a]
        for p in path:
            node = (node or {}).get(p) if isinstance(node, dict) else None
        return node

    bar([get(a, "composite", "mean") for a in arms],
        "Composite score by arm", "composite.png", "composite (%)")
    bar([get(a, "medication", "recall") for a in arms],
        "Medication reconciliation recall", "medication_recall.png",
        "recall (%)")
    bar([get(a, "contraindication", "recall") for a in arms],
        "Contraindication-signal recall", "contraindication_recall.png",
        "recall (%)")
    bar([get(a, "evidence", "mean") for a in arms],
        "Source-grounding rate", "grounding_rate.png", "rate (%)")
    bar([get(a, "safety", "mean") for a in arms],
        "Unsupported-claim rate (lower is better)", "unsupported_rate.png",
        "rate (%)")
    bar([get(a, "operational", "cost_usd_per_case") for a in arms],
        "Cost per case (USD)", "cost_per_case.png", "USD", pct=False)
    bar([get(a, "operational", "latency_median_s") for a in arms],
        "Median latency (s)", "latency_median.png", "seconds", pct=False)
    print("charts written to results/charts/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
