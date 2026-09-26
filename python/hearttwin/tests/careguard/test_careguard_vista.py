"""VISTA adapter: URL construction + safe degradation (hermetic, no network)."""

from __future__ import annotations

import pytest

from python.hearttwin.careguard.simulation import vista_adapter


def test_effective_base_appends_secret_path(monkeypatch):
    monkeypatch.setenv("CAREGUARD_VISTA_ENABLED", "true")
    monkeypatch.setenv("CAREGUARD_VISTA_API_BASE", "https://tunnel.example.com")
    monkeypatch.setenv("CAREGUARD_VISTA_ENDPOINT_SECRET", "v3d_abc123")
    assert vista_adapter.effective_base() == "https://tunnel.example.com/x/v3d_abc123"
    assert vista_adapter.is_configured() is True


def test_effective_base_respects_prebuilt_secret_path(monkeypatch):
    monkeypatch.setenv("CAREGUARD_VISTA_ENABLED", "true")
    monkeypatch.setenv("CAREGUARD_VISTA_API_BASE", "https://tunnel.example.com/x/v3d_xyz")
    monkeypatch.setenv("CAREGUARD_VISTA_ENDPOINT_SECRET", "v3d_xyz")
    assert vista_adapter.effective_base() == "https://tunnel.example.com/x/v3d_xyz"


def test_configured_without_secret_open_auth(monkeypatch):
    # Secret is OPTIONAL: a deployment with auth off (bare paths) is configured
    # with just the origin. effective_base is then the bare origin.
    monkeypatch.setenv("CAREGUARD_VISTA_ENABLED", "true")
    monkeypatch.setenv("CAREGUARD_VISTA_API_BASE", "https://tunnel.example.com")
    monkeypatch.delenv("CAREGUARD_VISTA_ENDPOINT_SECRET", raising=False)
    monkeypatch.delenv("VISTA3D_API_KEY", raising=False)
    monkeypatch.delenv("VISTA3D_ENDPOINT_SECRET", raising=False)
    assert vista_adapter.is_configured() is True
    assert vista_adapter.effective_base() == "https://tunnel.example.com"
    assert vista_adapter.status()["auth_mode"] == "open"


def test_not_configured_without_origin(monkeypatch):
    monkeypatch.setenv("CAREGUARD_VISTA_ENABLED", "true")
    monkeypatch.delenv("CAREGUARD_VISTA_API_BASE", raising=False)
    monkeypatch.delenv("VISTA3D_API_BASE", raising=False)
    assert vista_adapter.is_configured() is False


@pytest.mark.asyncio
async def test_segment_disabled_when_flag_off(monkeypatch):
    monkeypatch.setenv("CAREGUARD_VISTA_ENABLED", "false")
    out = await vista_adapter.segment(file_bytes=b"x", filename="v.nii.gz")
    assert out["status"] == "disabled"
    assert "clinician review" in out["label"].lower()


@pytest.mark.asyncio
async def test_segment_unconfigured_when_no_origin(monkeypatch):
    monkeypatch.setenv("CAREGUARD_VISTA_ENABLED", "true")
    monkeypatch.delenv("CAREGUARD_VISTA_API_BASE", raising=False)
    monkeypatch.delenv("VISTA3D_API_BASE", raising=False)
    out = await vista_adapter.segment(file_bytes=b"x", filename="v.nii.gz")
    assert out["status"] == "unconfigured"


@pytest.mark.asyncio
async def test_health_reports_missing_config(monkeypatch):
    monkeypatch.setenv("CAREGUARD_VISTA_ENABLED", "true")
    monkeypatch.delenv("CAREGUARD_VISTA_API_BASE", raising=False)
    monkeypatch.delenv("VISTA3D_API_BASE", raising=False)
    h = await vista_adapter.health()
    assert h["ok"] is False and "configured" in h["reason"].lower()
