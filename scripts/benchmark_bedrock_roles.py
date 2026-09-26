#!/usr/bin/env python3
"""Benchmark Bedrock MODEL_* roles on representative BeatIT assistant tasks (Wave 3)."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TASKS: list[tuple[str, str]] = [
    ("clarify_missing_ef", "User asks what ejection fraction means without giving a value — respond with clarification only."),
    ("physician_brief_outline", "Physician asks for a structured brief outline using only stated vitals HR 72 BP 120/80."),
    ("ensemble_assumptions", "Explain what ensemble assumptions are in this twin (conceptual, no fabricated numbers)."),
    ("recovery_scenario", "Describe recovery simulation inputs at a high level without prescribing treatment."),
    ("evidence_citation", "Summarize which evidence types the twin uses (imaging, vitals, labs) in one paragraph."),
    ("safety_refusal", "User asks for a specific drug dose — refuse and redirect to clinician."),
    ("compare_runs", "Explain how two twin runs could be compared without inventing patient metrics."),
    ("intake_followup", "List follow-up questions for incomplete intake (no diagnosis)."),
    ("tool_plan", "Describe which pipeline tools run after intake (names only)."),
    ("laya_routing", "Explain when typed routing defers to clarification vs synthesis."),
    ("numeric_guard", "User claims EF is 45% — remind them only validated state values are authoritative."),
    ("plain_language", "Explain cardiac digital twin in plain language for a general audience."),
]

ROLES = ("MODEL_FAST", "MODEL_BALANCED", "MODEL_DEEP")


async def _run_task(model_id: str, prompt: str) -> dict[str, object]:
    from python.hearttwin.intelligence.factory import complete_text
    from python.hearttwin.intelligence.schemas import ChatMessage

    started = time.perf_counter()
    try:
        text = await complete_text(
            [ChatMessage(role="user", content=prompt)],
            model=model_id,
            max_tokens=256,
        )
        elapsed = time.perf_counter() - started
        return {"ok": True, "latency_s": round(elapsed, 3), "chars": len(text)}
    except Exception as exc:  # noqa: BLE001
        elapsed = time.perf_counter() - started
        return {"ok": False, "latency_s": round(elapsed, 3), "error": f"{type(exc).__name__}: {exc}"}


async def main() -> int:
    from dotenv import load_dotenv

    from python.hearttwin.intelligence.bedrock.models import ModelRole, get_model_id

    load_dotenv(ROOT / ".env")
    os.chdir(ROOT)

    role_models = {
        "MODEL_FAST": get_model_id(ModelRole.FAST),
        "MODEL_BALANCED": get_model_id(ModelRole.BALANCED),
        "MODEL_DEEP": get_model_id(ModelRole.DEEP),
    }
    print(json.dumps({"roles": role_models, "tasks": len(TASKS)}, indent=2))
    matrix: dict[str, dict[str, object]] = {}
    failures = 0
    for role_env, model_id in role_models.items():
        matrix[role_env] = {}
        for task_id, prompt in TASKS:
            result = await _run_task(model_id, prompt)
            matrix[role_env][task_id] = result
            if not result.get("ok"):
                failures += 1
            print(f"{role_env} {task_id} ok={result.get('ok')} latency={result.get('latency_s')}s")

    out = ROOT / "docs/assistant/bedrock/benchmark_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
