#!/usr/bin/env python3
"""Stage 00 — environment & disk preflight, venv creation, dependency install.

Idempotent: re-running reuses an existing venv and only records versions.
Never deletes anything outside the data/ target directory.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

VENV = C.DATA_DIR / ".venv-data"
MIN_PY = (3, 11)


def check_python() -> None:
    if sys.version_info < MIN_PY:
        sys.exit(f"FATAL: Python {MIN_PY[0]}.{MIN_PY[1]}+ required, found {sys.version.split()[0]}")


def check_disk(log) -> None:
    cfg = C.load_config_safe()
    need = cfg.get("disk", {}).get("min_free_gb", 15) if cfg else 15
    gb = C.free_gb(C.DATA_DIR)
    log.info("free disk at target: %.1f GB (need %s GB)", gb, need)
    if gb < need:
        sys.exit(f"FATAL: insufficient disk space: {gb:.1f} GB < {need} GB")


def check_tools(log) -> dict:
    tools = {}
    for t in ("curl", "wget", "git", "java"):
        tools[t] = shutil.which(t)
        log.info("tool %-5s -> %s", t, tools[t] or "MISSING")
    if not (tools["curl"] or tools["wget"]):
        log.warning("neither curl nor wget present; pipeline falls back to Python urllib")
    if not tools["java"]:
        log.warning("Java not found; Synthea fallback (if triggered) will use the "
                    "deterministic Python synthetic generator instead.")
    return tools


def make_venv(log) -> Path:
    py = VENV / "bin" / "python"
    if not py.exists():
        log.info("creating venv at %s", VENV)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    else:
        log.info("venv already present: %s", VENV)
    subprocess.run([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip", "wheel"], check=True)
    return py


def install_deps(py: Path, log) -> None:
    req = C.DATA_DIR / "requirements-data.txt"
    log.info("installing dependencies from %s", req.name)
    r = subprocess.run([str(py), "-m", "pip", "install", "-q", "-r", str(req)])
    if r.returncode != 0:
        log.error("dependency install failed (rc=%s). Some wheels may be unavailable "
                  "for this interpreter; inspect logs/00_check_environment.log", r.returncode)
        sys.exit(r.returncode)


def record_versions(py: Path, log) -> None:
    out = subprocess.run([str(py), "-m", "pip", "freeze"], capture_output=True, text=True)
    (C.LOGS / "installed_versions.txt").write_text(out.stdout)
    env = {
        "python_executable": str(py),
        "python_version": subprocess.run(
            [str(py), "--version"], capture_output=True, text=True).stdout.strip(),
        "recorded_at": C.now_iso(),
    }
    C.write_json(C.LOGS / "environment.json", env)
    log.info("recorded %d installed packages", len(out.stdout.splitlines()))


def main() -> None:
    C.ensure_dirs()
    log = C.get_logger("00_check_environment")
    log.info("=== Stage 00: environment preflight ===")
    check_python()
    log.info("python OK: %s", sys.version.split()[0])
    check_disk(log)
    tools = check_tools(log)
    py = make_venv(log)
    install_deps(py, log)
    record_versions(py, log)
    C.write_json(C.LOGS / "tools.json", tools)
    log.info("=== Stage 00 complete. venv=%s ===", VENV)
    print(json.dumps({"venv": str(VENV), "python": str(py), "ok": True}))


if __name__ == "__main__":
    main()
