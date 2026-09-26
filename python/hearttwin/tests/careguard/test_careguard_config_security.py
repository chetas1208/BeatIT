"""Config endpoint must expose only booleans + non-secret model ids — never a key."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from python.hearttwin.careguard import config as cg_config


def test_public_config_contains_no_secret_values(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-SECRET-DO-NOT-LEAK-123")
    monkeypatch.setenv("OPENFDA_API_KEY", "openfda-SECRET-456")
    cfg = cg_config.public_config()
    blob = json.dumps(cfg)
    assert "sk-ant-SECRET-DO-NOT-LEAK-123" not in blob
    assert "openfda-SECRET-456" not in blob
    # But it must still report that they are configured.
    assert cfg["anthropic"]["configured"] is True
    assert cfg["openfda_key_configured"] is True


def test_config_endpoint_no_secret_leak(app_with_flags, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-TOPSECRET-789")
    app = app_with_flags(careguard_enabled=True, ANTHROPIC_API_KEY="sk-ant-TOPSECRET-789")
    client = TestClient(app)
    resp = client.get("/api/v1/careguard/config")
    assert resp.status_code == 200
    assert "sk-ant-TOPSECRET-789" not in resp.text
    body = resp.json()
    assert body["anthropic"]["configured"] is True
    assert body["feature_flags"]["careguard_enabled"] is True


def test_validate_env_flags_conflicting_privacy_settings(monkeypatch):
    monkeypatch.setenv("CAREGUARD_ENABLED", "true")
    monkeypatch.setenv("CAREGUARD_ALLOW_IDENTIFIABLE_DATA", "true")
    monkeypatch.setenv("CAREGUARD_REQUIRE_DEIDENTIFICATION", "true")
    report = cg_config.validate_env()
    assert report["ok"] is False
    assert any("conflicts" in e for e in report["errors"])


def test_validate_env_ok_with_defaults(monkeypatch):
    for k in ("CAREGUARD_ALLOW_IDENTIFIABLE_DATA",):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("CAREGUARD_ENABLED", "false")
    report = cg_config.validate_env()
    assert report["ok"] is True


def test_system_check_endpoint_shape(app_with_flags):
    app = app_with_flags(careguard_enabled=True)
    client = TestClient(app)
    body = client.get("/api/v1/careguard/system-check").json()
    assert "ready" in body
    assert "checks" in body
    assert "redis" in body["checks"]
    assert "safety_disclaimer" in body
