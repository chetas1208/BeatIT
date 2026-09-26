"""CDS Hooks discovery document."""

from __future__ import annotations


def services() -> dict:
    return {
        "services": [
            {
                "hook": "patient-view",
                "title": "CareGuard cardiac evidence review",
                "description": "Surfaces evidence-linked cardiac care considerations, missing evidence, and "
                               "cross-organ cautions for clinician review. Draft only — clinician review required.",
                "id": "careguard-patient-view",
                "prefetch": {"patient": "Patient/{{context.patientId}}"},
            },
            {
                "hook": "order-select",
                "title": "CareGuard medication conflict + alternatives",
                "description": "On selecting a proposed medication, surfaces cross-condition conflicts and "
                               "evidence-linked candidate alternatives. Advisory only; never modifies the order.",
                "id": "careguard-order-select",
            },
            {
                "hook": "order-sign",
                "title": "CareGuard medication safety check",
                "description": "Checks a medication order against official-label contraindications and recorded "
                               "renal/allergy factors. Returns advisory cards only; never places or blocks an order.",
                "id": "careguard-order-sign",
            },
        ]
    }
