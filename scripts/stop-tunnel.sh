#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
run_dir="${BEATIT_RUN_DIR:-$repo_root/.run/beatit}"
pid_file="$run_dir/cloudflared.pid"
if [[ ! -s "$pid_file" ]]; then
  echo "TUNNEL STOP: no recorded tunnel pid"
  exit 0
fi
pid="$(<"$pid_file")"
if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  for _ in {1..20}; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.1
  done
fi
rm -f -- "$pid_file"
echo "TUNNEL STOPPED pid=$pid"
