#!/usr/bin/env python
"""CareGuard verification gate.

Checks, in order:
  1. feature-flag isolation (flag off adds no routes / removes none)
  2. environment validation (no conflicting privacy settings)
  3. research manifest present + parseable
  4. source freshness policy sane
  5. forbidden runtime phrase ("prior work") absent from runtime code
  6. no obvious secret/PHI logging posture
  7. medication source policy (DrugBank disabled w/o license, no Kaggle authority)

Exit non-zero on any hard failure. Run: python scripts/verify_careguard.py
"""

from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAIL: list[str] = []
WARN: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def main() -> int:
    # 1. Feature-flag isolation.
    os.environ["CAREGUARD_ENABLED"] = "false"
    import importlib

    import python.hearttwin.api as api

    importlib.reload(api)

    def route_paths(app):
        out = set()

        def walk(coll):
            for r in coll:
                p = getattr(r, "path", None)
                if p:
                    out.add(p)
                inner = getattr(r, "original_router", None)
                if inner is not None and getattr(inner, "routes", None):
                    walk(inner.routes)
                if getattr(r, "routes", None):
                    walk(r.routes)
        walk(app.routes)
        return out

    off = route_paths(api.app)
    check("flag-off adds no CareGuard routes", not any("careguard" in p for p in off))
    check("flag-off preserves baseline health route", "/api/v1/health" in off)

    os.environ["CAREGUARD_ENABLED"] = "true"
    importlib.reload(api)
    on = route_paths(api.app)
    check("flag-on mounts CareGuard routes", any("careguard" in p for p in on))
    check("flag-on preserves baseline routes", "/api/v1/health" in on and "/api/v1/config" in on)

    # 2. Environment validation.
    from python.hearttwin.careguard import config as cg_config

    report = cg_config.validate_env()
    check("environment validation ok", report["ok"], "; ".join(report["errors"]))

    # 3. Research manifest.
    manifest = ROOT / "docs" / "careguard" / "research-manifest.yaml"
    check("research manifest present", manifest.exists(), str(manifest))
    if manifest.exists():
        try:
            import yaml

            data = yaml.safe_load(manifest.read_text())
            check("manifest parses + has sources", bool(data.get("sources")))
        except Exception as exc:  # noqa: BLE001
            check("manifest parses", False, str(exc))

    # 4. Source freshness policy.
    from python.hearttwin.careguard.config import max_source_age_days

    check("max source age sane", 30 <= max_source_age_days() <= 3650, str(max_source_age_days()))

    # 5. Forbidden runtime phrase.
    from python.hearttwin.careguard.constants import FORBIDDEN_RUNTIME_PHRASE

    offenders = []
    for base in ("python/hearttwin/careguard", "web/components/careguard", "web/lib/careguardApi.ts",
                 "web/app/careguard"):
        p = ROOT / base
        files = p.rglob("*") if p.is_dir() else [p]
        for f in files:
            if f.suffix in (".py", ".ts", ".tsx") and f.is_file():
                if FORBIDDEN_RUNTIME_PHRASE in f.read_text().lower():
                    offenders.append(str(f.relative_to(ROOT)))
    check(f"forbidden phrase {FORBIDDEN_RUNTIME_PHRASE!r} absent from runtime code", not offenders,
          ", ".join(offenders))

    # 6. Logging posture.
    check("raw model IO logging off by default",
          not cg_config.flags.log_raw_model_inputs() and not cg_config.flags.log_raw_model_outputs())

    # 7. Medication source policy.
    from python.hearttwin.careguard.medications import source_registry

    ok, reason = source_registry.drugbank_loadable()
    check("DrugBank disabled without confirmed license", not ok, reason)
    try:
        source_registry.assert_not_prohibited("kaggle_medicine_dataset")
        check("Kaggle rejected as clinical authority", False)
    except Exception:
        check("Kaggle rejected as clinical authority", True)

    print()
    if FAIL:
        print(f"VERIFY:CAREGUARD FAILED — {len(FAIL)} check(s): {', '.join(FAIL)}")
        return 1
    print("VERIFY:CAREGUARD PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
