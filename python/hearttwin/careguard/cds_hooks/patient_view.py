"""patient-view hook → advisory cards from a case's CareGuard artifacts."""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.cds_hooks.cards import make_card
from python.hearttwin.careguard.memory import keys, redis_store


async def build_cards(case_id: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    context = await redis_store.get_json(keys.case_context(case_id)) or {}
    conflicts = await redis_store.get_json(keys.case_contraindications(case_id)) or []
    critic = await redis_store.get_json(keys.case_critic(case_id)) or {}
    review_url = f"/careguard/case/{case_id}"

    missing = (context.get("missing_critical_evidence") or [])
    if missing:
        cards.append(make_card(
            summary="Missing evidence for a safe cardiac review",
            detail="\n".join(f"- {m}" for m in missing),
            indicator="warning",
            evidence_url=review_url,
        ))

    for cf in conflicts:
        if cf.get("severity") in ("high", "blocked"):
            cards.append(make_card(
                summary=f"Medication caution: {cf.get('medication_name')}",
                detail=cf.get("statement", ""),
                indicator="warning" if cf["severity"] == "high" else "critical",
                evidence_url=review_url,
                override_reasons=["Clinician has reviewed and accepts the risk",
                                  "Additional monitoring arranged"],
            ))

    if critic and not critic.get("safe_to_display", True):
        cards.append(make_card(
            summary="CareGuard blocked candidate display pending review",
            detail="; ".join(critic.get("blocked_reasons", [])),
            indicator="info",
            evidence_url=review_url,
        ))

    if not cards:
        cards.append(make_card(
            summary="CareGuard: no blocking findings",
            detail="No missing critical evidence or high-severity medication cautions detected. "
                   "Draft only — clinician review required.",
            indicator="info",
            evidence_url=review_url,
        ))
    return cards
