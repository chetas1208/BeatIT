"""CareGuard configuration + environment validation.

``validate_env`` checks required variables, boolean parsing, timeout ranges,
model values, API-base URL shape, feature-flag behavior, and secret hygiene.
``public_config`` returns ONLY safe metadata (booleans + non-secret model ids) —
never a secret value.
"""

from __future__ import annotations

import os
from typing import Any

from python.hearttwin.careguard import feature_flags as flags
from python.hearttwin.tools.env_config import env_bool

# --- Anthropic model routing (defaults mirror .env.example) -----------------
_MODEL_DEFAULTS = {
    "fast": ("CAREGUARD_MODEL_FAST", "claude-haiku-4-5-20251001"),
    "extraction": ("CAREGUARD_MODEL_EXTRACTION", "claude-sonnet-5"),
    "fhir": ("CAREGUARD_MODEL_FHIR", "claude-sonnet-5"),
    "multimorbidity": ("CAREGUARD_MODEL_MULTIMORBIDITY", "claude-sonnet-5"),
    "guidelines": ("CAREGUARD_MODEL_GUIDELINES", "claude-sonnet-5"),
    "medication_safety": ("CAREGUARD_MODEL_MEDICATION_SAFETY", "claude-fable-5"),
    "plan_composer": ("CAREGUARD_MODEL_PLAN_COMPOSER", "claude-fable-5"),
    "clinical_critic": ("CAREGUARD_MODEL_CLINICAL_CRITIC", "claude-fable-5"),
    "fallback": ("CAREGUARD_MODEL_FALLBACK", "claude-sonnet-5"),
}

# Models that must never receive identifiable data (spec §7 retention boundary).
DEIDENTIFY_ONLY_MODELS = {"claude-fable-5"}

_KNOWN_MODEL_PREFIXES = ("claude-haiku", "claude-sonnet", "claude-opus", "claude-fable")


def model_for(role: str) -> str:
    env_name, default = _MODEL_DEFAULTS.get(role, ("", "claude-sonnet-5"))
    return os.environ.get(env_name, default).strip() if env_name else default


def all_models() -> dict[str, str]:
    return {role: model_for(role) for role in _MODEL_DEFAULTS}


def anthropic_api_keys() -> list[str]:
    """Ordered, de-duplicated list of non-empty Anthropic keys.

    Primary is ANTHROPIC_API_KEY; fallbacks are ANTHROPIC_API_KEY_FALLBACK and
    ANTHROPIC_API_KEY_2. If the primary key fails (auth/rate/connection), the
    client transparently retries the next key.
    """
    raw = [
        os.environ.get("ANTHROPIC_API_KEY", ""),
        os.environ.get("ANTHROPIC_API_KEY_FALLBACK", ""),
        os.environ.get("ANTHROPIC_API_KEY_2", ""),
    ]
    seen: set[str] = set()
    keys: list[str] = []
    for k in raw:
        k = k.strip()
        if k and k not in seen:
            seen.add(k)
            keys.append(k)
    return keys


def anthropic_configured() -> bool:
    return bool(anthropic_api_keys())


def anthropic_key_count() -> int:
    return len(anthropic_api_keys())


def anthropic_timeout_seconds() -> int:
    return _int_env("CAREGUARD_ANTHROPIC_TIMEOUT_SECONDS", 75, lo=5, hi=300)


def anthropic_max_retries() -> int:
    return _int_env("CAREGUARD_ANTHROPIC_MAX_RETRIES", 2, lo=0, hi=5)


def anthropic_effort() -> str:
    val = os.environ.get("CAREGUARD_ANTHROPIC_EFFORT", "high").strip().lower()
    return val if val in {"low", "medium", "high"} else "high"


def redis_ttl_seconds() -> int:
    return _int_env("CAREGUARD_REDIS_TTL_SECONDS", 86400, lo=60, hi=7 * 86400)


def guideline_manifest_path() -> str:
    return os.environ.get(
        "CAREGUARD_GUIDELINE_MANIFEST_PATH", "docs/careguard/research-manifest.yaml"
    ).strip()


def local_research_root() -> str:
    return os.environ.get("CAREGUARD_LOCAL_RESEARCH_ROOT", "").strip()


def require_source_version() -> bool:
    return env_bool("CAREGUARD_REQUIRE_SOURCE_VERSION", True)


def max_source_age_days() -> int:
    return _int_env("CAREGUARD_MAX_SOURCE_AGE_DAYS", 730, lo=1, hi=3650)


def medication_api_bases() -> dict[str, str]:
    return {
        "rxnorm": os.environ.get("RXNORM_API_BASE", "https://rxnav.nlm.nih.gov/REST").strip(),
        "openfda": os.environ.get("OPENFDA_API_BASE", "https://api.fda.gov").strip(),
        "dailymed": os.environ.get(
            "DAILYMED_API_BASE", "https://dailymed.nlm.nih.gov/dailymed/services/v2"
        ).strip(),
    }


