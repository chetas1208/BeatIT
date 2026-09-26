"""Reconcile morbidities from FHIR Conditions (recorded) + report mentions.

Recorded FHIR conditions are recorded_active / recorded_historical. Report
mentions keep their negation/temporality/experiencer status and, when
patient-experiencer and non-negated, are surfaced for clinician confirmation —
never treated as confirmed diagnoses.
"""

from __future__ import annotations

from typing import Any

from python.hearttwin.careguard.medications.schemas import ConditionMention
from python.hearttwin.careguard.reports import condition_mention_extractor
from python.hearttwin.careguard.schemas import PatientContext


def reconcile(
    pc: PatientContext,
    *,
    report_texts: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    confirmed: list[dict] = []
    historical: list[dict] = []

    for f in pc.active_cardiac_problem + pc.active_non_cardiac_conditions:
        confirmed.append({"display": f.display, "code": f.code, "code_system": f.code_system,
                          "fact_id": f.fact_id, "status": "recorded_active",
                          "json_pointer": f.json_pointer})
    for f in pc.historical_cardiac_problems:
        historical.append({"display": f.display, "code": f.code, "fact_id": f.fact_id,
                          "status": "recorded_historical", "json_pointer": f.json_pointer})

    mentions: list[ConditionMention] = []
    for doc in (report_texts or []):
        mentions.extend(condition_mention_extractor.extract(
            doc.get("text", ""), document_id=doc.get("document_id", "report"),
            section=doc.get("section"),
        ))

    # A report mention that matches an already-recorded condition is redundant.
    recorded_displays = {str(c["display"]).lower() for c in confirmed + historical if c.get("display")}
    novel_mentions = [m for m in mentions if (m.normalized_display or "").lower() not in recorded_displays]
    needs_confirmation = condition_mention_extractor.requiring_confirmation(novel_mentions)

    return {
        "confirmed_conditions": confirmed,
        "historical_conditions": historical,
        "all_report_mentions": [m.model_dump() for m in mentions],
        "report_mentions_requiring_confirmation": [m.model_dump() for m in needs_confirmation],
    }
