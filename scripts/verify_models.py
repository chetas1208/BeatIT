#!/usr/bin/env python3
"""Verify BeatIT's model portfolio without pretending metadata is inference."""

from __future__ import annotations

import json
import os
import platform
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "models" / "manifest.json"
REPORT_JSON = ROOT / "artifacts" / "model-verification.json"
REPORT_MD = ROOT / "docs" / "models" / "FINAL_LOCAL_MODEL_INVENTORY.md"


def _placeholder(value: str | None) -> bool:
    if not value:
        return True
    return any(token in value.upper() for token in ("REPLACE", "CHANGE_ME", "YOUR_", "EXAMPLE"))


def _vista_check(path: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "capability": "medical-segmentation",
        "path": str(path),
        "required": False,
        "status": "MISSING",
        "files": path.is_file(),
        "load": False,
        "inference": False,
        "gpu_smoke": False,
    }
    if not path.is_file():
        return result
    result["size_bytes"] = path.stat().st_size
    metadata = path.parent.parent / "configs" / "metadata.json"
    result["metadata_present"] = metadata.is_file()
    if metadata.is_file():
        try:
            meta = json.loads(metadata.read_text())
            result["bundle_version"] = meta.get("version")
            result["expected_pytorch"] = meta.get("pytorch_version")
            result["expected_monai"] = meta.get("monai_version")
        except (OSError, ValueError) as exc:
            result["metadata_error"] = type(exc).__name__
    try:
        import torch

        started = time.perf_counter()
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        result["load"] = isinstance(checkpoint, dict)
        result["load_seconds"] = round(time.perf_counter() - started, 3)
        result["checkpoint_keys"] = len(checkpoint) if isinstance(checkpoint, dict) else 0
        if torch.cuda.is_available():
            device = torch.device("cuda:0")
            _ = torch.zeros((1,), device=device) + 1
            result["gpu_smoke"] = True
            result["gpu_name"] = torch.cuda.get_device_name(0)
        result["torch_version"] = torch.__version__
    except Exception as exc:  # noqa: BLE001 - report exact safe exception class only
        result["load_error"] = type(exc).__name__
    # BeatIT's request-facing adapter is API-gated and does not have a local
    # runner contract, so checkpoint load is not misreported as inference.
    result["inference"] = False
    result["status"] = "COMPLETE_BUT_INCOMPATIBLE" if result["load"] else "PARTIAL_DOWNLOAD"
    result["inference_note"] = "No configured local MONAI/VISTA runner; service adapter remains disabled."
    return result


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    models: list[dict[str, object]] = []
    vista_path = Path(os.environ.get("BEATIT_SEGMENTATION_MODEL", "") or manifest["models"]["medical-segmentation"]["default_path"])
    models.append(_vista_check(vista_path))
    language_path = os.environ.get("BEATIT_LANGUAGE_MODEL", "")
    models.append({
        "capability": "language",
        "path": language_path or None,
        "required": False,
        "files": bool(language_path and Path(language_path).exists()),
        "load": False,
        "inference": False,
        "status": "OPTIONAL_NOT_INSTALLED" if not language_path or _placeholder(language_path) else "NOT_VALIDATED",
        "note": "No approved local serving contract; deterministic fallback is authoritative.",
    })
    embedding_path = os.environ.get("BEATIT_EMBEDDING_MODEL", "")
    models.append({
        "capability": "embedding",
        "path": embedding_path or None,
        "required": False,
        "status": "OPTIONAL_NOT_INSTALLED" if not embedding_path else "NOT_VALIDATED",
        "note": "Semantic retrieval is not required by the current BeatIT path.",
    })
    report = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": platform.node(),
        "portfolio_policy": "No model is required for deterministic cardiac physiology; optional models cannot upgrade numeric authority.",
        "models": models,
        "learned_ecg_model": {"required": False, "status": "NOT_REQUIRED"},
        "overall": "DETERMINISTIC_FALLBACK_READY",
        "live_model_claims": "NOT_READY",
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        "# BeatIT Final Local Model Inventory",
        "",
        "This report distinguishes checkpoint presence/load from request-serving inference.",
        "",
        "| Capability | Path/configured | Files | Load | Inference | GPU smoke | Required | Status |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for model in models:
        rows.append(
            f"| {model['capability']} | {'configured' if model.get('path') else 'not configured'} | "
            f"{model.get('files', 'n/a')} | {model.get('load', 'n/a')} | {model.get('inference', 'n/a')} | "
            f"{model.get('gpu_smoke', 'n/a')} | {model['required']} | {model['status']} |"
        )
    rows += [
        "",
        "- Learned ECG model: `NOT_REQUIRED`; the current path uses deterministic ECG parsing/formulas.",
        "- Overall: `DETERMINISTIC_FALLBACK_READY`; live model claims remain `NOT_READY`.",
        "- The VISTA checkpoint is not treated as usable inference without a configured compatible runner and smoke output.",
    ]
    REPORT_MD.write_text("\n".join(rows) + "\n")
    for model in models:
        print(f"{model['capability']:<24} {model['status']}")
    print("OVERALL                 DETERMINISTIC_FALLBACK_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
