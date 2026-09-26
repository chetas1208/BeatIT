#!/usr/bin/env python3
"""Smoke-test configured Bedrock OpenAI model IDs (chat completions)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODEL_ENV_KEYS = (
    "MODEL_NAME",
    "OPENAI_MODEL",
    "OPENAI_MODEL_INTAKE",
    "OPENAI_MODEL_EXTRACTION",
    "OPENAI_MODEL_VALIDATOR",
    "OPENAI_MODEL_STATE_BUILDER",
    "OPENAI_MODEL_ELECTROPHYSIOLOGY",
    "OPENAI_MODEL_HEMODYNAMICS",
    "OPENAI_MODEL_RECOVERY",
    "OPENAI_MODEL_EVALUATOR",
    "OPENAI_MODEL_FAST",
)


async def _probe(model_id: str) -> tuple[str, str]:
    from python.hearttwin.intelligence.factory import complete_text
    from python.hearttwin.intelligence.schemas import ChatMessage

    try:
        text = await complete_text(
            [ChatMessage(role="user", content=f"Reply with exactly: ok-{model_id.split('.')[-1][:12]}")],
            model=model_id,
            max_tokens=24,
        )
        return "ok", text.strip()[:80]
    except Exception as exc:  # noqa: BLE001 — report all failures in the matrix
        return "fail", f"{type(exc).__name__}: {exc}"


async def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    os.chdir(ROOT)

    models: dict[str, str] = {}
    for key in MODEL_ENV_KEYS:
        value = (os.environ.get(key) or "").strip()
        if value and not value.startswith("REPLACE_WITH_"):
            models[f"{key}={value}"] = value

    if not models:
        print("No model IDs found in environment.", file=sys.stderr)
        return 1

    print(f"provider={os.environ.get('INTELLIGENCE_PROVIDER', '?')} openai_enabled={os.environ.get('OPENAI_ENABLED', '?')}")
    print(f"base_url={os.environ.get('OPENAI_BASE_URL', os.environ.get('MODEL_BASE_URL', '?'))}")
    print("-" * 72)

    failures = 0
    for label, model_id in sorted(models.items(), key=lambda item: item[1]):
        status, detail = await _probe(model_id)
        print(f"{status:4}  {label}")
        if status != "ok":
            failures += 1
            print(f"      {detail}")

    print("-" * 72)
    print(f"tested={len(models)} failed={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
