#!/usr/bin/env python3
"""One-image preliminary results dashboard (results/charts/preliminary_dashboard.png).

Reads results/aggregate/metrics.json only. Honest by construction: every bar is
annotated with its n; arms with pilot-scale n are hatched and flagged. CareGuard
arms are the 1,000-case deterministic runs; direct-model arms appear only if
their raw results exist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BENCH = Path(__file__).resolve().parent.parent
METRICS = BENCH / "results" / "aggregate" / "metrics.json"
OUT = BENCH / "results" / "charts" / "preliminary_dashboard.png"

# fixed palette: CareGuard violet, ablations muted violet, models slate gray
C_CG = "#6d28d9"
C_ABL = "#a78bfa"
C_MODEL = "#64748b"
INK = "#1e293b"
MUTED = "#64748b"

ARM_LABEL = {
    "sonnet_45_case_only": "S4.5\ncase-only",
    "sonnet_46_case_only": "S4.6\ncase-only",
    "sonnet_45_evidence_grounded": "S4.5\n+evidence",
    "sonnet_46_evidence_grounded": "S4.6\n+evidence",
    "careguard_full": "CareGuard\nfull",
    "careguard_no_critic": "CG\n−critic",
    "careguard_no_retrieval": "CG\n−retrieval",
    "careguard_no_multimorbidity": "CG\n−multimorb",
    "careguard_no_deterministic_conflict_engine": "CG\n−engine",
}
PILOT_N = 50  # arms with fewer trials than this are flagged as pilot


def _color(arm: str) -> str:
    if arm == "careguard_full":
        return C_CG
    if arm.startswith("careguard"):
        return C_ABL
    return C_MODEL


def _bars(ax, arms, values, ns, title, ylim=(0, 1.0), fmt="{:.2f}"):
    xs = range(len(arms))
    headroom = ylim[1] * 1.22
    for i, (a, v, n) in enumerate(zip(arms, values, ns)):
        pilot = (n or 0) < PILOT_N
        ax.bar(i, v if v is not None else 0, width=0.6, color=_color(a),
               hatch="//" if pilot else None, edgecolor="white", linewidth=0.5,
               zorder=3)
        if v is not None:
            ax.text(i, v + ylim[1] * 0.03, fmt.format(v), ha="center",
                    va="bottom", fontsize=8, color=INK, zorder=4)
        ax.text(i, -headroom * 0.14,
                f"n={n}" + ("†" if pilot else ""),
                ha="center", va="top", fontsize=6.5, color=MUTED)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([ARM_LABEL.get(a, a) for a in arms], fontsize=7)
    ax.set_ylim(ylim[0], headroom)
    ax.set_yticks([t for t in (0, 0.25, 0.5, 0.75, 1.0)] if ylim[1] == 1.0
                  else ax.get_yticks()[:-1])
    ax.set_title(title, fontsize=10, color=INK, pad=10)
    ax.grid(axis="y", color="#e2e8f0", linewidth=0.7, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#cbd5e1")
    ax.tick_params(colors=MUTED, labelsize=7.5)


def main() -> int:
    m = json.loads(METRICS.read_text())
    order = [a for a in ARM_LABEL if a in m]

    def get(arm, *path):
        cur = m.get(arm, {})
        for p in path:
            cur = (cur or {}).get(p) if isinstance(cur, dict) else None
        return cur

    def ns(arm):
        return get(arm, "n_gradable") or get(arm, "n_trials") or 0

    fig, axes = plt.subplots(2, 3, figsize=(17, 9))
    fig.subplots_adjust(hspace=0.66, wspace=0.32, top=0.85, bottom=0.11,
                        left=0.05, right=0.98)

    # 1. medication reconciliation F1 (corpus-pooled)
    _bars(axes[0][0], order, [get(a, "medication", "f1") for a in order],
          [ns(a) for a in order], "Medication reconciliation F1 (pooled)")

    # 2. contraindication: label-signal coverage
    _bars(axes[0][1], order,
          [get(a, "contraindication_signal_coverage", "mean") for a in order],
          [ns(a) for a in order],
          "Label-contraindication signal coverage\n(asserted OR explicit abstention)")

    # 3. source grounding rate of substantive conflicts
    _bars(axes[0][2], order, [get(a, "evidence", "mean") for a in order],
          [ns(a) for a in order], "Source-grounding rate (substantive conflicts)")

    # 4. unsupported-claim rate (lower better)
    _bars(axes[1][0], order, [get(a, "safety", "mean") for a in order],
          [ns(a) for a in order],
          "Unsupported-claim rate (lower = safer)")

    # 5. allergy conflict detection recall
    _bars(axes[1][1], order, [get(a, "allergy", "recall") for a in order],
          [ns(a) for a in order], "Allergy-conflict recall (12 documented)")

    # 6. cost per case
    costs = [get(a, "operational", "cost_usd_per_case") for a in order]
    top = max([c for c in costs if c is not None] + [0.02]) * 1.4
    _bars(axes[1][2], order, costs, [ns(a) for a in order],
          "Cost per case (USD)", ylim=(0, top), fmt="${:.3f}")

    fig.suptitle(
        "HeartTwin CareGuard 1,000-case benchmark — PRELIMINARY",
        fontsize=14, fontweight="bold", color=INK, y=0.97)
    fig.text(0.5, 0.915,
             "CareGuard arms: full 1,000-case deterministic runs • "
             "† hatched = pilot-scale n, not comparable • "
             "research benchmark on deidentified/composite open data — "
             "not clinical validation",
             ha="center", fontsize=9, color=MUTED)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=160, facecolor="white")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
