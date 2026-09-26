"""Idempotent schema creation for the durable CareGuard tables.

Run at startup (best-effort) and via scripts. Uses JSONB + indexes for fast,
durable case/audit/feedback queries. Never drops or alters existing tables.
"""

from __future__ import annotations

from python.hearttwin.careguard.db import pool

_DDL = """
CREATE TABLE IF NOT EXISTS careguard_cases (
    case_id           text PRIMARY KEY,
    source_bundle_id  text,
    fixture_id        text,
    clinical_question text,
    facts             jsonb,
    deidentified      boolean DEFAULT true,
    created_at        timestamptz DEFAULT now(),
    updated_at        timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS careguard_audit (
    event_id   text PRIMARY KEY,
    case_id    text,
    run_id     text,
    stage_id   text,
    actor      text,
    action     text,
    detail     jsonb,
    created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS careguard_audit_case_idx
    ON careguard_audit (case_id, created_at);

CREATE TABLE IF NOT EXISTS careguard_feedback (
    feedback_id   text PRIMARY KEY,
    case_id       text,
    decision      text,
    candidate_id  text,
    reason        text,
    reviewer_role text,
    created_at    timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS careguard_feedback_case_idx
    ON careguard_feedback (case_id, created_at);
"""


async def migrate() -> dict:
    p = await pool.get_pool()
    if p is None:
        return {"migrated": False, "reason": "Postgres not configured"}
    async with p.connection() as conn:
        await conn.execute(_DDL)
    return {"migrated": True, "tables": ["careguard_cases", "careguard_audit", "careguard_feedback"]}
