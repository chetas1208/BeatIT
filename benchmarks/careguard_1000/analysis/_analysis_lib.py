"""Shared analysis: grade raw trials, pool set metrics, bootstrap CIs, paired
tests, operational summaries. Pure functions over the results/ files.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))
from _bench_common import (  # noqa: E402
    REFERENCE_DIR, RESULTS_DIR, read_jsonl, write_jsonl,
)
from graders._grader_lib import grade_trial  # noqa: E402

SET_METRICS = ["medication", "allergy", "contraindication", "missingness",
               "condition"]
RATE_METRICS = {
    "evidence": "grounding_rate",
    "safety": "unsupported_claim_rate",
    "abstention": "abstention_quality",
    "trace": "traceability_rate",
}


def load_reference() -> dict[str, dict]:
    out = {}
    p = REFERENCE_DIR / "reference_labels.ndjson"
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            r = json.loads(line)
            out[r["case_id"]] = r
    return out


def grade_arm(arm: str, ref: dict[str, dict]) -> list[dict]:
    raw = read_jsonl(RESULTS_DIR / "raw" / f"{arm}.ndjson")
    graded = []
    for trial in raw:
        cid = trial.get("case_id")
        r = ref.get(cid)
        if r is None:
            continue
        g = grade_trial(trial, r)
        # carry operational fields for the pooled summary
        g["_op"] = {
            "cost_usd": float(trial.get("cost_usd", 0) or 0),
            "latency_seconds": float(trial.get("latency_seconds", 0) or 0),
            "input_tokens": (trial.get("usage") or {}).get("input_tokens", 0),
            "output_tokens": (trial.get("usage") or {}).get("output_tokens", 0),
            "status": trial.get("status"),
            "retry_count": trial.get("retry_count", 0),
            "tool_call_count": trial.get("tool_call_count", 0),
        }
        graded.append(g)
    write_jsonl(RESULTS_DIR / "graded" / f"{arm}.ndjson",
                [{k: v for k, v in g.items() if k != "_op"} for g in graded])
    return graded


def _pct(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return xs[int(k)]
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def pool_metrics(graded: list[dict]) -> dict:
    n = len(graded)
    gradable = [g for g in graded if g.get("gradable")]

    out: dict[str, Any] = {"n_trials": n, "n_gradable": len(gradable)}

    # pooled set metrics (corpus-level P/R/F1)
    for m in SET_METRICS:
        tp = fp = fn = 0
        for g in gradable:
            mm = g["metrics"].get(m, {})
            tp += mm.get("tp", 0) or 0
            fp += mm.get("fp", 0) or 0
            fn += mm.get("fn", 0) or 0
        prec = tp / (tp + fp) if (tp + fp) else None
        rec = tp / (tp + fn) if (tp + fn) else None
        f1 = (2 * prec * rec / (prec + rec)) if (prec and rec) else None
        out[m] = {"tp": tp, "fp": fp, "fn": fn, "precision": prec,
                  "recall": rec, "f1": f1,
                  "support": tp + fn}

    # contraindication signal coverage (asserted OR explicitly abstained)
    cov = [g["metrics"]["contraindication"].get("signal_coverage")
           for g in gradable
           if g["metrics"].get("contraindication", {}).get("signal_coverage")
           is not None]
    out["contraindication_signal_coverage"] = {
        "mean": (sum(cov) / len(cov)) if cov else None, "n": len(cov)}

    # rate metrics (mean over trials where defined)
    for m, key in RATE_METRICS.items():
        vals = [g["metrics"][m].get(key) for g in gradable
                if g["metrics"].get(m, {}).get(key) is not None]
        out[m] = {"mean": (sum(vals) / len(vals)) if vals else None,
                  "n": len(vals)}

    # composite
    comps = [g["composite_score"] for g in gradable
             if g.get("composite_score") is not None]
    out["composite"] = {"mean": (sum(comps) / len(comps)) if comps else None,
                        "n": len(comps)}

    # schema validity
    valid = sum(1 for g in graded
                if g["metrics"]["format"]["schema_valid"])
    repaired = sum(1 for g in graded if g["metrics"]["format"]["repaired"])
    out["schema"] = {
        "valid": valid, "valid_rate": (valid / n) if n else None,
        "repaired": repaired,
        "schema_failure": sum(1 for g in graded
                              if g["metrics"]["format"]["schema_failure"]),
    }

    # operational
    costs = [g["_op"]["cost_usd"] for g in graded]
    lats = [g["_op"]["latency_seconds"] for g in graded
            if g["_op"]["latency_seconds"] > 0]
    itok = [g["_op"]["input_tokens"] for g in graded]
    otok = [g["_op"]["output_tokens"] for g in graded]
    statuses = [g["_op"]["status"] for g in graded]
    out["operational"] = {
        "cost_usd_total": round(sum(costs), 4),
        "cost_usd_per_case": round(sum(costs) / n, 6) if n else None,
        "latency_median_s": _pct(lats, 0.5),
        "latency_p95_s": _pct(lats, 0.95),
        "input_tokens_mean": (sum(itok) / n) if n else None,
        "output_tokens_mean": (sum(otok) / n) if n else None,
        "api_failure_rate": statuses.count("api_failure") / n if n else None,
        "schema_failure_rate":
            statuses.count("schema_failure") / n if n else None,
        "retry_rate": (sum(g["_op"]["retry_count"] for g in graded) / n)
        if n else None,
        "completion_rate":
            sum(1 for s in statuses if s in ("ok", "repaired")) / n
            if n else None,
    }
    return out


def per_case_composite(graded: list[dict]) -> dict[str, float]:
    """case_id -> mean composite across its trials (for paired tests)."""
    acc: dict[str, list[float]] = {}
    for g in graded:
        c = g.get("composite_score")
        if c is not None:
            acc.setdefault(g["case_id"], []).append(c)
    return {k: sum(v) / len(v) for k, v in acc.items()}


def per_case_metric(graded: list[dict], metric: str, field: str) -> dict:
    """case_id -> per-case metric value (recall for set metrics)."""
    acc: dict[str, list[float]] = {}
    for g in graded:
        if not g.get("gradable"):
            continue
        v = g["metrics"].get(metric, {}).get(field)
        if v is not None:
            acc.setdefault(g["case_id"], []).append(v)
    return {k: sum(v) / len(v) for k, v in acc.items()}


def bootstrap_ci(values: list[float], resamples: int = 2000,
                 ci: float = 0.95, seed: int = 12345) -> dict:
    if not values:
        return {"mean": None, "lo": None, "hi": None, "n": 0}
    import random
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(resamples):
        s = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(s) / n)
    means.sort()
    lo = means[int((1 - ci) / 2 * resamples)]
    hi = means[int((1 - (1 - ci) / 2) * resamples) - 1]
    return {"mean": sum(values) / n, "lo": lo, "hi": hi, "n": n}


def wilcoxon_paired(a: dict[str, float], b: dict[str, float]) -> dict:
    """Paired Wilcoxon signed-rank on the cases both arms scored."""
    keys = sorted(set(a) & set(b))
    xa = [a[k] for k in keys]
    xb = [b[k] for k in keys]
    diffs = [x - y for x, y in zip(xa, xb)]
    nonzero = [d for d in diffs if d != 0]
    result = {
        "n_paired": len(keys),
        "n_nonzero": len(nonzero),
        "mean_a": (sum(xa) / len(xa)) if xa else None,
        "mean_b": (sum(xb) / len(xb)) if xb else None,
        "mean_diff": (sum(diffs) / len(diffs)) if diffs else None,
    }
    if len(nonzero) < 6:
        result["p_value"] = None
        result["test"] = "insufficient_nonzero_pairs"
        return result
    try:
        from scipy.stats import wilcoxon
        stat, p = wilcoxon(xa, xb, zero_method="wilcox",
                           alternative="two-sided")
        result["statistic"] = float(stat)
        result["p_value"] = float(p)
        result["test"] = "wilcoxon_signed_rank"
        # rank-biserial effect size
        pos = sum(1 for d in nonzero if d > 0)
        result["direction_positive_frac"] = pos / len(nonzero)
    except Exception as exc:
        result["p_value"] = None
        result["test"] = f"error:{exc!r}"
    return result
