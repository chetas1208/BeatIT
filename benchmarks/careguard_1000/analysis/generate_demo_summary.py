#!/usr/bin/env python3
"""Emit the concise demo proof summary — delegates to generate_report.py which
writes results/reports/demo_summary.{md,html}."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analysis.generate_report import build_demo_summary, write_html
from _bench_common import RESULTS_DIR

if __name__ == "__main__":
    demo = build_demo_summary()
    (RESULTS_DIR / "reports" / "demo_summary.md").write_text(demo)
    write_html(demo, RESULTS_DIR / "reports" / "demo_summary.html")
    print(demo)
