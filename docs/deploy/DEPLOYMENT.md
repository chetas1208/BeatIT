# BeatIT self-host deployment

The verified local/self-host path uses the host's Python and Next.js runtimes,
with PostgreSQL/Valkey managed separately when required. This avoids claiming a
container image that has not been built and exercised. Keep the app processes
on loopback and place nginx or Caddy in front of them.

## Operator path

```bash
cp .env.example .env
# Set only the integrations you actually operate; keep secrets out of Git.
./scripts/demo-preflight.sh
./deploy/beatit up
./deploy/beatit status
```

The launcher builds the production frontend, starts FastAPI on `127.0.0.1:8000`
and Next.js on `127.0.0.1:3001`, records only its own PIDs under `.run/beatit`,
and checks `/api/health/live` plus the frontend root. Override ports with
`BEATIT_API_PORT` and `BEATIT_WEB_PORT`.

Use [`nginx.conf.example`](../../deploy/nginx.conf.example) as the reverse
proxy starting point. Add TLS through the host's certificate manager; the
example intentionally does not invent certificates or a public hostname.

## Health

- `/api/health/live`: process liveness only.
- `/api/health/ready`: deterministic core and storage readiness plus optional
  language/Weave/Redis/VISTA degradation.
- `/api/v1/system-status`: operator summary with non-secret model availability.
- `/api/v1/system-check`: deterministic end-to-end golden-case check.

## Restart and rollback

```bash
./deploy/beatit restart
./deploy/beatit down
```

Before upgrades, copy the configured local artifact root and SQLite files to a
restricted backup location. Roll back by restoring the previous source tree and
restarting the recorded processes; never delete a broad data directory as part
of rollback.
