# Rollback

1. Stop only the processes recorded by `./deploy/beatit down`.
2. Preserve logs under `.run/beatit/` and the configured data/artifact roots.
3. Restore the previously reviewed source tree or release archive.
4. Restore database/SQLite/artifact backups into an explicitly verified target.
5. Run `./scripts/demo-preflight.sh`, `./deploy/beatit up`, and both readiness
   and system-check endpoints.
6. Re-run the deterministic seed only when the rollback target intentionally
   uses the canonical demo fixture.

Do not run recursive deletion against the repository, `/home`, `/usr/data`, or
the configured artifact root during rollback.
