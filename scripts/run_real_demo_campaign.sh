#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"
PY="${repo}/data/.venv-data/bin/python"
if [[ ! -x "$PY" ]]; then
  python3 "${repo}/data/scripts/00_check_environment.py"
  PY="${repo}/data/.venv-data/bin/python"
fi
export PYTHONPATH="$repo"
echo "=== Real demo campaign — Wave 2 download ==="
"$PY" "${repo}/data/real/scripts/wave2_download.py"
echo "=== Wave 3 mine ==="
"$PY" "${repo}/data/real/scripts/wave3_mine_cohort.py"
echo "=== Wave 4 normalize ==="
"$PY" "${repo}/data/real/scripts/wave4_normalize.py"
echo "=== Wave 5 BeatIT run ==="
"$PY" "${repo}/data/real/scripts/wave5_beatit_run.py"
echo "=== Wave 6 finalize docs ==="
"$PY" "${repo}/data/real/scripts/wave6_finalize_docs.py"
echo "=== Campaign scripts complete ==="
"$repo/scripts/verify_physionet_access.sh"
