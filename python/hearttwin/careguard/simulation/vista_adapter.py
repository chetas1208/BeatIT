"""CareGuard VISTA-3D adapter.

Reuses DualBeat's existing, tested ``vista3d_client`` (spec §12) but targets a
Cloudflare-tunneled deployment whose paths are secret-in-path
(``{origin}/x/{ENDPOINT_SECRET}/...``). This adapter builds the effective base
``{CAREGUARD_VISTA_API_BASE}/x/{CAREGUARD_VISTA_ENDPOINT_SECRET}`` and points the
existing client at it.

VISTA runs only when: the feature is enabled, the endpoint + secret are
configured, and the user initiated image processing. Output is labeled
"Model-derived research segmentation requiring clinician review." VISTA failure
never blocks non-imaging CareGuard functions; nothing here raises.
"""

from __future__ import annotations

import os
from typing import Any

from python.hearttwin.careguard.feature_flags import vista_enabled

VISTA_LABEL = "Model-derived research segmentation requiring clinician review."


def _origin() -> str:
    return (os.environ.get("CAREGUARD_VISTA_API_BASE", "")
            or os.environ.get("VISTA3D_API_BASE", "")).strip().rstrip("/")


def _secret() -> str:
    return (os.environ.get("CAREGUARD_VISTA_ENDPOINT_SECRET", "")
            or os.environ.get("VISTA3D_ENDPOINT_SECRET", "")
            or os.environ.get("VISTA3D_API_KEY", "")).strip()


def effective_base() -> str:
    """Full base. Appends the secret path segment ONLY when a secret is set
    (secret-in-path deployments); with auth off, the bare origin is the base."""
    origin, secret = _origin(), _secret()
    if not origin:
        return ""
    if secret and "/x/" not in origin:
        return f"{origin}/x/{secret}"
    return origin


def is_configured() -> bool:
    # Secret is OPTIONAL — the deployment may run with auth off (bare paths).
    return vista_enabled() and bool(_origin())


def status() -> dict[str, Any]:
    return {
        "enabled": vista_enabled(),
        "origin_configured": bool(_origin()),
        "secret_configured": bool(_secret()),
        "auth_mode": "secret_in_path" if _secret() else "open",
        "ready": is_configured(),
        "external_service": True,
        "label": VISTA_LABEL,
    }


def _point_existing_client_at_deployment() -> None:
    """Configure the existing DualBeat vista3d_client to target this deployment."""
    base = effective_base()
    if base:
        os.environ["VISTA3D_API_BASE"] = base
        os.environ["VISTA3D_ENABLED"] = "true"
        # secret also sent as header by the client — harmless for path-secret auth.
        if _secret():
            os.environ.setdefault("VISTA3D_API_KEY", _secret())


async def health() -> dict[str, Any]:
    """Best-effort VISTA health probe. Never raises."""
    if not is_configured():
        return {"ok": False, "reachable": False,
                "reason": "VISTA not fully configured (need CAREGUARD_VISTA_ENABLED, "
                          "CAREGUARD_VISTA_API_BASE, and CAREGUARD_VISTA_ENDPOINT_SECRET).",
                "status": status()}
    _point_existing_client_at_deployment()
    try:
        from python.hearttwin.tools import vista3d_client

        ok, warnings = await vista3d_client.health_check()
        return {"ok": bool(ok), "reachable": bool(ok), "warnings": warnings,
                "base": effective_base(), "label": VISTA_LABEL}
    except Exception as exc:  # noqa: BLE001 — imaging never breaks the pipeline
        return {"ok": False, "reachable": False, "error": type(exc).__name__, "detail": str(exc)[:200]}


