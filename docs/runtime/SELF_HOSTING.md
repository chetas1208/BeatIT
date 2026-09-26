# BeatIT self-hosting

Run the frontend and FastAPI backend behind a reverse proxy. Configure the
frontend with `NEXT_PUBLIC_API_BASE` and the backend with provider-neutral model
variables. PostgreSQL and Redis are optional infrastructure choices for the
deployment; the deterministic cardiac engine and local fallbacks do not require
an external model endpoint.

Recommended boundary:

```text
browser -> reverse proxy -> Next.js frontend
                       -> FastAPI /api/v1, /api/intelligence/status, and /copilotkit
FastAPI -> deterministic cardiac engine
        -> optional provider-neutral model endpoint
        -> local artifacts or optional S3
```

The Next.js `/api/copilotkit` route remains server-side and uses the same
provider-neutral model variables. REST calls and the trace SSE stream remain
behind the reverse proxy; no model or storage credential is sent to the
browser.

Keep `.env` server-side, rotate deployment credentials independently, and never
copy model or AWS secrets into browser-exposed `NEXT_PUBLIC_*` variables.
