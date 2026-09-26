"""CareGuardRepository — the durable persistence interface (spec §14).

A Postgres implementation backs it when DATABASE_URL is set; otherwise a Null
implementation no-ops so callers never depend on Postgres. Writes store only
deidentified, redacted structured data (never raw bundles/notes/PHI/secrets).
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from python.hearttwin.careguard.db import pool
from python.hearttwin.careguard.security import redact_structured


class CareGuardRepository(Protocol):
    async def save_case(self, case: dict[str, Any]) -> bool: ...
    async def get_case(self, case_id: str) -> dict[str, Any] | None: ...
    async def append_audit_event(self, event: dict[str, Any]) -> bool: ...
    async def get_audit_trail(self, case_id: str) -> list[dict[str, Any]]: ...
    async def save_feedback(self, case_id: str, feedback: dict[str, Any]) -> bool: ...


class NullRepository:
    """Used when Postgres is unconfigured — every call is a safe no-op."""

    async def save_case(self, case: dict[str, Any]) -> bool:
        return False

    async def get_case(self, case_id: str) -> dict[str, Any] | None:
        return None

    async def append_audit_event(self, event: dict[str, Any]) -> bool:
        return False

    async def get_audit_trail(self, case_id: str) -> list[dict[str, Any]]:
        return []

    async def save_feedback(self, case_id: str, feedback: dict[str, Any]) -> bool:
        return False


class PostgresRepository:
    async def save_case(self, case: dict[str, Any]) -> bool:
        p = await pool.get_pool()
        if p is None:
            return False
        async with p.connection() as conn:
            await conn.execute(
                """
                INSERT INTO careguard_cases
                    (case_id, source_bundle_id, fixture_id, clinical_question, facts, deidentified, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (case_id) DO UPDATE SET
                    source_bundle_id = EXCLUDED.source_bundle_id,
                    clinical_question = EXCLUDED.clinical_question,
                    facts = EXCLUDED.facts,
                    updated_at = now()
                """,
                (
                    case.get("case_id"), case.get("source_bundle_id"), case.get("fixture_id"),
                    case.get("clinical_question"),
                    json.dumps(redact_structured(case.get("facts", [])), default=str),
                    bool(case.get("deidentified", True)),
                ),
            )
        return True

    async def get_case(self, case_id: str) -> dict[str, Any] | None:
        p = await pool.get_pool()
        if p is None:
            return None
        async with p.connection() as conn:
            cur = await conn.execute(
                "SELECT case_id, source_bundle_id, fixture_id, clinical_question, facts, deidentified, "
                "created_at, updated_at FROM careguard_cases WHERE case_id = %s",
                (case_id,),
            )
            row = await cur.fetchone()
        if not row:
            return None
        return {
            "case_id": row[0], "source_bundle_id": row[1], "fixture_id": row[2],
            "clinical_question": row[3], "facts": row[4], "deidentified": row[5],
            "created_at": str(row[6]), "updated_at": str(row[7]),
        }

    async def append_audit_event(self, event: dict[str, Any]) -> bool:
        p = await pool.get_pool()
        if p is None:
            return False
        async with p.connection() as conn:
            await conn.execute(
                """
                INSERT INTO careguard_audit (event_id, case_id, run_id, stage_id, actor, action, detail)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                """,
                (
                    event.get("event_id"), event.get("case_id"), event.get("run_id"),
                    event.get("stage_id"), event.get("actor"), event.get("action"),
                    json.dumps(redact_structured(event.get("detail", {})), default=str),
                ),
            )
        return True

    async def get_audit_trail(self, case_id: str) -> list[dict[str, Any]]:
        p = await pool.get_pool()
        if p is None:
            return []
        async with p.connection() as conn:
            cur = await conn.execute(
                "SELECT event_id, case_id, run_id, stage_id, actor, action, detail, created_at "
                "FROM careguard_audit WHERE case_id = %s ORDER BY created_at ASC",
                (case_id,),
            )
            rows = await cur.fetchall()
        return [
            {"event_id": r[0], "case_id": r[1], "run_id": r[2], "stage_id": r[3],
             "actor": r[4], "action": r[5], "detail": r[6], "created_at": str(r[7])}
            for r in rows
        ]

    async def save_feedback(self, case_id: str, feedback: dict[str, Any]) -> bool:
        p = await pool.get_pool()
        if p is None:
            return False
        async with p.connection() as conn:
            await conn.execute(
                """
                INSERT INTO careguard_feedback
                    (feedback_id, case_id, decision, candidate_id, reason, reviewer_role)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (feedback_id) DO NOTHING
                """,
                (
                    feedback.get("feedback_id"), case_id, feedback.get("decision"),
                    feedback.get("candidate_id"), feedback.get("reason"),
                    feedback.get("reviewer_role", "clinician"),
                ),
            )
        return True


_REPO: CareGuardRepository | None = None


def get_repository() -> CareGuardRepository:
    global _REPO
    if _REPO is not None:
        return _REPO
    _REPO = PostgresRepository() if pool.is_configured() else NullRepository()
    return _REPO


def reset_repository() -> None:
    global _REPO
    _REPO = None
