"""Provider-neutral model-key pool with health-aware failover.

Per GLOBAL_ARCHITECTURE.md's "MODEL ROUTER" section: the pool of configured
model API keys is a **reliability pool**, not a set of distinct personalities.
This module answers exactly one question — "which key should the caller use
right now, and how do I record whether it worked" — and nothing else. Making
the actual OpenAI-compatible chat-completion call is a later wave's job (a
model-router component that asks this pool for a `KeyHandle` first).

Naming is deliberately vendor-neutral (``ModelKeyPool``, ``MODEL_API_KEY_n``)
even though the only backing provider confirmed so far is NVIDIA Build's
OpenAI-compatible endpoint (see docs/assistant/NVIDIA_MODEL_RESEARCH.md) —
the campaign's domain-facing surface must not hardcode a vendor identity in
case the backing provider changes.

Security invariant: no function in this module ever returns, logs, or
formats a raw key value. ``get_pool_health()`` and every exception path use
only the 1-based env-var slot index as an identifier.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Env var convention — extends the existing MODEL_API_KEY / MODEL_BASE_URL
# single-key convention (see .env.example) rather than inventing a parallel
# vendor-specific one. Up to 3 slots; any subset may be configured.
# ---------------------------------------------------------------------------

_MAX_SLOTS = 3
_KEY_ENV_TEMPLATE = "MODEL_API_KEY_{n}"
_POOL_BASE_URL_ENV = "MODEL_POOL_BASE_URL"
_DEFAULT_POOL_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Quarantine/backoff defaults. Rate-limit numbers in the research doc are
# explicitly flagged as unverified third-party figures, so nothing here is a
# hardcoded RPM assumption — only a generic circuit-breaker shape.
DEFAULT_INITIAL_BACKOFF_SECONDS = 2.0
DEFAULT_MAX_BACKOFF_SECONDS = 300.0
DEFAULT_FAILURE_THRESHOLD = 3

Clock = Callable[[], float]


class ModelRole(str, Enum):
    FAST = "fast"
    DEEP = "deep"
    SAFETY = "safety"


# Provisional model-ID defaults from docs/assistant/NVIDIA_MODEL_RESEARCH.md's
# shortlist. NOT benchmarked and NOT locked — Wave 6 owns empirical selection.
# Env override lets a later wave swap candidates without touching code.
_ROLE_ENV_NAMES: dict[ModelRole, str] = {
    ModelRole.FAST: "FAST_MODEL_ID",
    ModelRole.DEEP: "DEEP_MODEL_ID",
    ModelRole.SAFETY: "SAFETY_MODEL_ID",
}
_ROLE_DEFAULTS: dict[ModelRole, str] = {
    ModelRole.FAST: "nvidia/nemotron-3.5-lightning-30b-a3b",
    ModelRole.DEEP: "nvidia/nemotron-3-super-120b-a12b",
    ModelRole.SAFETY: "nvidia/nemotron-3.5-content-safety",
}


def get_model_id(role: ModelRole) -> str:
    """Return the configured model ID for a role, env-overridable.

    Provisional defaults only — see module docstring and
    docs/assistant/wave2/nvidia-key-pool.md. Wave 6 benchmarks before any of
    this is treated as locked.
    """

    return os.environ.get(_ROLE_ENV_NAMES[role], _ROLE_DEFAULTS[role])


@dataclass(frozen=True)
class KeyHandle:
    """Opaque handle a caller uses to make one request and then report back.

    ``slot`` is the only thing safe to log or display (matches the env-var
    suffix, e.g. slot=2 for MODEL_API_KEY_2). ``api_key`` is excluded from the
    generated repr so an accidental print/log of a handle cannot leak it.
    """

    slot: int
    api_key: str = field(repr=False)
    base_url: str


@dataclass
class _KeySlot:
    slot: int
    api_key: str
    base_url: str
    quarantined_until: float = 0.0
    consecutive_failures: int = 0
    quarantine_count: int = 0


class ModelKeyPool:
    """Round-robin pool of configured model keys with quarantine on failure.

    Construction reads env vars once (no module-level singleton — callers own
    their own instance so tests never fight over global state). A fresh
    ``ModelKeyPool()`` with zero configured keys is a valid, expected steady
    state (matches the FALLBACK TREE: "All NVIDIA unavailable → canonical
    BeatIT tools still work") — every method degrades gracefully rather than
    raising.
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        initial_backoff_seconds: float = DEFAULT_INITIAL_BACKOFF_SECONDS,
        max_backoff_seconds: float = DEFAULT_MAX_BACKOFF_SECONDS,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        clock: Clock = time.monotonic,
    ) -> None:
        self._initial_backoff = initial_backoff_seconds
        self._max_backoff = max_backoff_seconds
        self._failure_threshold = failure_threshold
        self._clock = clock
        resolved_base_url = base_url or os.environ.get(
            _POOL_BASE_URL_ENV, _DEFAULT_POOL_BASE_URL
        )

        self._slots: list[_KeySlot] = []
        for n in range(1, _MAX_SLOTS + 1):
            raw = os.environ.get(_KEY_ENV_TEMPLATE.format(n=n), "").strip()
            if raw:
                self._slots.append(
                    _KeySlot(slot=n, api_key=raw, base_url=resolved_base_url)
                )
        self._rr_cursor = 0

    # -- selection -----------------------------------------------------

    def get_healthy_key(self) -> Optional[KeyHandle]:
        """Return the next healthy key round-robin, or None if none is usable.

        Callers must treat ``None`` as "no generative model available right
        now" and fall back to deterministic tools only — never raise or
        retry-loop here.
        """

        n = len(self._slots)
        if n == 0:
            return None
        now = self._clock()
        for offset in range(n):
            idx = (self._rr_cursor + offset) % n
            candidate = self._slots[idx]
            if candidate.quarantined_until <= now:
                self._rr_cursor = (idx + 1) % n
                return KeyHandle(
                    slot=candidate.slot,
                    api_key=candidate.api_key,
                    base_url=candidate.base_url,
                )
        return None

    # -- state machine ---------------------------------------------------

    def _find_slot(self, key_handle: KeyHandle) -> Optional[_KeySlot]:
        for candidate in self._slots:
            if candidate.slot == key_handle.slot:
                return candidate
        return None

    def report_success(self, key_handle: KeyHandle) -> None:
        """Clear failure/quarantine state for a key after a real success."""

        slot = self._find_slot(key_handle)
        if slot is None:
            return
        slot.consecutive_failures = 0
        slot.quarantine_count = 0
        slot.quarantined_until = 0.0

    def report_failure(
        self, key_handle: KeyHandle, status_code: Optional[int] = None
    ) -> None:
        """Record a failed call and quarantine the key if warranted.

        A 429 (rate limit) is an unambiguous signal and quarantines
        immediately. Any other failure only quarantines after
        ``failure_threshold`` consecutive misses, so a single transient
        network blip doesn't pull a key out of rotation. Each time a key is
        re-quarantined, the backoff duration doubles (capped) — a key that
        keeps failing right after being retried backs off further.
        """

        slot = self._find_slot(key_handle)
        if slot is None:
            return
        slot.consecutive_failures += 1
        is_rate_limited = status_code == 429
        if is_rate_limited or slot.consecutive_failures >= self._failure_threshold:
            duration = min(
                self._max_backoff,
                self._initial_backoff * (2**slot.quarantine_count),
            )
            slot.quarantined_until = self._clock() + duration
            slot.quarantine_count += 1
            slot.consecutive_failures = 0

    # -- observability -----------------------------------------------------

    def get_pool_health(self) -> dict:
        """Non-secret pool status: counts and per-slot quarantine state only.

        Never include a key value or anything derived from one — only the
        env-var slot index, booleans, counts, and a monotonic-clock timestamp.
        """

        now = self._clock()
        keys = []
        healthy_count = 0
        for slot in self._slots:
            quarantined = slot.quarantined_until > now
            if not quarantined:
                healthy_count += 1
            keys.append(
                {
                    "slot": slot.slot,
                    "quarantined": quarantined,
                    "quarantined_until": slot.quarantined_until if quarantined else None,
                    "consecutive_failures": slot.consecutive_failures,
                    "quarantine_count": slot.quarantine_count,
                }
            )
        return {
            "configured_count": len(self._slots),
            "healthy_count": healthy_count,
            "keys": keys,
        }
