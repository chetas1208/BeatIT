#!/usr/bin/env bash
# HeartTwin CareGuard — full reproducible data pipeline.
# Idempotent + resumable: completed downloads/normalizations are skipped via cache.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$(cd "$HERE/.." && pwd)"
cd "$DATA_DIR"

LOG="$DATA_DIR/logs/run_all.log"
mkdir -p "$DATA_DIR/logs"
echo "=== run_all start $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee -a "$LOG"

# Stage 00 bootstraps the venv on the system interpreter; the rest use it.
PYBOOT="${PYTHON:-python3}"
"$PYBOOT" scripts/00_check_environment.py | tee -a "$LOG"
PY="$DATA_DIR/.venv-data/bin/python"

run() { echo "--- $* ---" | tee -a "$LOG"; "$PY" "$@" 2>&1 | tee -a "$LOG"; }

run scripts/01_download_sources.py
run scripts/02_verify_downloads.py
run scripts/03_extract_eicu.py
run scripts/04_select_cohort.py
run scripts/05_select_ptbxl.py
run scripts/06_download_selected_ecgs.py
run scripts/13_select_echonet.py
run scripts/14_match_download_echos.py
run scripts/07_normalize_medications.py
run scripts/08_build_fhir.py
run scripts/09_generate_case_files.py
run scripts/10_run_quality_checks.py
run scripts/11_run_analysis.py
run scripts/12_validate_all_cases.py

echo "" | tee -a "$LOG"
echo "=== FINAL SUMMARY ===" | tee -a "$LOG"
"$PY" - <<'PYEOF' | tee -a "$LOG"
import json, glob, os
d = os.path.dirname(os.path.dirname(os.path.abspath("scripts")))
def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return {}
base = os.path.join(os.getcwd())
sel = load("staging/eicu/selection_summary.json")
val = load("analysis/validation_summary.json")
qs  = load("analysis/quality_summary.json")
ecg = load("staging/ptb-xl/ecg_assignments.json") if os.path.exists("staging/ptb-xl/ecg_assignments.json") else []
ncases = len(glob.glob("cases/case-*"))
print(f"Total cases packaged      : {ncases}")
print(f"Real eICU cases           : {sel.get('real_selected')}")
print(f"Synthetic fallback cases  : {sel.get('synthetic_shortfall')}")
print(f"Cases with PTB-XL ECG      : {qs.get('ecg_assigned')}")
print(f"Structurally valid cases  : {val.get('valid')}")
print(f"FHIR-valid cases          : {qs.get('fhir_valid')}")
print(f"Failed/quarantined cases  : {val.get('quarantined')}")
print(f"Output directory          : {os.getcwd()}")
print(f"Analysis report           : analysis/cohort_quality_report.html")
PYEOF
echo "=== run_all done $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee -a "$LOG"
