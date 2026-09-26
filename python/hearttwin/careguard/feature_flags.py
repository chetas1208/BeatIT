"""CareGuard feature-flag gate — the single source of truth for isolation.

When CareGuard is disabled, the router is never mounted, no Anthropic client is
built, and no ``careguard:*`` Redis keys are created. This module reuses
DualBeat's existing ``env_bool`` parser so boolean semantics match the rest of
the app exactly.
"""

from __future__ import annotations

import os

from python.hearttwin.tools.env_config import env_bool

# Env var names (kept as constants so tests and docs reference one place).
ENV_CAREGUARD_ENABLED = "CAREGUARD_ENABLED"
ENV_PUBLIC_CAREGUARD_ENABLED = "NEXT_PUBLIC_CAREGUARD_ENABLED"
ENV_REDIS_ENABLED = "CAREGUARD_REDIS_ENABLED"
ENV_VISTA_ENABLED = "CAREGUARD_VISTA_ENABLED"
ENV_ALLOW_EXTERNAL_RESEARCH = "CAREGUARD_ALLOW_EXTERNAL_RESEARCH"
ENV_REQUIRE_DEID = "CAREGUARD_REQUIRE_DEIDENTIFICATION"
ENV_ALLOW_IDENTIFIABLE = "CAREGUARD_ALLOW_IDENTIFIABLE_DATA"


def careguard_enabled() -> bool:
    """Master backend switch. Default False — off means baseline DualBeat."""
    return env_bool(ENV_CAREGUARD_ENABLED, False)


def public_careguard_enabled() -> bool:
    """Frontend-facing switch (mirrors NEXT_PUBLIC_CAREGUARD_ENABLED)."""
    return env_bool(ENV_PUBLIC_CAREGUARD_ENABLED, False)


def redis_enabled() -> bool:
    """CareGuard may use Redis only when both this flag and a REDIS_URL exist.

    The URL check lives in the memory layer; this is the policy switch.
    """
    return env_bool(ENV_REDIS_ENABLED, True)


def vista_enabled() -> bool:
    return env_bool(ENV_VISTA_ENABLED, False)


def external_research_allowed() -> bool:
    """When False (default), guideline retrieval is local-corpus only and the
    evidence agent abstains rather than reaching the network."""
    return env_bool(ENV_ALLOW_EXTERNAL_RESEARCH, False)


def require_deidentification() -> bool:
    return env_bool(ENV_REQUIRE_DEID, True)


def allow_identifiable_data() -> bool:
    return env_bool(ENV_ALLOW_IDENTIFIABLE, False)


def log_raw_model_inputs() -> bool:
    return env_bool("CAREGUARD_LOG_RAW_MODEL_INPUTS", False)


def log_raw_model_outputs() -> bool:
    return env_bool("CAREGUARD_LOG_RAW_MODEL_OUTPUTS", False)


def redis_prefix() -> str:
    return os.environ.get("CAREGUARD_REDIS_PREFIX", "careguard").strip() or "careguard"
