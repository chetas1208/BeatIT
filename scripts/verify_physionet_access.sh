#!/usr/bin/env bash
# Report PhysioNet/MIMIC access readiness without printing credentials.
set -euo pipefail

status="UNKNOWN"
reasons=()

if [[ -d "${HOME}/.physionet" ]]; then
  reasons+=("physionet_config_dir_present")
fi

if command -v wget >/dev/null 2>&1; then
  if wget --spider -q "https://physionet.org/files/mimiciv/2.2/" 2>/dev/null; then
    reasons+=("mimiciv_index_reachable")
  else
    reasons+=("mimiciv_index_not_reachable_or_denied")
  fi
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${repo_root}/data/raw/mimic-demo/core/patients.csv.gz" ]]; then
  reasons+=("mimic_demo_files_present")
  status="PARTIAL_OPEN_DEMO"
fi

if [[ -f "${repo_root}/data/raw/ptb-xl/ptbxl_database.csv" ]]; then
  reasons+=("ptbxl_index_present")
fi

# Credentialed full MIMIC: require demo or explicit env flag set by operator after manual verify
if [[ "${PHYSIONET_MIMIC_AUTHORIZED:-}" == "true" ]]; then
  status="AUTHORIZED"
elif [[ "$status" == "UNKNOWN" ]]; then
  if [[ " ${reasons[*]} " == *" mimic_demo_files_present "* ]]; then
    status="PARTIAL_OPEN_DEMO"
  else
    status="NOT_AUTHORIZED"
    reasons+=("no_local_mimic_files_no_operator_flag")
  fi
fi

echo "PHYSIONET_ACCESS_STATUS=${status}"
for r in "${reasons[@]}"; do
  echo "SIGNAL ${r}"
done
