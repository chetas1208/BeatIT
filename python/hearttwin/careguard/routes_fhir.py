"""FHIR import + case retrieval routes (attached to the CareGuard router).

POST /api/v1/careguard/fhir/import   → validate + parse a Bundle, persist facts
GET  /api/v1/careguard/cases/{id}    → case record (deidentified facts only)

The raw Bundle is NEVER persisted or logged. Only deidentified, structured facts
and the validation summary are stored.
"""

from __future__ import annotations

import json
import pathlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from python.hearttwin.careguard import audit
from python.hearttwin.careguard.constants import DEID_NOTICE, DISCLAIMER
from python.hearttwin.careguard.errors import FhirValidationError, RunNotFoundError
from python.hearttwin.careguard.fhir import normalizer, parser
from python.hearttwin.careguard.memory import keys, redis_store
from python.hearttwin.careguard.schemas import CareGuardCase, FhirImportRequest
from python.hearttwin.careguard.security import deidentify_for_model

_FIXTURE_DIR = pathlib.Path(__file__).resolve().parents[3] / "fixtures" / "careguard"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_fixture(fixture_id: str) -> dict:
    # Guard against path traversal — only a bare stem is allowed.
    safe = pathlib.Path(fixture_id).name
    if not safe.endswith(".json"):
        safe = f"{safe}.json"
    path = _FIXTURE_DIR / safe
    if not path.exists() or path.parent != _FIXTURE_DIR:
        raise FhirValidationError(f"Unknown fixture {fixture_id!r}", issues=["fixture_not_found"])
    return json.loads(path.read_text())


def attach(router: APIRouter) -> None:
    @router.post("/fhir/import")
    async def fhir_import(request: FhirImportRequest) -> dict:
        if request.bundle is None and not request.fixture_id:
            raise FhirValidationError("Provide a FHIR 'bundle' or a 'fixture_id'", issues=["no_input"])
        bundle = request.bundle if request.bundle is not None else _load_fixture(request.fixture_id)

        parsed = parser.parse_bundle(bundle)
        case_id = f"cg-{uuid.uuid4().hex[:12]}"
        patient_context = normalizer.build_patient_context(case_id, parsed)

        # Deidentify defensively before persistence (facts are structured, but we
        # never trust that upstream). Raw bundle is intentionally discarded here.
        stored_facts = deidentify_for_model([f.model_dump() for f in parsed.facts])

        case = CareGuardCase(
            case_id=case_id,
            source_bundle_id=parsed.bundle_id,
            fixture_id=request.fixture_id,
            deidentified=True,
            created_at=_now(),
            clinical_question=request.clinical_question,
            facts=parsed.facts,
            unsupported_resources=parsed.unsupported_resources,
        )
        await redis_store.set_json(keys.case_record(case_id), case.model_dump())
        # Durable case record in Postgres (best-effort; additive to Redis).
        try:
            from python.hearttwin.careguard.db.repository import get_repository

            await get_repository().save_case(case.model_dump())
        except Exception:  # noqa: BLE001
            pass
        await redis_store.set_json(
            keys.case_fhir(case_id),
            {
                "facts": stored_facts,
                "validation": parsed.validation.model_dump(),
                "missing_critical_evidence": parsed.missing_critical_evidence,
            },
        )
        await redis_store.set_json(keys.case_context(case_id), patient_context.model_dump())
        await audit.record(
            case_id=case_id,
            actor="careguard_fhir_import",
            action="imported FHIR bundle",
            detail={
                "bundle_id": parsed.bundle_id,
                "fact_count": len(parsed.facts),
                "unsupported": len(parsed.unsupported_resources),
                "fixture_id": request.fixture_id,
            },
        )

        return {
            "case_id": case_id,
            "deidentified": True,
            "deidentification_notice": DEID_NOTICE,
            "validation": parsed.validation.model_dump(),
            "fact_count": len(parsed.facts),
            "supported_resources": parsed.validation.supported,
            "unsupported_resources": parsed.unsupported_resources,
            "missing_critical_evidence": parsed.missing_critical_evidence,
            "resource_counts": parsed.validation.resource_counts,
            "persisted": redis_store.redis_configured(),
            "persistence_note": redis_store.persistence_note(),
            "safety_disclaimer": DISCLAIMER,
        }

    @router.get("/cases/{case_id}")
    async def get_case(case_id: str) -> dict:
        record = await redis_store.get_json(keys.case_record(case_id))
        if not record:
            raise RunNotFoundError(f"No CareGuard case {case_id!r}")
        fhir = await redis_store.get_json(keys.case_fhir(case_id)) or {}
        context = await redis_store.get_json(keys.case_context(case_id))
        return {
            "case": record,
            "fhir": fhir,
            "patient_context": context,
            "safety_disclaimer": DISCLAIMER,
        }
