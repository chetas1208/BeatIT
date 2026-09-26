#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
./scripts/verify-models.sh
./scripts/verify-cohort-500.sh
if [[ "${1:-}" != "--public" ]]; then
  echo "PUBLIC VERIFICATION BLOCKED: pass --public after starting a named Cloudflare Tunnel" >&2
  exit 2
fi
./scripts/verify-tunnel.sh "${BEATIT_PUBLIC_URL:-}"
echo "MODEL + DATA + PUBLIC CAMPAIGN READY"
