#!/usr/bin/env python3
"""Verify the two pinned Sonnet models are available to this account.

Scientific rule (spec §5): before any benchmark call, query Anthropic's Models
API and confirm the EXACT pinned IDs are retrievable. Never substitute another
model silently; never map 4.5 -> 4.6 or either -> Sonnet 5. If a model is
unavailable, mark its arms not-executable and record why.

Writes results/model_verification.json and exits non-zero if a required model
is missing (so the full-run scripts refuse to start).
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _bench_common import RESULTS_DIR, get_api_key  # noqa: E402

REQUIRED = {
    "sonnet_45": "claude-sonnet-4-5-20250929",
    "sonnet_46": "claude-sonnet-4-6",
}


def _utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _model_record(model_obj) -> dict:
    """Extract a JSON-safe record from an SDK Model object (robust to schema)."""
    rec: dict = {}
    for attr in ("id", "display_name", "created_at", "type",
                 "max_input_tokens", "max_tokens"):
        val = getattr(model_obj, attr, None)
        if val is not None:
            rec[attr] = str(val) if isinstance(val, _dt.datetime) else val
    caps = getattr(model_obj, "capabilities", None)
    if caps is not None:
        # capabilities is an untyped nested dict; keep a shallow view of the
        # leaves we care about for the benchmark contract.
        def leaf(*path):
            node = caps
            try:
                for p in path:
                    node = node[p]
                return node.get("supported") if isinstance(node, dict) else node
            except (KeyError, TypeError, AttributeError):
                return None
        rec["capabilities_probe"] = {
            "structured_outputs": leaf("structured_outputs"),
            "image_input": leaf("image_input"),
            "adaptive_thinking": leaf("thinking", "types", "adaptive"),
            "tool_use": leaf("tool_use") if leaf("tool_use") is not None
            else "assumed_true",
        }
    return rec


def main() -> int:
    import anthropic

    key = get_api_key()
    client = anthropic.Anthropic(api_key=key)

    result: dict = {
        "verified_at": _utcnow(),
        "endpoint": "GET /v1/models/{id} + GET /v1/models",
        "required_models": REQUIRED,
        "models": {},
        "all_listed_ids": [],
        "all_executable": True,
        "notes": [],
    }

    # 1) Enumerate the model list the account can see (auto-paginates).
    try:
        listed = [m.id for m in client.models.list()]
        result["all_listed_ids"] = listed
    except Exception as exc:  # pragma: no cover - network dependent
        result["notes"].append(f"models.list() failed: {exc!r}")
        listed = []

    # 2) Retrieve each required model EXACTLY; do not fall back.
    for arm_key, model_id in REQUIRED.items():
        entry: dict = {"model_id": model_id, "arm_key": arm_key}
        try:
            m = client.models.retrieve(model_id)
            entry["available"] = True
            entry["retrieved"] = _model_record(m)
            # Guard against any silent server-side aliasing.
            returned_id = getattr(m, "id", None)
            entry["id_matches_exactly"] = (returned_id == model_id)
            if not entry["id_matches_exactly"]:
                entry["available"] = False
                result["all_executable"] = False
                result["notes"].append(
                    f"{model_id}: server returned id {returned_id!r}; "
                    "refusing to treat as the requested model"
                )
        except Exception as exc:  # NotFoundError etc.
            entry["available"] = False
            entry["error"] = repr(exc)
            result["all_executable"] = False
            result["notes"].append(
                f"{model_id} unavailable to this account: {exc!r}"
            )
        result["models"][arm_key] = entry

    # 3) Cross-check: neither required ID may be an alias of the other.
    ids = [result["models"][k].get("retrieved", {}).get("id")
           for k in REQUIRED]
    if ids[0] and ids[0] == ids[1]:
        result["all_executable"] = False
        result["notes"].append(
            "45 and 46 resolved to the same id — comparison would be invalid"
        )

    out_path = RESULTS_DIR / "model_verification.json"
    out_path.write_text(json.dumps(result, indent=2))

    print(f"Wrote {out_path}")
    for arm_key, model_id in REQUIRED.items():
        e = result["models"][arm_key]
        status = "AVAILABLE" if e.get("available") else "NOT AVAILABLE"
        dn = e.get("retrieved", {}).get("display_name", "")
        so = e.get("retrieved", {}).get("capabilities_probe", {}) \
            .get("structured_outputs")
        print(f"  {model_id:32s} {status:14s} {dn}  "
              f"[structured_outputs={so}]")

    if not result["all_executable"]:
        print("\nRESULT: at least one required model is NOT executable.")
        print("Full paid comparison MUST NOT be claimed as completed.")
        return 2
    print("\nRESULT: both pinned models verified and executable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
