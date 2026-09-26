#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ "${1:-}" == "--reset" ]]; then
  exec python scripts/build_cohort_500.py --reset
fi
if [[ "${1:-}" != "" ]]; then
  echo "usage: $0 [--reset]" >&2
  exit 2
fi
exec python scripts/build_cohort_500.py
