"""Isolation contract: with the flag OFF the app is byte-identical to baseline;
with it ON, CareGuard routes appear and every baseline route still exists.

This is the enforcement of the spec §1 preservation contract.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from python.hearttwin.tests.careguard.conftest import BASELINE_ROUTES, _route_set


def test_flag_off_adds_no_careguard_routes(app_with_flags):
    app = app_with_flags(careguard_enabled=False)
    routes = _route_set(app)
    careguard_routes = {p for _, p in routes if p.startswith("/api/v1/careguard")}
    assert careguard_routes == set(), f"CareGuard leaked routes while disabled: {careguard_routes}"


def test_flag_off_preserves_every_baseline_route(app_with_flags):
    app = app_with_flags(careguard_enabled=False)
    routes = _route_set(app)
    missing = BASELINE_ROUTES - routes
    assert not missing, f"Baseline DualBeat routes disappeared: {missing}"


def test_flag_on_preserves_every_baseline_route(app_with_flags):
    app = app_with_flags(careguard_enabled=True)
    routes = _route_set(app)
    missing = BASELINE_ROUTES - routes
    assert not missing, f"CareGuard removed baseline routes: {missing}"


def test_flag_on_mounts_careguard_core_routes(app_with_flags):
    app = app_with_flags(careguard_enabled=True)
    routes = _route_set(app)
    for path in (
        "/api/v1/careguard/health",
        "/api/v1/careguard/config",
        "/api/v1/careguard/system-check",
    ):
        assert ("GET", path) in routes, f"missing CareGuard route {path}"


def test_flag_off_careguard_health_is_404(app_with_flags):
    app = app_with_flags(careguard_enabled=False)
    client = TestClient(app)
    assert client.get("/api/v1/careguard/health").status_code == 404
    # And baseline health still works.
    assert client.get("/api/v1/health").status_code == 200


def test_flag_on_health_ok_and_baseline_health_ok(app_with_flags):
    app = app_with_flags(careguard_enabled=True)
    client = TestClient(app)
    cg = client.get("/api/v1/careguard/health")
    assert cg.status_code == 200
    assert cg.json()["status"] == "ok"
    assert "safety_disclaimer" in cg.json()
    assert client.get("/api/v1/health").status_code == 200