async def segment(
    *,
    file_bytes: bytes,
    filename: str,
    target_classes: list[str] | None = None,
    file_id: str | None = None,
) -> dict[str, Any]:
    """Submit a CT/MRI volume for segmentation via the existing client. Returns a
    CareGuard-shaped, clinician-review-labeled result; never raises."""
    classes = target_classes or ["heart", "aorta", "left atrium", "left ventricle", "myocardium"]
    if not vista_enabled():
        return {"status": "disabled", "label": VISTA_LABEL,
                "note": "CAREGUARD_VISTA_ENABLED is false — segmentation skipped."}
    if not is_configured():
        return {"status": "unconfigured", "label": VISTA_LABEL,
                "note": "VISTA endpoint/secret not configured — set CAREGUARD_VISTA_ENDPOINT_SECRET.",
                "status_detail": status()}
    _point_existing_client_at_deployment()
    try:
        from python.hearttwin.tools import vista3d_client

        result = await vista3d_client.run_segmentation(
            file_bytes=file_bytes, filename=filename,
            target_classes=classes, file_id=file_id, mode="automatic",
        )
        payload = result.model_dump() if hasattr(result, "model_dump") else dict(result)
        payload["label"] = VISTA_LABEL
        payload["clinician_review_required"] = True
        payload["base"] = effective_base()
        return payload
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "label": VISTA_LABEL,
                "error": type(exc).__name__, "detail": str(exc)[:200]}


def _same_host_as_endpoint(url: str) -> bool:
    """Only fetch URLs on the configured VISTA origin — we never let a caller-
    supplied URL make our server fetch an arbitrary address (mirrors the VISTA
    deployment's own CALLBACK_ALLOW_PRIVATE_HOSTS=false SSRF hardening)."""
    from urllib.parse import urlparse

    origin = _origin()
    if not origin or not url:
        return False
    try:
        return urlparse(url).netloc == urlparse(origin).netloc and urlparse(url).scheme in ("http", "https")
    except Exception:  # noqa: BLE001
        return False


async def fetch_result(url: str) -> dict[str, Any]:
    """Fetch a server-returned status/result/metadata URL directly.

    The VISTA server now hands back tunnel-reachable URLs (its V3D_PUBLIC_BASE_URL
    fix), so we follow those rather than reconstructing paths. The URL must be on
    the configured VISTA origin — arbitrary hosts are refused (SSRF guard).
    """
    if not _same_host_as_endpoint(url):
        return {"status": "refused", "reason": "URL host is not the configured VISTA endpoint (SSRF guard)",
                "label": VISTA_LABEL}
    try:
        import httpx

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
        ctype = resp.headers.get("content-type", "")
        out: dict[str, Any] = {"http": resp.status_code, "content_type": ctype,
                               "label": VISTA_LABEL, "clinician_review_required": True}
        if "application/json" in ctype:
            out["body"] = resp.json()
        else:
            out["bytes"] = len(resp.content)  # e.g. NIfTI mask / preview image
        return out
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": type(exc).__name__, "detail": str(exc)[:200], "label": VISTA_LABEL}


async def job_result(job_id: str, *, result_url: str | None = None) -> dict[str, Any]:
    """Fetch a segmentation job's status/metadata. Prefers the server-returned
    tunnel URLs; falls back to reconstructing paths from the effective base."""
    if not is_configured():
        return {"status": "unconfigured", "label": VISTA_LABEL}
    if result_url and _same_host_as_endpoint(result_url):
        return {"job_id": job_id, "result": await fetch_result(result_url), "label": VISTA_LABEL}
    base = effective_base()
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            meta = await client.get(f"{base}/api/v1/jobs/{job_id}/metadata")
            status_resp = await client.get(f"{base}/api/v1/jobs/{job_id}")
        return {
            "job_id": job_id,
            "job_status": status_resp.json() if status_resp.status_code == 200 else {"http": status_resp.status_code},
            "metadata": meta.json() if meta.status_code == 200 else {"http": meta.status_code},
            "label": VISTA_LABEL, "clinician_review_required": True,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": type(exc).__name__, "detail": str(exc)[:200], "label": VISTA_LABEL}
