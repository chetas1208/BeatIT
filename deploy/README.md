# BeatIT deployment

This directory contains deployment guidance rather than provider-specific
infrastructure. A self-hosted deployment runs:

- the Next.js frontend;
- the FastAPI application;
- PostgreSQL and Redis when durable persistence is needed;
- a reverse proxy for frontend, API, CopilotKit, and trace SSE routes; and
- an OpenAI-compatible model endpoint selected through server-only `MODEL_*`
  variables.

Copy the root `.env.example` to a private deployment environment, replace all
placeholders, and keep credentials out of the repository. Use local artifact
storage by default or set `AWS_ENABLED=true` with a configured S3 bucket.
