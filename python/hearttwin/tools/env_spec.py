"""Canonical specification of BeatIT environment variables.

Single source of truth shared by:
  * scripts/verify_env.py (CLI validator)
  * python/hearttwin/tests/test_env_config.py (test suite)

Each entry declares the variable name, category, whether it is required for a
production deployment, whether it is a secret (must never be exposed), an
optional default, and a short description. Optional integrations degrade to
local/deterministic fallbacks, so very few vars are strictly required.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class EnvVarSpec:
    name: str
    category: str
    required_for_production: bool = False
    secret: bool = False
    default: Optional[str] = None
    description: str = ""
    # Optional validator returning an error string, or None when valid.
    validator: Optional[Callable[[str], Optional[str]]] = field(default=None, compare=False)


def _is_numeric(value: str) -> Optional[str]:
    try:
        float(value)
        return None
    except (TypeError, ValueError):
        return f"expected a numeric value, got {value!r}"


def _is_bool(value: str) -> Optional[str]:
    if value.strip().lower() in {
        "1", "true", "yes", "on", "enabled",
        "0", "false", "no", "off", "disabled",
    }:
        return None
    return f"expected a boolean-like value, got {value!r}"


# Canonical env var specification.
ENV_SPEC: list[EnvVarSpec] = [
    # --- Provider-neutral model runtime ---
    EnvVarSpec("MODEL_ENABLED", "model", default="true", validator=_is_bool,
               description="Enable provider-backed language/extraction features."),
    EnvVarSpec("MODEL_API_PROTOCOL", "model", default="openai-compatible",
               description="Protocol used by the configured model endpoint."),
    EnvVarSpec("MODEL_API_KEY", "model", secret=True,
               description="Private key for the configured compatible endpoint."),
    EnvVarSpec("MODEL_BASE_URL", "model",
               description="Private OpenAI-compatible endpoint base URL."),
    EnvVarSpec("MODEL_NAME", "model",
               description="Default model name at the configured endpoint."),
    EnvVarSpec("MODEL_TIMEOUT_SECONDS", "model", default="45", validator=_is_numeric,
               description="Model request timeout in seconds."),
    EnvVarSpec("MODEL_MAX_RETRIES", "model", default="2", validator=_is_numeric,
               description="Maximum model request retries."),
    EnvVarSpec("INTELLIGENCE_PROVIDER", "model", default="generic",
               description="generic, openai, or disabled."),
    EnvVarSpec("BEATIT_MODEL_ROOT", "model",
               description="Optional centralized root for local model artifacts."),
    EnvVarSpec("BEATIT_SEGMENTATION_MODEL", "model",
               description="Optional local medical-segmentation checkpoint path."),
    EnvVarSpec("BEATIT_LANGUAGE_MODEL", "model",
               description="Optional local language model path or endpoint identifier."),
    EnvVarSpec("BEATIT_EMBEDDING_MODEL", "model",
               description="Optional local embedding model path or identifier."),
    EnvVarSpec("OPENAI_ENABLED", "openai", default="false", validator=_is_bool,
               description="Enable the optional first-party OpenAI adapter."),
    EnvVarSpec("OPENAI_MODEL", "openai",
               description="Default model for the optional OpenAI adapter."),
    # --- OpenAI ---
    EnvVarSpec("OPENAI_API_KEY", "openai", required_for_production=False, secret=True,
               description="OpenAI API key; missing → deterministic fallbacks."),
    EnvVarSpec("OPENAI_MODEL_INTAKE", "openai", default="gpt-5.4-mini",
               description="Model for the Intake & Safety agent."),
    EnvVarSpec("OPENAI_MODEL_EXTRACTION", "openai", default="gpt-5.4-mini",
               description="Model for the Multimodal Extraction agent."),
    EnvVarSpec("OPENAI_MODEL_VALIDATOR", "openai", default="gpt-5.4-mini",
               description="Model for the Evidence Validator agent."),
    EnvVarSpec("OPENAI_MODEL_STATE_BUILDER", "openai", default="gpt-5.5",
               description="Model for the Cardiac State Builder agent."),
    EnvVarSpec("OPENAI_MODEL_ELECTROPHYSIOLOGY", "openai", default="gpt-5.4-mini",
               description="Model for the Electrophysiology agent."),
    EnvVarSpec("OPENAI_MODEL_HEMODYNAMICS", "openai", default="gpt-5.4-mini",
               description="Model for the Hemodynamics Simulation agent."),
    EnvVarSpec("OPENAI_MODEL_RECOVERY", "openai", default="gpt-5.5",
               description="Model for the Recovery Orchestration agent."),
    EnvVarSpec("OPENAI_MODEL_EVALUATOR", "openai", default="gpt-5.5",
               description="Model for the Evaluator & Critic agent."),
    EnvVarSpec("OPENAI_MODEL_FAST", "openai", default="gpt-5.4-nano",
               description="Fast/utility model for cheap tasks."),
    EnvVarSpec("OPENAI_EMBEDDING_MODEL", "openai", default="text-embedding-3-small",
               description="Embedding model for case memory vectors."),
    # --- W&B / Weave ---
    EnvVarSpec("WANDB_API_KEY", "weave", secret=True,
               description="W&B key; missing → local trace fallback."),
    EnvVarSpec("WANDB_ENTITY", "weave",
               description="W&B entity (optional)."),
    EnvVarSpec("WANDB_PROJECT", "weave", default="hearttwin-weavehacks",
               description="W&B project; should be hearttwin-weavehacks."),
    EnvVarSpec("NEXT_PUBLIC_WEAVE_PROJECT_URL", "weave",
               description="Public Weave project URL (safe to expose)."),
    # --- Storage ---
    EnvVarSpec("BLOB_READ_WRITE_TOKEN", "storage", secret=True,
               description="Vercel Blob token; missing → local metadata fallback."),
    EnvVarSpec("ARTIFACT_ROOT", "storage", default="data/artifacts",
               description="Local artifact storage root when AWS is disabled."),
    EnvVarSpec("AWS_ENABLED", "aws", default="false", validator=_is_bool,
               description="Enable the optional S3 artifact adapter."),
    EnvVarSpec("AWS_REGION", "aws", default="us-west-2",
               description="AWS region for optional S3 storage."),
    EnvVarSpec("AWS_ACCESS_KEY_ID", "aws", secret=True,
               description="Optional AWS access key supplied by deployment secrets."),
    EnvVarSpec("AWS_SECRET_ACCESS_KEY", "aws", secret=True,
               description="Optional AWS secret supplied by deployment secrets."),
    EnvVarSpec("AWS_S3_BUCKET", "aws",
               description="S3 bucket used only when AWS_ENABLED=true."),
    EnvVarSpec("DATABASE_URL", "database", secret=True,
               description="Optional self-hosted database URL."),
    EnvVarSpec("BEATIT_ENSEMBLE_STORE", "storage", default="sqlite",
               description="Plausible-twin persistence provider; file-backed sqlite is required."),
    EnvVarSpec("BEATIT_ENSEMBLE_DB_PATH", "storage", default="data/beatit-ensembles.sqlite3",
               description="Local SQLite path for durable plausible-twin ensembles."),
    # --- Redis ---
    EnvVarSpec("REDIS_URL", "redis", secret=True,
               description="Redis connection URL (redis:// or rediss://); missing → in-memory fallback."),
    # --- API base ---
    EnvVarSpec("NEXT_PUBLIC_API_BASE", "api", default="/api/v1",
               description="Primary public API base used by the Next.js frontend."),
    EnvVarSpec("API_BASE", "api", default="/api/v1",
               description="Server-side API base."),
    # --- VISTA-3D ---
    EnvVarSpec("VISTA3D_API_BASE", "vista3d",
               description="VISTA-3D endpoint base URL (optional)."),
    EnvVarSpec("VISTA3D_API_KEY", "vista3d", secret=True,
               description="VISTA-3D API key (optional)."),
    EnvVarSpec("VISTA3D_TIMEOUT_SECONDS", "vista3d", default="120", validator=_is_numeric,
               description="VISTA-3D request timeout in seconds (numeric)."),
    EnvVarSpec("VISTA3D_ENABLED", "vista3d", default="false", validator=_is_bool,
               description="Whether VISTA-3D is enabled (boolean)."),
    # --- App ---
    EnvVarSpec("NEXT_PUBLIC_APP_NAME", "app", default="BeatIT",
               description="Public app name."),
    EnvVarSpec("HEARTTWIN_SAFETY_MODE", "app", default="strict",
               description="Safety mode; expected strict."),
    EnvVarSpec("HEARTTWIN_TRACE_MODE", "app", default="weave_with_local_fallback",
               description="Trace mode."),
    EnvVarSpec("HEARTTWIN_REDIS_MEMORY_ENABLED", "app", default="true", validator=_is_bool,
               description="Whether Redis memory is enabled (boolean)."),
]


# Variables that must NEVER appear in a public config/system-check response.
SECRET_ENV_VARS: list[str] = [spec.name for spec in ENV_SPEC if spec.secret]

EXPECTED_ENV_NAMES: set[str] = {spec.name for spec in ENV_SPEC}

DEPLOY_MODES = ("local-dev", "vercel-preview", "vercel-production")


def get_spec(name: str) -> Optional[EnvVarSpec]:
    for spec in ENV_SPEC:
        if spec.name == name:
            return spec
    return None


def validate_env(mode: str = "local-dev") -> dict:
    """Validate the current process environment against the spec.

    Returns a structured report. Never raises. ``errors`` are structural
    problems (invalid values, or production-required vars missing in a vercel
    production deploy). ``warnings`` are non-fatal (optional vars missing).
    """
    if mode not in DEPLOY_MODES:
        mode = "local-dev"

    errors: list[str] = []
    warnings: list[str] = []
    present: list[str] = []
    missing_optional: list[str] = []

    for spec in ENV_SPEC:
        raw = os.environ.get(spec.name)
        has_value = raw is not None and raw.strip() != ""

        if has_value:
            present.append(spec.name)
            if spec.validator is not None:
                err = spec.validator(raw)
                if err is not None:
                    errors.append(f"{spec.name}: {err}")
        else:
            if spec.default is not None:
                # Has a safe fallback; not a problem.
                pass
            elif spec.required_for_production and mode == "vercel-production":
                errors.append(f"{spec.name}: required for production but missing")
            else:
                missing_optional.append(spec.name)
                warnings.append(f"{spec.name}: not set ({spec.category}) — {spec.description}")

    # WANDB_PROJECT sanity
    wandb_project = os.environ.get("WANDB_PROJECT")
    if wandb_project and wandb_project != "hearttwin-weavehacks":
        warnings.append(
            f"WANDB_PROJECT is '{wandb_project}', expected 'hearttwin-weavehacks'"
        )

    return {
        "mode": mode,
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "present": present,
        "missing_optional": missing_optional,
    }
