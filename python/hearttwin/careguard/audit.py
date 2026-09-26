"""CareGuard audit trail — append-only, redacted, namespaced.

Every stage, safety decision, and clinician action writes an audit event. Events
are redacted before persistence (no PHI, no secrets, no raw model IO) and stored
under ``careguard:case:{case_id}:audit``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from python.hearttwin.careguard.memory import keys, redis_store
from python.hearttwin.careguard.schemas import AuditEvent
from python.hearttwin.careguard.security import redact_structured, redact_text


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def record(
    *,
    case_id: str,
    actor: str,
    action: str,
    run_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    detail: Optional[dict[str, Any]] = None,
) -> str:
    """Append one redacted audit event; return its id."""
    event = AuditEvent(
        event_id=f"aud-{uuid.uuid4().hex[:12]}",
        case_id=case_id,
        run_id=run_id,
        stage_id=stage_id,
        actor=actor,
        action=redact_text(action),
        detail=redact_structured(detail or {}),
        created_at=_now(),
    )
    payload = event.model_dump()
    await redis_store.append_json(keys.case_audit(case_id), payload)
    # Durable mirror to Postgres (best-effort; never breaks the request).
    try:
        from python.hearttwin.careguard.db.repository import get_repository

        await get_repository().append_audit_event(payload)
    except Exception:  # noqa: BLE001 — durability is additive, not required
        pass
    return event.event_id


async def get_trail(case_id: str) -> list[dict]:
    """Prefer the durable Postgres trail (survives Redis TTL); fall back to Redis."""
    try:
        from python.hearttwin.careguard.db.repository import get_repository

        durable = await get_repository().get_audit_trail(case_id)
        if durable:
            return durable
    except Exception:  # noqa: BLE001
        pass
    return await redis_store.get_list(keys.case_audit(case_id))
