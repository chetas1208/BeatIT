"""CareGuard memory layer: namespaced Redis state, cache, and audit stream.

Reuses DualBeat's ``redis_client`` (standard ``REDIS_URL``). All keys are
namespaced under ``careguard:`` so existing DualBeat keys are never touched.
When Redis is unavailable, a bounded in-process fallback serves the active
request only and every surface discloses "not persisted".
"""

from __future__ import annotations

__all__ = ["keys", "redis_store"]
