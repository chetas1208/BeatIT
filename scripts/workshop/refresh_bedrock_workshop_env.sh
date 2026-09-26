#!/usr/bin/env bash
# Workshop Studio: OpenAI models on Amazon Bedrock (Getting Started → Labs)
# Requires AWS CLI credentials from the event (temporary keys + session token).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REGION="${AWS_DEFAULT_REGION:-${AWS_REGION:-us-east-1}}"
export AWS_DEFAULT_REGION="$REGION"
export AWS_REGION="$REGION"

MODEL_ID="${MODEL_ID:-global.openai.gpt-5.6-terra}"
OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://bedrock-runtime.${REGION}.amazonaws.com/openai/v1}"

if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "Missing or invalid AWS credentials." >&2
  echo "From the event: Get AWS CLI credentials → export AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, AWS_DEFAULT_REGION=us-east-1" >&2
  exit 1
fi

PYTHON="${PYTHON:-python3}"
if ! "$PYTHON" -c "import aws_bedrock_token_generator" 2>/dev/null; then
  echo "Installing aws-bedrock-token-generator…" >&2
  "$PYTHON" -m pip install -q aws-bedrock-token-generator
fi

TOKEN="$("$PYTHON" -c "from aws_bedrock_token_generator import provide_token; print(provide_token())")"

export MODEL_ID
export OPENAI_BASE_URL
export OPENAI_API_KEY="$TOKEN"

# BeatIT generic intelligence (Chat Completions on /openai/v1)
export MODEL_API_KEY="$TOKEN"
export MODEL_BASE_URL="$OPENAI_BASE_URL"
export MODEL_NAME="$MODEL_ID"
export INTELLIGENCE_PROVIDER=generic
export MODEL_ENABLED=true
export MODEL_API_PROTOCOL=openai-compatible

echo "Workshop env ready (region=${REGION}, model=${MODEL_ID})."
echo "  OPENAI_BASE_URL=${OPENAI_BASE_URL}"
echo "  OPENAI_API_KEY=<bedrock bearer, ${#TOKEN} chars>"
echo ""
echo "Run labs: cd ${ROOT}/scripts/workshop && python openai_basic_response.py"
echo "BeatIT: restart uvicorn after sourcing this file, or run: python ${ROOT}/scripts/workshop/verify_beatit_chat.py"
