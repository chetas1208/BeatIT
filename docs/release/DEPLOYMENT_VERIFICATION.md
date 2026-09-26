# M10.5 Deployment Verification

Verified locally on alternate ports:

1. `deploy/beatit up` builds from `web/` and starts FastAPI/Next.js on
   loopback.
2. Liveness, readiness, system-check, models-status, frontend root, and demo
   preflight return success.
3. `deploy/beatit down` stops only recorded PIDs and releases the ports.

Not verified: nginx/Caddy installation, TLS, public hostname, external
database/Redis, hosted restart, or remote deployment.
