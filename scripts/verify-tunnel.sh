#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
run_dir="${BEATIT_RUN_DIR:-$repo_root/.run/beatit}"
public_url="${1:-${BEATIT_PUBLIC_URL:-}}"
if [[ -z "$public_url" && -s "$run_dir/public-url" ]]; then
  public_url="$(<"$run_dir/public-url")"
fi
if [[ -z "$public_url" ]]; then
  echo "TUNNEL VERIFY BLOCKED: public URL is not configured" >&2
  exit 2
fi
public_url="${public_url%/}"
if [[ -s "$run_dir/cloudflared.pid" ]] && kill -0 "$(<"$run_dir/cloudflared.pid")" 2>/dev/null; then
  echo "cloudflared             PASS"
else
  echo "cloudflared             FAIL"
  exit 1
fi
for path in / /api/health/live /api/health/ready /api/v1/system-check /api/v1/models/status; do
  if curl --fail --silent --show-error --max-time 20 --proto '=https' --tlsv1.2 "$public_url$path" >/dev/null; then
    echo "public $path            PASS"
  else
    echo "public $path            FAIL"
    exit 1
  fi
done
echo "PUBLIC TUNNEL READY"
