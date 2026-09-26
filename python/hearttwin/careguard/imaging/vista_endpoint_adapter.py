"""VISTA endpoint capability handshake + class resolution (spec §12).

Adapts (does not replace) the existing ``python.hearttwin.tools.vista3d_client``.
Adds a `/capabilities` handshake that normalizes any endpoint response into
``EndpointCapabilities``. When the endpoint is unconfigured/unreachable it returns
an HONEST static fallback (``reachable=False``, ``source="static_fallback"``)
built from the client's verified label map — it never fabricates a live service.

Verified deployment facts (from vista3d_client): VISTA-3D emits the heart as a
single label (115) — no chamber split — plus aorta (6) and a pulmonary-vein
proxy (119). It does NOT segment coronary arteries, epicardial adipose tissue,
or pericoronary adipose tissue; those classes are reported unsupported.
"""
from __future__ import annotations

import os
from typing import Any

from python.hearttwin.careguard.imaging.schemas import EndpointCapabilities
from python.hearttwin.tools import vista3d_client as _client

# Structures the deployed endpoint can actually resolve as distinct masks.
_VERIFIED_SUPPORTED_CLASSES = ["heart", "aorta", "pulmonary artery"]
# Structures explicitly NOT available on this deployment (never claim these).
_KNOWN_UNSUPPORTED = ["coronary arteries", "epicardial adipose tissue",
                      "pericoronary adipose tissue", "left ventricle",
                      "right ventricle", "myocardium"]


def _base_url() -> str:
    return _client._base_url()


def is_configured() -> bool:
    return _client.is_configured()


def _static_fallback(reason: str) -> EndpointCapabilities:
    return EndpointCapabilities(
        service="vista3d",
        version="unknown",
        supported_modalities=["CT"],
        supported_classes=list(_VERIFIED_SUPPORTED_CLASSES),
        input_formats=["nifti"],
        maximum_upload_bytes=None,
        supports_signed_urls=False,
        supports_batch=False,
        supports_async_jobs=True,
        returns_confidence=False,
        returns_masks=True,
        returns_measurements=False,
        reachable=False,
        source="static_fallback",
        warnings=[reason,
                  "Capabilities are the conservatively verified set; "
                  f"unsupported on this deployment: {', '.join(_KNOWN_UNSUPPORTED)}."],
    )


def _normalize_live(body: dict) -> EndpointCapabilities:
    """Map a live /capabilities response into the normalized schema."""
    classes = (body.get("supported_classes") or body.get("classes")
               or body.get("labels") or [])
    if isinstance(classes, dict):
        classes = list(classes.keys())
    return EndpointCapabilities(
        service=body.get("service") or body.get("model") or "vista3d",
        version=str(body.get("version") or body.get("model_version") or ""),
        supported_modalities=body.get("supported_modalities") or ["CT"],
        supported_classes=[str(c) for c in classes],
        input_formats=body.get("input_formats") or ["nifti"],
        maximum_upload_bytes=body.get("maximum_upload_bytes"),
        supports_signed_urls=bool(body.get("supports_signed_urls", False)),
        supports_batch=bool(body.get("supports_batch", False)),
        supports_async_jobs=bool(body.get("supports_async_jobs", True)),
        returns_confidence=bool(body.get("returns_confidence", False)),
        returns_masks=bool(body.get("returns_masks", True)),
        returns_measurements=bool(body.get("returns_measurements", False)),
        reachable=True,
        source="live",
    )


async def discover_capabilities() -> EndpointCapabilities:
    """Async capability handshake. Never raises."""
    if not is_configured():
        return _static_fallback("VISTA endpoint is not configured "
                                "(VISTA3D_ENABLED false / API base empty).")
    cap_path = os.environ.get("CAREGUARD_VISTA_CAPABILITIES_PATH", "/capabilities")
    try:
        import httpx
        async with httpx.AsyncClient() as c:
            resp = await c.get(f"{_base_url()}{cap_path}", headers=_client._headers(),
                               timeout=_client._timeout())
        if resp.status_code == 200:
            return _normalize_live(resp.json())
        # endpoint reachable but no capabilities route -> probe health instead
        ok, warns = await _client.health_check()
        fb = _static_fallback(f"/capabilities returned HTTP {resp.status_code}; "
                              "using verified fallback class set.")
        fb.reachable = ok
        fb.source = "live" if ok else "unavailable"
        fb.warnings += warns
        return fb
    except Exception as exc:
        return _static_fallback(f"capability handshake failed: {type(exc).__name__}: {exc}")


def discover_capabilities_sync() -> EndpointCapabilities:
    """Sync wrapper for pipeline scripts."""
    import asyncio
    try:
        return asyncio.run(discover_capabilities())
    except RuntimeError:
        # already inside a loop
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(discover_capabilities())
        finally:
            loop.close()


def resolve_requested_classes(desired: list[str], caps: EndpointCapabilities
                              ) -> tuple[list[str], list[str], list[str]]:
    """Split desired classes into (accepted, rejected, warnings) using ONLY the
    endpoint's declared capabilities. Never requests an unsupported class."""
    supported = {c.strip().lower() for c in caps.supported_classes}
    accepted, rejected, warnings = [], [], []
    for d in desired:
        dn = d.strip().lower()
        if dn in supported:
            accepted.append(d)
        else:
            rejected.append(d)
            warnings.append(f"class '{d}' not in endpoint capabilities — not requested")
    return accepted, rejected, warnings
