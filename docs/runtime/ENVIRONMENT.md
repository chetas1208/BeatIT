# BeatIT environment variables

`.env.example` contains fake placeholders only. Copy it to a private `.env` and
replace values in the server environment. `.env.example` is intentionally not
ignored; `.env` and all other `.env.*` files are ignored.

Core model variables are `MODEL_*`. `OPENAI_*` configuration is optional and
only activates the genuine OpenAI adapter when `OPENAI_ENABLED=true`. AWS S3 is
optional and disabled by default; local artifacts are the default.

Do not define `NEXT_PUBLIC_MODEL_API_KEY`, `NEXT_PUBLIC_OPENAI_API_KEY`, or
`NEXT_PUBLIC_AWS_SECRET_ACCESS_KEY`. The backend status endpoint returns no
secret values or fragments.

The existing per-agent `OPENAI_MODEL_*` settings remain supported for backward
compatibility, but provider transport now passes through the central
`IntelligenceProvider` interface.
