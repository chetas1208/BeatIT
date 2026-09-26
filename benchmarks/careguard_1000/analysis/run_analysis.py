#!/usr/bin/env python3
"""Grade every arm present in results/raw/, pool metrics, compute bootstrap CIs,
paired tests, and subgroup breakdowns, then write aggregate + statistics JSON.

Deterministic and free — operates on already-produced trial records. Safe to run
on just the CareGuard (Arm E) + ablations without any paid model arm present.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH / "analysis"))
from _bench_common import RESULTS_DIR, load_config  # noqa: E402
from _analysis_lib import (  # noqa: E402
    bootstrap_ci, grade_arm, load_reference, per_case_composite,
    per_case_metric, pool_metrics, wilcoxon_paired,
)

ALL_ARMS = [
    "sonnet_45_case_only", "sonnet_46_case_only",
    "sonnet_45_evidence_grounded", "sonnet_46_evidence_grounded",
    "careguard_full", "careguard_no_critic", "careguard_no_retrieval",
    "careguard_no_multimorbidity", "careguard_no_deterministic_conflict_engine",
]

# Paired comparisons that answer the benchmark's questions.
PAIRS = [
    ("model_generation_case_only", "sonnet_46_case_only", "sonnet_45_case_only"),
    ("model_generation_evidence", "sonnet_46_evidence_grounded",
     "sonnet_45_evidence_grounded"),
    ("retrieval_effect_45", "sonnet_45_evidence_grounded",
     "sonnet_45_case_only"),
    ("retrieval_effect_46", "sonnet_46_evidence_grounded",
     "sonnet_46_case_only"),
    ("system_vs_model_46", "careguard_full", "sonnet_46_case_only"),
    ("system_vs_model_46_evidence", "careguard_full",
     "sonnet_46_evidence_grounded"),
    ("ablation_critic", "careguard_full", "careguard_no_critic"),
    ("ablation_retrieval", "careguard_full", "careguard_no_retrieval"),
    ("ablation_multimorbidity", "careguard_full",
     "careguard_no_multimorbidity"),
    ("ablation_conflict_engine", "careguard_full",
     "careguard_no_deterministic_conflict_engine"),
]


def main() -> int:
    import pandas as pd

    cfg = load_config("report_config") if (BENCH / "config" /
                                           "report_config.yaml").exists() else {}
    resamples = int((cfg.get("statistical") or {}).get(
        "bootstrap_resamples", 2000))

    ref = load_reference()
    present = [a for a in ALL_ARMS
               if (RESULTS_DIR / "raw" / f"{a}.ndjson").exists()]
    print(f"Grading arms present: {present}")

    graded_by_arm = {}
    aggregate = {}
    for arm in present:
        graded = grade_arm(arm, ref)
        graded_by_arm[arm] = graded
        aggregate[arm] = pool_metrics(graded)
        m = aggregate[arm]
        comp = m["composite"]["mean"]
        print(f"  {arm:44s} n={m['n_trials']:4d} "
              f"gradable={m['n_gradable']:4d} "
              f"composite={comp:.3f}" if comp is not None
              else f"  {arm:44s} n={m['n_trials']}")

    (RESULTS_DIR / "aggregate" / "metrics.json").write_text(
        json.dumps(aggregate, indent=2, default=str))

    # Bootstrap CIs on per-case composite + key recalls
    stats = {"bootstrap": {}, "paired": {}}
    for arm, graded in graded_by_arm.items():
        comp = list(per_case_composite(graded).values())
        med = list(per_case_metric(graded, "medication", "recall").values())
        contra = list(per_case_metric(graded, "contraindication",
                                      "recall").values())
        stats["bootstrap"][arm] = {
            "composite": bootstrap_ci(comp, resamples),
            "medication_recall": bootstrap_ci(med, resamples),
            "contraindication_recall": bootstrap_ci(contra, resamples),
        }

    # Paired tests
    comp_by_arm = {a: per_case_composite(g)
                   for a, g in graded_by_arm.items()}
    for name, arm_a, arm_b in PAIRS:
        if arm_a in comp_by_arm and arm_b in comp_by_arm:
            stats["paired"][name] = {
                "arm_a": arm_a, "arm_b": arm_b,
                "composite": wilcoxon_paired(comp_by_arm[arm_a],
                                             comp_by_arm[arm_b]),
            }

    (RESULTS_DIR / "statistics" / "statistics.json").write_text(
        json.dumps(stats, indent=2, default=str))

    # Subgroup breakdown (composite by index subgroup) for present arms
    idx_path = RESULTS_DIR / "case_index.parquet"
    subgroups = {}
    if idx_path.exists():
        idx = pd.read_parquet(idx_path).set_index("case_id")

        def band_med(n):
            n = float(n or 0)
            return "few<=10" if n <= 10 else ("many_11_40" if n <= 40
                                              else "poly>=41")

        def band_org(n):
            n = float(n or 0)
            return "low<=2" if n <= 2 else ("mid_3_6" if n <= 6 else "high>=7")

        for arm, graded in graded_by_arm.items():
            per_case = per_case_composite(graded)
            rows = {"by_medication_band": {}, "by_organ_band": {}}
            buckets_m: dict[str, list] = {}
            buckets_o: dict[str, list] = {}
            for cid, score in per_case.items():
                if cid in idx.index:
                    r = idx.loc[cid]
                    buckets_m.setdefault(band_med(r.get("medication_count")),
                                         []).append(score)
                    buckets_o.setdefault(band_org(r.get("organ_system_count")),
                                         []).append(score)
            rows["by_medication_band"] = {
                k: {"mean": sum(v) / len(v), "n": len(v)}
                for k, v in buckets_m.items()}
            rows["by_organ_band"] = {
                k: {"mean": sum(v) / len(v), "n": len(v)}
                for k, v in buckets_o.items()}
            subgroups[arm] = rows
    (RESULTS_DIR / "statistics" / "subgroups.json").write_text(
        json.dumps(subgroups, indent=2, default=str))

    # Failure analysis: schema/api failures per arm + a few examples
    failures = {}
    for arm, graded in graded_by_arm.items():
        fails = [g for g in graded
                 if g["status"] in ("schema_failure", "api_failure")]
        failures[arm] = {
            "n_failures": len(fails),
            "by_status": {s: sum(1 for g in graded if g["status"] == s)
                          for s in ("ok", "repaired", "schema_failure",
                                    "api_failure")},
            "example_case_ids": [g["case_id"] for g in fails[:10]],
        }
    (RESULTS_DIR / "failures" / "failure_analysis.json").write_text(
        json.dumps(failures, indent=2, default=str))

    print("\nWrote results/aggregate/metrics.json, "
          "results/statistics/{statistics,subgroups}.json, "
          "results/failures/failure_analysis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
