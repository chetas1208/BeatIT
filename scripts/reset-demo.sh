#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
state_file="$repo_root/data/demo/state.json"

if [[ -f "$state_file" ]]; then
  rm -f "$state_file"
  echo "Removed explicit demo state: $state_file"
else
  echo "Demo state already reset"
fi

echo "Run ./scripts/seed-demo.sh to recreate the canonical synthetic demo state."