def _int_env(name: str, default: int, *, lo: int, hi: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        val = int(raw)
    except ValueError:
        return default
    return max(lo, min(hi, val))


def _looks_like_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


# ---------------------------------------------------------------------------
# Public, secret-free config view (served by GET /api/v1/careguard/config).
# ---------------------------------------------------------------------------
def public_config() -> dict[str, Any]:
    from python.hearttwin.careguard.memory import redis_store

    return {
        "module": "DualBeat CareGuard",
        "version": "0.1.0",
        "feature_flags": {
            "careguard_enabled": flags.careguard_enabled(),
            "public_careguard_enabled": flags.public_careguard_enabled(),
            "redis_enabled": flags.redis_enabled(),
            "vista_enabled": flags.vista_enabled(),
            "external_research_allowed": flags.external_research_allowed(),
            "require_deidentification": flags.require_deidentification(),
            "allow_identifiable_data": flags.allow_identifiable_data(),
        },
        "anthropic": {
            "configured": anthropic_configured(),  # bool only — never the key
            "keys_configured": anthropic_key_count(),  # count only, for failover visibility
            "models": all_models(),
            "timeout_seconds": anthropic_timeout_seconds(),
            "max_retries": anthropic_max_retries(),
            "effort": anthropic_effort(),
            "deidentify_only_models": sorted(DEIDENTIFY_ONLY_MODELS),
        },
        "research": {
            "manifest_path": guideline_manifest_path(),
            "manifest_present": os.path.exists(guideline_manifest_path()),
            "external_retrieval_enabled": flags.external_research_allowed(),
            "require_source_version": require_source_version(),
            "max_source_age_days": max_source_age_days(),
            "local_research_root_configured": bool(local_research_root()),
        },
        "medication_apis": {
            name: {"configured": bool(base), "external_calls_default_off": True}
            for name, base in medication_api_bases().items()
        },
        "openfda_key_configured": bool(os.environ.get("OPENFDA_API_KEY", "").strip()),
        "redis": {
            "enabled": flags.redis_enabled(),
            "configured": redis_store.redis_configured(),
            "prefix": flags.redis_prefix(),
            "ttl_seconds": redis_ttl_seconds(),
        },
        "vista": _vista_status(),
        "database": {
            "configured": _db_configured(),  # bool only — never the DSN
            "kind": "postgres" if _db_configured() else "none",
            "pooled": True,
            "durable_case_and_audit": _db_configured(),
        },
    }


def _db_configured() -> bool:
    from python.hearttwin.careguard.db import pool as _dbpool

    return _dbpool.is_configured()


def _vista_status() -> dict[str, Any]:
    origin = (os.environ.get("CAREGUARD_VISTA_API_BASE", "")
              or os.environ.get("VISTA3D_API_BASE", "")).strip()
    secret = (os.environ.get("CAREGUARD_VISTA_ENDPOINT_SECRET", "")
              or os.environ.get("VISTA3D_ENDPOINT_SECRET", "")).strip()
    return {
        "enabled": flags.vista_enabled(),
        "origin_configured": bool(origin),
        "secret_configured": bool(secret),  # bool only — never the secret
        "ready": flags.vista_enabled() and bool(origin) and bool(secret),
        "external_service": True,
    }


def validate_env() -> dict[str, Any]:
    """Structured validation report — errors/warnings, never secret values."""
    errors: list[str] = []
    warnings: list[str] = []

    # Boolean flags parse cleanly (env_bool never raises, but flag odd values).
    for name in (
        flags.ENV_CAREGUARD_ENABLED, flags.ENV_PUBLIC_CAREGUARD_ENABLED,
        flags.ENV_REDIS_ENABLED, flags.ENV_VISTA_ENABLED,
        flags.ENV_ALLOW_EXTERNAL_RESEARCH, flags.ENV_REQUIRE_DEID,
        flags.ENV_ALLOW_IDENTIFIABLE,
    ):
        raw = os.environ.get(name, "").strip().lower()
        if raw and raw not in {"1", "true", "yes", "on", "enabled", "0", "false", "no", "off", "disabled", ""}:
            warnings.append(f"{name}={raw!r} is not a recognized boolean; treated as default")

    # Timeout / retry ranges.
    if anthropic_timeout_seconds() != _int_env("CAREGUARD_ANTHROPIC_TIMEOUT_SECONDS", 75, lo=1, hi=10_000):
        warnings.append("CAREGUARD_ANTHROPIC_TIMEOUT_SECONDS clamped into [5,300]")

    # Model ids look like Anthropic ids.
    for role, model in all_models().items():
        if not any(model.startswith(p) for p in _KNOWN_MODEL_PREFIXES):
            warnings.append(f"CareGuard model for {role!r} ({model!r}) is not a known claude-* id")

    # Medication API bases are URLs.
    for name, base in medication_api_bases().items():
        if base and not _looks_like_url(base):
            errors.append(f"{name} API base {base!r} is not a valid http(s) URL")

    # Runtime readiness: if enabled, we should be able to actually run.
    if flags.careguard_enabled():
        if not anthropic_configured():
            warnings.append(
                "CAREGUARD_ENABLED=true but ANTHROPIC_API_KEY is unset — CareGuard runs in "
                "deterministic-fallback mode (no model prose; evidence/deterministic stages only)."
            )
        if flags.allow_identifiable_data() and flags.require_deidentification():
            errors.append(
                "CAREGUARD_ALLOW_IDENTIFIABLE_DATA=true conflicts with "
                "CAREGUARD_REQUIRE_DEIDENTIFICATION=true"
            )

    # Secret hygiene: never allow raw model IO logging in production posture.
    if flags.log_raw_model_inputs() or flags.log_raw_model_outputs():
        warnings.append(
            "Raw model input/output logging is enabled — must be false in any shared "
            "or production environment (may capture PHI)."
        )

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "careguard_enabled": flags.careguard_enabled(),
        "anthropic_configured": anthropic_configured(),
    }
