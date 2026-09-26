"""CDS Hooks routes (attached to the CareGuard router)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from python.hearttwin.careguard.cds_hooks import cards, discovery, order_sign, patient_view
from python.hearttwin.careguard.constants import DISCLAIMER


def _case_id_from_hook(body: dict[str, Any]) -> str:
    ctx = body.get("context", {}) or {}
    return ctx.get("careguardCaseId") or ctx.get("patientId") or ""


def attach(router: APIRouter) -> None:
    @router.get("/cds-services")
    async def cds_services() -> dict:
        return discovery.services()

    @router.post("/cds-services/patient-view")
    async def patient_view_hook(request: Request) -> dict:
        body = await request.json()
        case_id = _case_id_from_hook(body)
        built = await patient_view.build_cards(case_id)
        _validate(built)
        return {"cards": built, "safety_disclaimer": DISCLAIMER}

    @router.post("/cds-services/order-select")
    async def order_select_hook(request: Request) -> dict:
        body = await request.json()
        case_id = _case_id_from_hook(body)
        drafts = _extract_draft_meds(body)
        # order-select shows conflicts + evidence-backed candidates; never modifies the order.
        built = await order_sign.build_cards(case_id, drafts)
        _validate(built)
        return {"cards": built, "systemActions": [], "safety_disclaimer": DISCLAIMER}

    @router.post("/cds-services/order-sign")
    async def order_sign_hook(request: Request) -> dict:
        body = await request.json()
        case_id = _case_id_from_hook(body)
        drafts = _extract_draft_meds(body)
        built = await order_sign.build_cards(case_id, drafts)
        _validate(built)
        # Never return an executable order — cards only.
        return {"cards": built, "systemActions": [], "safety_disclaimer": DISCLAIMER}


def _validate(built: list[dict]) -> None:
    for card in built:
        issues = cards.validate_card(card)
        if issues:
            card["_validation_warnings"] = issues


def _extract_draft_meds(body: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull medication names from a FHIR draftOrders bundle in the hook context."""
    out: list[dict[str, Any]] = []
    draft = (body.get("context", {}) or {}).get("draftOrders", {})
    for entry in (draft.get("entry", []) if isinstance(draft, dict) else []):
        res = (entry or {}).get("resource", {})
        concept = res.get("medicationCodeableConcept", {})
        text = concept.get("text")
        rxcui = None
        for c in concept.get("coding", []) or []:
            if "rxnorm" in (c.get("system", "").lower()):
                rxcui = c.get("code")
        if text or rxcui:
            out.append({"name": text or "", "rxcui": rxcui})
    return out
