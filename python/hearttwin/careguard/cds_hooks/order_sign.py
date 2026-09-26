"""order-sign hook → advisory cards for a drafted medication order.

Returns warning/info cards only. Never returns a create action, never blocks or
places the order. The clinician remains the decision-maker.
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.cds_hooks.cards import make_card
from python.hearttwin.careguard.medications import contraindication_engine, rxnorm_client
from python.hearttwin.careguard.memory import keys, redis_store
from python.hearttwin.careguard.risk.signals import extract_signals
from python.hearttwin.careguard.schemas import PatientContext


async def build_cards(case_id: str, draft_medications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    context_dict = await redis_store.get_json(keys.case_context(case_id)) or {"case_id": case_id}
    pc = PatientContext.model_validate(context_dict) if context_dict.get("case_id") else PatientContext(case_id=case_id)
    signals = extract_signals(pc)
    ctx = {
        "reduced_egfr": signals["reduced_egfr"],
        "missing_potassium": signals["missing_potassium"],
        "pregnancy_recorded": signals["pregnancy_recorded"],
        "allergen_terms": signals["allergen_terms"],
    }

    cards: list[dict[str, Any]] = []
    for med in draft_medications:
        name = med.get("name") or med.get("display") or ""
        norm = rxnorm_client.normalize(name=name, coded_rxcui=med.get("rxcui"))
        conflicts = contraindication_engine.evaluate(med=norm, context=ctx, fact_ids=[])
        for cf in conflicts:
            if cf.severity in ("high", "blocked"):
                cards.append(make_card(
                    summary=f"Order caution: {cf.medication_name}",
                    detail=cf.statement,
                    indicator="warning",
                    override_reasons=["Reviewed; monitoring arranged", "Benefit outweighs risk per clinician"],
                ))
            elif cf.conflict_type == "label_unavailable":
                cards.append(make_card(
                    summary=f"No official label evidence for {cf.medication_name}",
                    detail="CareGuard could not verify an official drug label for this medication; "
                           "no automated contraindication check was possible.",
                    indicator="info",
                ))
    if not cards:
        cards.append(make_card(
            summary="CareGuard: no label-based caution for this order",
            detail="No high-severity contraindication was found in official labeling for the recorded factors. "
                   "Draft only — clinician review required.",
            indicator="info",
        ))
    return cards
