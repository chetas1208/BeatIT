"""Model-arm call layer: identical request shape across both pinned models.

Structured output uses a single FORCED tool (tool_choice = {type: tool}) whose
input_schema is the benchmark output contract. This is portable across Sonnet
4.5 and 4.6 without depending on output_config.format (structured-output support
is not guaranteed on 4.5). The ONLY intended difference between paired arms is
the model id: no temperature/top_p/top_k, no thinking, identical max_tokens,
identical tool policy.

Returns a trial_result record (schemas/trial_result.schema.json).
"""

from __future__ import annotations

import copy
import datetime as _dt
import json
import time
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bench_common import cost_usd, load_schema  # noqa: E402

TOOL_NAME = "submit_medication_safety_review"

# Fields the harness injects, not the model.
_INJECTED = {"case_id", "arm_id", "trial_id"}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def build_tool_schema() -> dict:
    """Benchmark output schema adapted as a forced-tool input_schema."""
    out = load_schema("benchmark_output")
    schema = copy.deepcopy(out)
    # Drop harness-injected fields from properties/required so the model only
    # produces the review content.
    for k in list(schema.get("properties", {})):
        if k in _INJECTED:
            schema["properties"].pop(k, None)
    schema["required"] = [
        r for r in schema.get("required", []) if r not in _INJECTED
    ]
    return schema


def make_tool() -> dict:
    return {
        "name": TOOL_NAME,
        "description": (
            "Submit the structured medication-safety review for this case. "
            "Call exactly once with the full object."
        ),
        "input_schema": build_tool_schema(),
    }


# ----------------------------------------------------------------------------
# Deterministic syntax-only repair (spec §10): prune unknown keys and coerce
# obvious scalar types. NEVER changes clinical content or enum values.
# ----------------------------------------------------------------------------
def _coerce_scalar(value, expected_types):
    if "number" in expected_types:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return value
    if "boolean" in expected_types and isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes"):
            return True
        if low in ("false", "no"):
            return False
    if "string" in expected_types and isinstance(value, (int, float, bool)):
        return str(value)
    return value


def _types(node: dict) -> set:
    t = node.get("type")
    if isinstance(t, list):
        return set(t)
    if isinstance(t, str):
        return {t}
    return set()


def repair_against_schema(obj: Any, schema: dict) -> Any:
    """Prune unknown keys, coerce scalars. Structure/content preserved."""
    types = _types(schema)
    if "object" in types and isinstance(obj, dict):
        props = schema.get("properties", {})
        out = {}
        for k, v in obj.items():
            if k in props:
                out[k] = repair_against_schema(v, props[k])
            elif schema.get("additionalProperties") is not False:
                out[k] = v
            # else: unknown key under additionalProperties:false -> drop
        return out
    if "array" in types and isinstance(obj, list):
        item_schema = schema.get("items", {})
        return [repair_against_schema(i, item_schema) for i in obj]
    if types and not (types & {"object", "array"}):
        return _coerce_scalar(obj, types)
    return obj


def validate(obj: dict, schema: dict) -> list[str]:
    from jsonschema import Draft7Validator

    return [
        f"{'/'.join(str(p) for p in e.path)}: {e.message}"
        for e in Draft7Validator(schema).iter_errors(obj)
    ]


