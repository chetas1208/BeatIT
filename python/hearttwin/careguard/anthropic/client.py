"""Anthropic Messages client for CareGuard — structured, safe, optional.

If no ANTHROPIC_API_KEY is set (or the SDK is absent), ``is_available()`` is
False and callers use their deterministic path. When available, structured calls
enforce: deidentification for deidentify-only models, refusal detection with
fallback, schema validation, and redacted telemetry. Per spec §7, temperature/
top_p/top_k are never set for Sonnet/Fable.
"""

from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel

from python.hearttwin.careguard import config as cg_config
from python.hearttwin.careguard.anthropic import model_router, refusal_handler, structured_output
from python.hearttwin.careguard.anthropic.telemetry import record_call
from python.hearttwin.careguard.errors import DeidentificationError, ModelRefusalError
from python.hearttwin.careguard.security import assert_no_identifiers, deidentify_for_model

_ADAPTIVE_ROLES = {"medication_safety", "candidate_composition", "clinical_critic"}


class StructuredResult(BaseModel):
    ok: bool
    model_used: str | None = None
    obj: dict | None = None
    refusal: dict | None = None
    error: str | None = None
    fell_back: bool = False
    deidentified: bool = False


def is_available() -> bool:
    if not cg_config.anthropic_configured():
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _client(api_key: str):
    import anthropic

    return anthropic.Anthropic(
        api_key=api_key,
        max_retries=cg_config.anthropic_max_retries(),
        timeout=float(cg_config.anthropic_timeout_seconds()),
    )


# Errors that should trigger a failover to the next API key (not a model change).
def _is_key_level_error(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    return any(t in name for t in (
        "authentication", "permission", "ratelimit", "apiconnection",
        "apistatus", "apitimeout", "internalserver", "overloaded", "notfound",
    ))


def _prepare_payload(payload: Any, model: str) -> tuple[Any, bool]:
    """Return (payload, deidentified). Enforces the retention boundary."""
    if model_router.requires_deidentification(model):
        clean = deidentify_for_model(payload)
        leaked = assert_no_identifiers(clean)
        if leaked:
            raise DeidentificationError(
                f"identifiers survived deidentification before a deidentify-only model: {leaked}"
            )
        return clean, True
    return payload, False


def _one_call(*, model: str, system: str, payload: Any, schema: dict, stage_id: str) -> Any:
    """Make one structured call, transparently failing over across API keys.

    Tries each configured key in order; a key-level failure (auth/rate/connection/
    overloaded) moves to the next key. Raises the last error only if every key fails.
    """
    import json

    tool = structured_output.build_forced_tool(schema)
    # Per spec §7: no temperature/top_p/top_k for current Claude models.
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": 2048,
        "system": system,
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": structured_output.STRUCTURED_TOOL_NAME},
        "messages": [
            {"role": "user", "content": json.dumps(payload, default=str)}
        ],
    }
    keys = cg_config.anthropic_api_keys()
    last_exc: Exception | None = None
    for idx, key in enumerate(keys):
        try:
            resp = _client(key).messages.create(**kwargs)
            if idx > 0:
                record_call(stage_id=stage_id, model=model, status="key_failover",
                            detail={"key_index": idx})
            return resp
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if _is_key_level_error(exc) and idx < len(keys) - 1:
                record_call(stage_id=stage_id, model=model, status="key_error_failover",
                            detail={"key_index": idx, "error": type(exc).__name__})
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("no Anthropic API key configured")


def generate_structured(
    *,
    stage_id: str,
    system: str,
    payload: Any,
    schema: dict,
    model_cls: Type[BaseModel],
) -> StructuredResult:
    """Structured call with refusal-fallback-abstain. Never raises on refusal —
    returns ok=False with a refusal record so the caller can abstain safely."""
    if not is_available():
        return StructuredResult(ok=False, error="anthropic_unavailable")

    primary = model_router.model_for_stage(stage_id)
    payload_p, deid = _prepare_payload(payload, primary)

    try:
        resp = _one_call(model=primary, system=system, payload=payload_p, schema=schema, stage_id=stage_id)
    except Exception as exc:  # noqa: BLE001 — network/timeout/rate-limit → try fallback
        record_call(stage_id=stage_id, model=primary, status="error", detail={"error": type(exc).__name__})
        resp = None

    if resp is not None and not refusal_handler.is_refusal(resp):
        data = structured_output.extract_tool_input(resp)
        obj, err = structured_output.try_validate(model_cls, data)
        record_call(stage_id=stage_id, model=primary, status="ok" if obj else "invalid_output")
        if obj is not None:
            return StructuredResult(ok=True, model_used=primary, obj=obj.model_dump(), deidentified=deid)

    # Refusal or failure → fallback model (always Sonnet, receives deid payload).
    refusal = refusal_handler.refusal_metadata(resp, primary) if resp is not None else {
        "model": primary, "stop_reason": "error", "handled": True, "content_stored": False
    }
    fb = model_router.fallback_model()
    fb_payload, fb_deid = _prepare_payload(payload, fb)
    try:
        resp2 = _one_call(model=fb, system=system, payload=fb_payload, schema=schema, stage_id=stage_id)
    except Exception as exc:  # noqa: BLE001
        record_call(stage_id=stage_id, model=fb, status="error", detail={"error": type(exc).__name__})
        return StructuredResult(ok=False, model_used=fb, refusal=refusal, error="fallback_failed", fell_back=True)

    if refusal_handler.is_refusal(resp2):
        record_call(stage_id=stage_id, model=fb, status="refusal")
        return StructuredResult(
            ok=False, model_used=fb, refusal=refusal_handler.refusal_metadata(resp2, fb),
            error="double_refusal", fell_back=True,
        )
    data2 = structured_output.extract_tool_input(resp2)
    obj2, err2 = structured_output.try_validate(model_cls, data2)
    record_call(stage_id=stage_id, model=fb, status="ok" if obj2 else "invalid_output")
    if obj2 is not None:
        return StructuredResult(ok=True, model_used=fb, obj=obj2.model_dump(), fell_back=True, deidentified=fb_deid)
    return StructuredResult(ok=False, model_used=fb, refusal=refusal, error=err2 or "invalid_output", fell_back=True)
