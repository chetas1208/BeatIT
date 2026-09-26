#!/usr/bin/env python3
"""failure_analysis — computed inside analysis/run_analysis.py and written to
results/statistics|aggregate|failures. Re-exports the underlying helpers from
analysis/_analysis_lib.py so they can be imported directly."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis._analysis_lib import (  # noqa: F401
    bootstrap_ci, wilcoxon_paired, pool_metrics, per_case_composite,
    per_case_metric,
)

def main() -> int:
    import runpy
    runpy.run_path(str(Path(__file__).parent / "run_analysis.py"), run_name="__main__")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
