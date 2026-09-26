#!/usr/bin/env python3
"""Refresh MODEL_API_KEY in .env from AWS creds (Bedrock short-lived bearer)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def main() -> int:
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Install python-dotenv in your environment.", file=sys.stderr)
        return 1

    load_dotenv(ENV_PATH)
    try:
        from aws_bedrock_token_generator import provide_token
    except ImportError:
        print("Run: pip install aws-bedrock-token-generator", file=sys.stderr)
        return 1

    token = provide_token()
    if not token or not str(token).strip():
        print("Bedrock token generator returned empty token.", file=sys.stderr)
        return 1

    text = ENV_PATH.read_text(encoding="utf-8")
    if "MODEL_API_KEY=" not in text:
        print("MODEL_API_KEY= not found in .env", file=sys.stderr)
        return 1

    updated, count = re.subn(
        r"^MODEL_API_KEY=.*$",
        f"MODEL_API_KEY={token.strip()}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        print("Failed to update MODEL_API_KEY in .env", file=sys.stderr)
        return 1

    if "OPENAI_API_KEY=" in updated:
        updated, openai_count = re.subn(
            r"^OPENAI_API_KEY=.*$",
            f"OPENAI_API_KEY={token.strip()}",
            updated,
            count=1,
            flags=re.MULTILINE,
        )
        if openai_count != 1:
            print("Warning: OPENAI_API_KEY= not updated", file=sys.stderr)

    if "AWS_BEARER_TOKEN_BEDROCK=" in updated:
        updated, bearer_count = re.subn(
            r"^AWS_BEARER_TOKEN_BEDROCK=.*$",
            f"AWS_BEARER_TOKEN_BEDROCK={token.strip()}",
            updated,
            count=1,
            flags=re.MULTILINE,
        )
        if bearer_count != 1:
            print("Warning: AWS_BEARER_TOKEN_BEDROCK= not updated", file=sys.stderr)

    ENV_PATH.write_text(updated, encoding="utf-8")
    print(f"Updated MODEL_API_KEY in {ENV_PATH} (length={len(token.strip())})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
