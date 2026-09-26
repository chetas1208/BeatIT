#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
mode="${HEARTTWIN_DEPLOY_MODE:-local-dev}"
if [[ "${1:-}" == "--status" ]]; then
  python scripts/verify_env.py --mode "$mode" --status
else
  python scripts/verify_env.py --mode "$mode"
fi
