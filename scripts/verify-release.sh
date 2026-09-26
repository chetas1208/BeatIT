#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
deep="${1:-}"
cd "$repo_root"

echo "BEATIT RELEASE VERIFICATION"

python scripts/verify_env.py --mode local-dev >/dev/null
echo "Environment          PASS"
python scripts/build_release_golden.py >/dev/null
./scripts/verify-demo.sh
echo "Demo Data            PASS"

if git grep -I -n -E '(^|[=:])[[:space:]]*(sk-[A-Za-z0-9]{20,}|nvapi-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})' -- . >/dev/null 2>&1; then
  echo "Secrets              FAIL"
  exit 1
fi
if rg -I -l -E '(^|[=:])[[:space:]]*(sk-[A-Za-z0-9]{20,}|nvapi-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})' \
  --glob '!.env*' --glob '!node_modules/**' --glob '!.venv/**' --glob '!*.lock' . >/dev/null 2>&1; then
  echo "Secrets              FAIL"
  exit 1
fi
echo "Secrets              PASS"

backend_log="$(mktemp)"
PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev pytest -q >"$backend_log" 2>&1
tail -1 "$backend_log"
echo "Backend              PASS"

(cd web && ./node_modules/.bin/next build >/dev/null && ./node_modules/.bin/tsc --noEmit && ./node_modules/.bin/eslint components/layout/AppShell.tsx components/product lib/product lib/twin/comparison types/shadow-trial.ts types/missing-piece.ts >/dev/null)
mapfile -t frontend_tests < <(find web -path web/node_modules -prune -o -type f -name '*.test.ts' -print | sort)
node --experimental-strip-types --loader ./web/tests/alias-loader.mjs --test "${frontend_tests[@]}" >/dev/null
echo "Frontend             PASS"

if [[ "$deep" == "--deep" ]]; then
  PYTHONPATH=. uv run --python /opt/miniconda/bin/python3.13 --project . --extra dev python scripts/verify_api_e2e.py
  echo "API/Persistence      PASS"
  api_port=18000
  web_port=13001
  for pair in "8010 3010" "8000 3001" "${api_port} ${web_port}"; do
    read -r ap wp <<<"$pair"
    BEATIT_API_PORT="$ap" BEATIT_WEB_PORT="$wp" ./deploy/beatit down >/dev/null 2>&1 || true
  done
  BEATIT_API_PORT="$api_port" BEATIT_WEB_PORT="$web_port" ./deploy/beatit up
  trap 'BEATIT_API_PORT="$api_port" BEATIT_WEB_PORT="$web_port" ./deploy/beatit down >/dev/null 2>&1 || true' EXIT
  E2E_BASE_URL="http://127.0.0.1:${api_port}" ./scripts/demo-preflight.sh
  E2E_BASE_URL="http://127.0.0.1:${api_port}" PYTHONPATH=. python scripts/run_local_smoke.py
  curl -fsS "http://127.0.0.1:${web_port}/" >/dev/null
  echo "Deployment           PASS (local loopback lifecycle)"
  PYTHONPATH=. python scripts/verify_failure_injection.py
  echo "Failure injection    PASS"
  if E2E_WEB_URL="http://127.0.0.1:${web_port}" PYTHONPATH=. python scripts/browser_product_e2e.py; then
    echo "Browser E2E          PASS"
    export BEATIT_BROWSER_E2E_PASS=1
  else
    echo "Browser E2E          FAIL (see scripts/browser_product_e2e.py)"
    export BEATIT_BROWSER_E2E_PASS=0
    exit 1
  fi
else
  echo "Deep E2E             SKIP (run ./scripts/verify-release.sh --deep)"
fi

mkdir -p artifacts
export DEEP_MODE="${deep:-}"
export BACKEND_SUMMARY="$backend_log"
python - <<'PY'
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

manifest = json.loads(Path("data/manifest.json").read_text())
release_manifest = {}
if Path("RELEASE_MANIFEST.json").exists():
    release_manifest = json.loads(Path("RELEASE_MANIFEST.json").read_text())
try:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    source = f"working-tree@{head}" if dirty else head
except Exception:
    head = None
    dirty = True
    source = "working-tree"
backend_summary = Path(os.environ.get("BACKEND_SUMMARY", "")).read_text() if os.environ.get("BACKEND_SUMMARY") else ""
pytest_match = re.search(r"(\d+) passed", backend_summary)
pytest_passed = int(pytest_match.group(1)) if pytest_match else None
deep = os.environ.get("DEEP_MODE") == "--deep"
browser_e2e = os.environ.get("BEATIT_BROWSER_E2E_PASS") == "1"
open_gates = [
    "supported browser and accessibility journey",
    "public reverse proxy/TLS deployment",
    "external model live inference",
    "database/Redis fault injection and backup restore",
    "patient-data security hardening",
]
report = {
    "verification_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "source_identifier": source,
    "source_commit": head,
    "working_tree_dirty": dirty,
    "beatit_version": release_manifest.get("beatit_version"),
    "dataset_version": manifest.get("dataset_version"),
    "synthetic": manifest.get("synthetic", False),
    "engine_versions": release_manifest.get("engine_versions")
    or {
        "physiology": "canonical-repository-engine",
        "ensemble": "m5.5-ensemble-projection-v1",
        "shadow_trial": "m6-shadow-trial-v1",
        "missing_piece": "m8-tier1-bounded-v1",
    },
    "tests": {
        "python_passed": pytest_passed,
        "frontend_runtime": "all *.test.ts",
    },
    "model_runtime": {
        "language": "optional; liveness/readiness separate from deterministic core",
        "vista3d": "optional",
    },
    "persistence": "local SQLite/file-backed E2E verified" if deep else "not exercised (run --deep)",
    "offline": "local deterministic path verified" if deep else "not exercised (run --deep)",
    "deployment_loopback": "verified" if deep else "not exercised (run --deep)",
    "browser_e2e": "product modes + WebGL canvas smoke" if browser_e2e else ("not exercised" if not deep else "failed"),
    "status": "DO_NOT_SHIP",
    "open_gates": open_gates,
}
Path("artifacts/release-verification.json").write_text(json.dumps(report, indent=2) + "\n")
print("Machine report     PASS artifacts/release-verification.json")
PY

echo "RELEASE STATUS"
if [[ "$deep" == "--deep" ]]; then
  echo "DO NOT SHIP — browser, external model, proxy/TLS, and failure-injection gates remain separately required"
else
  echo "DO NOT SHIP — deep verification not requested"
fi
