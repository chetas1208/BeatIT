# AWS Workshop Studio — OpenAI on Bedrock

Event region: **us-east-1**.

## 1. Export workshop AWS credentials

In the event dashboard: **Get AWS CLI credentials**, then in your terminal:

```bash
export AWS_DEFAULT_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..."
export MODEL_ID="global.openai.gpt-5.6-terra"   # use value from Getting Started if different
```

## 2. Load Bedrock bearer + BeatIT model env

```bash
cd /home/923873155/BeatIT
source scripts/workshop/refresh_bedrock_workshop_env.sh
```

This sets:

| Workshop | BeatIT |
|----------|--------|
| `OPENAI_API_KEY` (Bedrock bearer) | `MODEL_API_KEY` |
| `OPENAI_BASE_URL` | `MODEL_BASE_URL` |
| `MODEL_ID` | `MODEL_NAME` |

`OPENAI_API_KEY` is **not** an OpenAI Platform `sk-` key.

## 3. Run workshop Lab 1 (SDK)

```bash
pip install 'openai[bedrock]' aws-bedrock-token-generator
python scripts/workshop/openai_basic_response.py
```

Uses `OpenAI(provider=bedrock(endpoint="runtime"))` and your **AWS** credentials (same as the lab).

## 4. Run curl / OpenAI CLI labs

After `source refresh_bedrock_workshop_env.sh`:

```bash
curl -s "${OPENAI_BASE_URL}/responses" \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"${MODEL_ID}\", \"input\": \"Say hi in one sentence.\", \"store\": false}" | jq .
```

## 5. BeatIT backend

With the same shell (env vars loaded):

```bash
python scripts/workshop/verify_beatit_chat.py
# then restart FastAPI so it picks up MODEL_* from the environment
```

Assistant Copilot routes may still use the NVIDIA key pool (`MODEL_API_KEY_1`…); this path is the **generic intelligence** seam used by legacy agents.
