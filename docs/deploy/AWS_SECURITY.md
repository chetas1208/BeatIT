# AWS deployment security result

Date: 2026-09-26 UTC

## Status

**NOT CERTIFIED.** No public deployment was made.

- AWS credentials and secret values were not printed or written to the
  repository.
- No restricted or patient-level dataset was uploaded.
- No `.env` file was uploaded.
- The local VISTA checkpoint and filesystem remained local.
- No Cloudflare tunnel was started.

The running local VISTA service currently has endpoint-secret enforcement
disabled and accepts unauthenticated requests on its local listener. It must be
restarted with `REQUIRE_ENDPOINT_SECRET=true`, a reduced upload limit, hardened
callback policy, and restricted CORS before any tunnel is started. Because this
gate failed, exposing the service—even through a temporary Quick Tunnel—was
intentionally refused.

The BeatIT backend currently configures wildcard CORS. A public deployment must
replace that with the exact frontend origin and add focused tests before
release.

