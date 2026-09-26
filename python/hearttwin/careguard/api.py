"""CareGuard FastAPI router — all routes under /api/v1/careguard.

Mounted by ``python/hearttwin/api.py`` ONLY when ``CAREGUARD_ENABLED=true`` (see
``build_router``). Existing DualBeat routes are never touched. Every response
carries the CareGuard disclaimer; the config endpoint returns booleans only.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from python.hearttwin.careguard import config as cg_config
from python.hearttwin.careguard.constants import DISCLAIMER
from python.hearttwin.careguard.errors import (
    CareGuardError,
    EvidenceUnavailableError,
    FhirValidationError,
    RunNotFoundError,
    SafetyBoundaryError,
)
from python.hearttwin.careguard.memory import redis_store


def _with_disclaimer(payload: dict[str, Any]) -> dict[str, Any]:
    payload.setdefault("safety_disclaimer", DISCLAIMER)
    return payload


async def _db_health() -> dict[str, Any]:
    from python.hearttwin.careguard.db import pool as dbpool

    if not dbpool.is_configured():
        return {"enabled": False, "configured": False, "reachable": False, "kind": "none"}
    try:
        import asyncio

        reachable = await asyncio.wait_for(dbpool.ping(), timeout=5.0)
        return {"enabled": True, "configured": True, "reachable": bool(reachable), "kind": "postgres"}
    except Exception as exc:  # noqa: BLE001 — report, don't crash system-check
        return {"enabled": True, "configured": True, "reachable": False,
                "kind": "postgres", "error": type(exc).__name__}


def register_startup(app) -> None:
    """Run the durable-schema migration once at startup (best-effort)."""

    @app.on_event("startup")
    async def _careguard_migrate() -> None:  # noqa: ANN202
        try:
            from python.hearttwin.careguard.db.migrate import migrate

            await migrate()
        except Exception:  # noqa: BLE001 — durability is additive; never block startup
            pass


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/careguard", tags=["careguard"])

    # -- health ------------------------------------------------------------
    @router.get("/health")
    async def health() -> dict:
        return _with_disclaimer(
            {"status": "ok", "module": "careguard", "version": "0.1.0"}
        )

    # -- config (secret-free) ---------------------------------------------
    @router.get("/config")
    async def config() -> dict:
        return _with_disclaimer(cg_config.public_config())

    # -- system-check ------------------------------------------------------
    @router.get("/system-check")
    async def system_check() -> dict:
        env_report = cg_config.validate_env()
        redis_health = await redis_store.health()
        db_health = await _db_health()
        checks = {
            "feature_flag": cg_config.flags.careguard_enabled(),
            "anthropic_configured": cg_config.anthropic_configured(),
            "anthropic_keys": cg_config.anthropic_key_count(),
            "redis": redis_health,
            "database": db_health,
            "env_validation": env_report,
            "deidentification_required": cg_config.flags.require_deidentification(),
            "external_research_allowed": cg_config.flags.external_research_allowed(),
        }
        ready = env_report["ok"]
        return _with_disclaimer({"ready": ready, "checks": checks})

    # Later phases register FHIR import, runs, getters, CDS hooks on this router.
    from python.hearttwin.careguard.api_routes import register_routes

    register_routes(router)

    return router


# ---------------------------------------------------------------------------
# Shared exception mapping (registered on the main app by the integration seam).
# ---------------------------------------------------------------------------
def register_exception_handlers(app) -> None:
    @app.exception_handler(SafetyBoundaryError)
    async def _safety(_request, exc: SafetyBoundaryError):  # noqa: ANN001
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=422,
            content=_with_disclaimer(
                {"error": "safety_boundary", "message": str(exc), "reason": exc.reason}
            ),
        )

    @app.exception_handler(FhirValidationError)
    async def _fhir(_request, exc: FhirValidationError):  # noqa: ANN001
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=400,
            content=_with_disclaimer(
                {"error": "fhir_validation", "message": str(exc), "issues": exc.issues}
            ),
        )

    @app.exception_handler(RunNotFoundError)
    async def _notfound(_request, exc: RunNotFoundError):  # noqa: ANN001
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404,
            content=_with_disclaimer({"error": "not_found", "message": str(exc)}),
        )

    @app.exception_handler(EvidenceUnavailableError)
    async def _evidence(_request, exc: EvidenceUnavailableError):  # noqa: ANN001
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=422,
            content=_with_disclaimer({"error": "evidence_unavailable", "message": str(exc)}),
        )

    @app.exception_handler(CareGuardError)
    async def _generic(_request, exc: CareGuardError):  # noqa: ANN001
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=500,
            content=_with_disclaimer({"error": "careguard_error", "message": str(exc)}),
        )