# ----------------------------------------------------------------------------
# The call
# ----------------------------------------------------------------------------
def run_model_trial(
    *,
    client,
    model_id: str,
    arm_id: str,
    case_id: str,
    trial_id: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    max_retries: int,
    timeout_seconds: int,
    store_raw_dir: Path | None = None,
) -> dict:
    """One trial against one pinned model. Identical shape for every arm."""
    import anthropic

    tool = make_tool()
    out_schema = load_schema("benchmark_output")

    record: dict = {
        "case_id": case_id, "arm_id": arm_id, "trial_id": trial_id,
        "model_id": model_id, "status": "api_failure",
        "output": None, "raw_output_present": False, "usage": {},
        "cost_usd": 0.0, "latency_seconds": 0.0, "stop_reason": None,
        "request_id": None, "retry_count": 0, "error_type": None,
        "tool_call_count": 0, "started_at": _now(), "finished_at": None,
    }

    last_exc = None
    for attempt in range(max_retries + 1):
        record["retry_count"] = attempt
        t0 = time.monotonic()
        try:
            resp = client.with_options(
                timeout=float(timeout_seconds), max_retries=0,
            ).messages.create(
                model=model_id,
                max_tokens=max_tokens,
                system=system_prompt,
                tools=[tool],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIStatusError as exc:
            last_exc = exc
            record["error_type"] = type(exc).__name__
            # Retry 429/5xx; do not retry 4xx client errors.
            code = getattr(exc, "status_code", 0)
            if code == 429 or code >= 500:
                time.sleep(min(2 ** attempt, 20))
                continue
            record["latency_seconds"] = round(time.monotonic() - t0, 3)
            break
        except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
            last_exc = exc
            record["error_type"] = type(exc).__name__
            time.sleep(min(2 ** attempt, 20))
            continue
        except Exception as exc:  # unexpected
            last_exc = exc
            record["error_type"] = type(exc).__name__
            record["latency_seconds"] = round(time.monotonic() - t0, 3)
            break

        # --- success path ---
        record["latency_seconds"] = round(time.monotonic() - t0, 3)
        record["request_id"] = getattr(resp, "_request_id", None)
        record["stop_reason"] = getattr(resp, "stop_reason", None)
        usage = getattr(resp, "usage", None)
        if usage is not None:
            record["usage"] = {
                "input_tokens": getattr(usage, "input_tokens", 0),
                "output_tokens": getattr(usage, "output_tokens", 0),
                "cache_creation_input_tokens":
                    getattr(usage, "cache_creation_input_tokens", 0) or 0,
                "cache_read_input_tokens":
                    getattr(usage, "cache_read_input_tokens", 0) or 0,
            }
            record["cost_usd"] = round(cost_usd(model_id, record["usage"]), 6)

        tool_inputs = [
            b.input for b in resp.content
            if getattr(b, "type", None) == "tool_use"
            and getattr(b, "name", None) == TOOL_NAME
        ]
        record["tool_call_count"] = len(tool_inputs)

        if not tool_inputs:
            record["status"] = "schema_failure"
            record["error_type"] = "no_tool_call"
            break

        raw = tool_inputs[0]
        record["raw_output_present"] = True
        if store_raw_dir is not None:
            store_raw_dir.mkdir(parents=True, exist_ok=True)
            (store_raw_dir / f"{case_id}__{arm_id}__{trial_id}.json").write_text(
                json.dumps(raw, indent=2, default=str)
            )

        # Inject harness fields, then validate/repair.
        obj = dict(raw)
        obj["case_id"] = case_id
        obj["arm_id"] = arm_id
        obj["trial_id"] = trial_id

        errors = validate(obj, out_schema)
        if not errors:
            record["status"] = "ok"
            record["output"] = obj
        else:
            repaired = repair_against_schema(obj, out_schema)
            repaired["case_id"] = case_id
            repaired["arm_id"] = arm_id
            repaired["trial_id"] = trial_id
            rerrors = validate(repaired, out_schema)
            if not rerrors:
                record["status"] = "repaired"
                record["output"] = repaired
                record["repair_note"] = "syntax-only prune/coerce"
                record["original_output"] = obj
            else:
                record["status"] = "schema_failure"
                # keep the (urepaired) output so graders can still score it
                record["output"] = obj
                record["schema_errors"] = errors[:8]
        break

    record["finished_at"] = _now()
    if record["status"] == "api_failure" and last_exc is not None:
        record["error_detail"] = repr(last_exc)[:300]
    return record
