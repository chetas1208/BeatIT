#!/usr/bin/env bash
# Full benchmark path INCLUDING the paid Sonnet 4.5/4.6 arms.
# Requires an explicit cost confirmation: set CONFIRM_COST=1 and honor the cap
# in config/benchmark.yaml. Review runners/estimate_cost.py first.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-$HERE/../../.venv/bin/python}"
"$PY" "$HERE/runners/estimate_cost.py"
if [[ "${CONFIRM_COST:-0}" != "1" ]]; then
  echo "Refusing to run paid arms without CONFIRM_COST=1 (projected cost may"
  echo "exceed the cap). Re-run: CONFIRM_COST=1 bash run_full_benchmark.sh"
  exit 3
fi
bash "$HERE/run_core_benchmark.sh"
for arm in sonnet_45_case_only sonnet_46_case_only \
           sonnet_45_evidence_grounded sonnet_46_evidence_grounded; do
  "$PY" "$HERE/runners/run_direct_baseline.py" --arm "$arm" "${@:-}"
done
"$PY" "$HERE/analysis/run_analysis.py"
"$PY" "$HERE/analysis/generate_charts.py"
"$PY" "$HERE/analysis/generate_report.py"
echo "Full benchmark complete. See results/reports/report.md"
