#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

failures=()
check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "READY    $1"
  else
    echo "MISSING  $1"
    failures+=("command:$1")
  fi
}

check_command python
check_command node
check_command curl

[[ -f fixtures/hearttwin/manual_baseline.json ]] && echo "READY    demo fixture" || failures+=("demo fixture")
[[ -f fixtures/golden/probabilistic/fixed-only.json ]] && echo "READY    ensemble golden" || failures+=("ensemble golden")
[[ -f fixtures/golden/shadow_trials/synthetic-demo-case.json ]] && echo "READY    Shadow Trial golden" || failures+=("Shadow Trial golden")
[[ -f models/manifest.json ]] && echo "READY    model manifest" || failures+=("model manifest")

if [[ -n "${E2E_BASE_URL:-}" ]]; then
  api_base="${E2E_BASE_URL%/}"
  for path in /api/health/live /api/health/ready /api/v1/system-check /api/v1/models/status; do
    code="$(curl -sS -o /tmp/beatit-preflight-response -w '%{http_code}' "$api_base$path" || true)"
    echo "$code    $path"
    [[ "$code" == "2"* ]] || failures+=("http:$path:$code")
  done
else
  echo "SKIP     HTTP checks (set E2E_BASE_URL)"
fi

if ((${#failures[@]})); then
  printf 'DEMO NOT READY\nFailures:\n'
  printf ' - %s\n' "${failures[@]}"
  exit 1
fi

echo "DEMO READY"
