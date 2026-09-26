"""Optional durable Postgres layer for CareGuard (Neon-friendly).

Additive system-of-record for case metadata, the audit trail, and clinician
feedback. Redis stays the hot cache + staged-workflow store; Postgres provides
durability (survives Redis TTL / restarts) and indexed audit queries.

Performance: a single warm async connection pool is reused across requests, so
the TLS handshake to Neon is paid once, not per request. When DATABASE_URL is
unset (or the driver is absent), everything degrades to the existing Redis /
in-memory behavior — no code path requires Postgres.
"""

from __future__ import annotations

__all__ = ["pool", "repository", "migrate"]
