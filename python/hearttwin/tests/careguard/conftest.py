"""Shared fixtures for CareGuard tests.

Key helper: ``app_with_flags`` rebuilds the REAL FastAPI app under a chosen
CAREGUARD_ENABLED value by reloading ``python.hearttwin.api``. This is how the
isolation tests prove flag-off == baseline against the actual app, not a mock.
"""

from __future__ import annotations

import importlib
import json
import pathlib

import pytest

from python.hearttwin.careguard.memory import redis_store

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
FIXTURE_DIR = REPO_ROOT / "fixtures" / "careguard"

# The 14 baseline DualBeat routes that must always survive (spec §5 / audit §5).
BASELINE_ROUTES = {
    ("POST", "/api/v1/cases"),
    ("GET", "/api/v1/cases/{case_id}"),
    ("POST", "/api/v1/cases/{case_id}/extract"),
    ("POST", "/api/v1/cases/{case_id}/files"),
    ("GET", "/api/v1/cases/{case_id}/harness"),
    ("POST", "/api/v1/cases/{case_id}/operate"),
    ("POST", "/api/v1/cases/{case_id}/self-improve"),
    ("POST", "/api/v1/cases/{case_id}/simulate-recovery"),
    ("GET", "/api/v1/cases/{case_id}/trace"),
    ("GET", "/api/v1/cases/{case_id}/trace/stream"),
    ("GET", "/api/v1/config"),
    ("POST", "/api/v1/ecg/diagnose"),
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/system-check"),
}


def _route_set(app):
    """Flatten every (method, path), recursing into nested routers/mounts.

    This FastAPI version keeps ``include_router`` routes inside a nested
    ``_IncludedRouter`` (path=None) rather than flattening them onto
    ``app.routes``; the recursion is required to see CareGuard's routes.
    """
    routes: set[tuple[str, str]] = set()

    def walk(collection):
        for r in collection:
            methods = getattr(r, "methods", None) or set()
            path = getattr(r, "path", None)
            if path and methods:
                for m in methods:
                    routes.add((m, path))
            # Follow nested routers. This FastAPI version wraps include_router in
            # an _IncludedRouter whose children live on original_router.routes
            # (or include_context.included_router.routes), not on .routes.
            nested = getattr(r, "routes", None)
            if nested:
                walk(nested)
            inner = getattr(r, "original_router", None)
            if inner is not None and getattr(inner, "routes", None):
                walk(inner.routes)
            ctx = getattr(r, "include_context", None)
            inc = getattr(ctx, "included_router", None) if ctx is not None else None
            if inc is not None and getattr(inc, "routes", None):
                walk(inc.routes)

    walk(getattr(app, "routes", []))
    return routes


@pytest.fixture
def app_with_flags(monkeypatch):
    """Return a builder: call with careguard_enabled=bool → fresh reloaded app."""
    def _build(*, careguard_enabled: bool, **env):
        monkeypatch.setenv("CAREGUARD_ENABLED", "true" if careguard_enabled else "false")
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        redis_store.reset_fallback()
        import python.hearttwin.api as api_module

        importlib.reload(api_module)
        return api_module.app

    yield _build
    # Restore the module to its default (flag-off) state for other tests.
    monkeypatch.setenv("CAREGUARD_ENABLED", "false")
    import python.hearttwin.api as api_module

    importlib.reload(api_module)


@pytest.fixture
def route_set():
    return _route_set


@pytest.fixture
def load_fixture():
    def _load(name: str) -> dict:
        return json.loads((FIXTURE_DIR / name).read_text())

    return _load
