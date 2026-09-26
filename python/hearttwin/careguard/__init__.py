"""DualBeat CareGuard — multimorbidity-aware cardiac care-plan review module.

Additive, feature-flagged extension of DualBeat. CareGuard never mutates
existing DualBeat behavior: it lives in its own namespace, mounts only when
``CAREGUARD_ENABLED=true``, uses Anthropic (alongside — never replacing —
DualBeat's providers), and reuses DualBeat's deterministic simulation through a
read-only adapter.

Nothing in this package is imported by DualBeat's core paths. The single seam is
a guarded ``include_router`` in ``python/hearttwin/api.py``.

Educational clinical-decision-support draft only. Clinician review required.
Not a medical device. No diagnosis, no dosing, no autonomous prescribing.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
