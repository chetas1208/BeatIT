# Security — Bedrock campaign

- Secrets only in `.env` / host env — never in repo or API JSON.
- `/api/intelligence/status` exposes role **model IDs** only, not tokens.
- Bearer rotation via `scripts/refresh_bedrock_model_key.py` from IAM session.
- `weave_trace.py` sanitizer remains mandatory for trace payloads.
- No `NEXT_PUBLIC_*` AWS credentials.

Historical NVIDIA docs are non-authoritative for runtime security.
