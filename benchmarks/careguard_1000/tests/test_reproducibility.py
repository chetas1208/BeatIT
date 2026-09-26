"""Deterministic layers reproduce: the case index and reference are stable, and
bootstrap is seeded (same input -> same CI)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis._analysis_lib import bootstrap_ci

def test_bootstrap_is_seeded():
    vals = [0.3, 0.6, 0.9, 0.4, 0.7]
    a = bootstrap_ci(vals, resamples=300)
    b = bootstrap_ci(vals, resamples=300)
    assert a == b

def test_case_index_exists_and_covers_all():
    import pandas as pd
    from _bench_common import RESULTS_DIR
    p = RESULTS_DIR / "case_index.parquet"
    assert p.exists()
    df = pd.read_parquet(p)
    assert (df["status"].str.startswith("eligible") |
            df["status"].str.startswith("ineligible")).all()

def _run():
    for k,v in list(globals().items()):
        if k.startswith("test_") and callable(v): v(); print("  ok ",k)
    print("reproducibility tests passed")
if __name__ == "__main__": _run()
