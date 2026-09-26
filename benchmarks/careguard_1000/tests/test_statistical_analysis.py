"""Bootstrap CI and paired Wilcoxon behave sanely."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis._analysis_lib import bootstrap_ci, wilcoxon_paired

def test_bootstrap_ci_brackets_mean():
    vals = [0.5]*50 + [0.6]*50
    ci = bootstrap_ci(vals, resamples=500)
    assert ci["lo"] <= ci["mean"] <= ci["hi"]
    assert abs(ci["mean"] - 0.55) < 0.02

def test_wilcoxon_detects_shift():
    a = {f"c{i}": 0.8 for i in range(20)}
    b = {f"c{i}": 0.4 for i in range(20)}
    r = wilcoxon_paired(a, b)
    assert r["mean_diff"] > 0
    assert r["p_value"] is not None and r["p_value"] < 0.05

def test_wilcoxon_insufficient_pairs():
    r = wilcoxon_paired({"c0": 0.5}, {"c0": 0.4})
    assert r["p_value"] is None

def _run():
    for k,v in list(globals().items()):
        if k.startswith("test_") and callable(v): v(); print("  ok ",k)
    print("statistical-analysis tests passed")
if __name__ == "__main__": _run()
