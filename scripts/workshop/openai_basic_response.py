"""Workshop Lab 1 — basic Responses API via OpenAI SDK + Bedrock provider."""
from __future__ import annotations

import os

from openai import OpenAI
from openai.providers import bedrock

client = OpenAI(provider=bedrock(endpoint="runtime"))

response = client.responses.create(
    model=os.environ["MODEL_ID"],
    input=[{"role": "user", "content": "Hello! How can you help me today?"}],
)

print(response.output_text)
