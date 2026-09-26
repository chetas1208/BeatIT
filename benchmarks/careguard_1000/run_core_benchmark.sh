#!/usr/bin/env bash
# Free / deterministic benchmark path — spends $0 on models.
# Prep -> CareGuard Arm E + ablations over eligible cases -> grade -> report.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-$HERE/../../.venv/bin/python}"
"$PY" "$HERE/runners/verify_models.py"
"$PY" "$HERE/runners/build_case_index.py"
"$PY" "$HERE/reference/build_reference_set.py"
"$PY" "$HERE/runners/run_careguard.py" --arm all "${@:-}"
"$PY" "$HERE/analysis/run_analysis.py"
"$PY" "$HERE/analysis/generate_charts.py"
"$PY" "$HERE/analysis/generate_report.py"
echo "Core benchmark complete. See results/reports/report.md"
