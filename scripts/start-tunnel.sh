#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
run_dir="${BEATIT_RUN_DIR:-$repo_root/.run/beatit}"
mkdir -p "$run_dir"
api_url="${BEATIT_ORIGIN_URL:-http://127.0.0.1:8000}"
if ! curl -fsS --max-time 5 "$api_url/api/health/live" >/dev/null; then
  echo "TUNNEL START FAILED: BeatIT origin is not healthy at $api_url" >&2
  exit 1
fi
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "TUNNEL START FAILED: cloudflared is not installed" >&2
  exit 1
fi
if [[ -s "$run_dir/cloudflared.pid" ]] && kill -0 "$(<"$run_dir/cloudflared.pid")" 2>/dev/null; then
  echo "TUNNEL ALREADY RUNNING pid=$(<"$run_dir/cloudflared.pid")"
  exit 0
fi

log_file="$run_dir/cloudflared.log"
pid_file="$run_dir/cloudflared.pid"
if [[ -n "${BEATIT_CLOUDFLARE_TUNNEL_TOKEN:-}" ]]; then
  nohup cloudflared tunnel run --token "$BEATIT_CLOUDFLARE_TUNNEL_TOKEN" >"$log_file" 2>&1 &
elif [[ -n "${BEATIT_CLOUDFLARE_CONFIG:-}" && -f "$BEATIT_CLOUDFLARE_CONFIG" ]]; then
  nohup cloudflared tunnel --config "$BEATIT_CLOUDFLARE_CONFIG" run >"$log_file" 2>&1 &
else
  echo "TUNNEL START BLOCKED: no named/managed Cloudflare token or config is available" >&2
  echo "Quick Tunnels are intentionally not used because BeatIT's live trace uses SSE." >&2
  exit 2
fi
echo $! >"$pid_file"
echo "TUNNEL STARTED pid=$(<"$pid_file") log=$log_file"
