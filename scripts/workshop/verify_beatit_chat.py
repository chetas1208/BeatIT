"""Smoke-test BeatIT's generic Chat Completions path against Bedrock OpenAI."""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from python.hearttwin.intelligence.schemas import ChatMessage
from python.hearttwin.intelligence.factory import complete_text, intelligence_status


async def main() -> None:
    status = await intelligence_status()
    print("provider:", status.provider, "reachable:", status.reachable, "model:", status.model_configured)
    text = await complete_text(
        [ChatMessage(role="user", content="Reply with exactly: bedrock-ok")],
        max_tokens=32,
        temperature=0,
    )
    print("reply:", text.strip())


if __name__ == "__main__":
    asyncio.run(main())
