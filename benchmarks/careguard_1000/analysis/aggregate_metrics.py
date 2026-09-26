#!/usr/bin/env python3
"""Aggregate metrics entrypoint — see analysis/run_analysis.py (grades all arms,
pools set metrics, writes results/aggregate/metrics.json)."""
import runpy, sys
from pathlib import Path
if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).parent / "run_analysis.py"), run_name="__main__")
