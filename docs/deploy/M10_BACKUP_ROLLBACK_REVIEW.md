# M10 Backup and Rollback Safety Review

**Review date:** 2026-09-26
**Scope:** `deploy/beatit`, deployment and rollback documentation, local
persistence paths, and the observed host runtime. No destructive command was
run and no service was stopped, restarted, or modified.

## Decision

**PARTIAL — rollback is documented, but backup and restore are not release-proven.**

The repository has a bounded local launcher and a manual rollback outline. It
does not contain an automated backup job, a database dump/restore procedure
that has been exercised, a Redis/Valkey snapshot policy, or a verified restore
artifact. A production release must supply and test those controls before it
can claim recoverability.

## Evidence collected

All observations below were read-only unless explicitly noted as a syntax
check.

| Check | Exact evidence | Result |
| --- | --- | --- |
| Launcher syntax | `bash -n deploy/beatit` returned `PASS` | PASS |
| Launcher runtime state | `.run/beatit` was absent; no launcher PID or log files were present | No local launcher state to restore |
| Service inventory | `docker ps` showed `ghostrange-postgres-dev` (`postgres:16-alpine`, healthy) and `ghostrange-valkey-dev` (`valkey/valkey:7-alpine`, healthy) | Running infrastructure is outside `deploy/beatit` |
| Published data services | PostgreSQL `0.0.0.0:5432->5432/tcp`; Valkey `0.0.0.0:6379->6379/tcp` | Exposure and backup ownership require deployment hardening |
| Disk headroom | `/` 3.6T total, 743G available, 79% used; `/usr/data` 2.7T total, 2.2T available, 22% used | Capacity exists, but no backup destination or retention is defined |
| SQLite file | `data/beatit-ensembles.sqlite3`, mode `-rw-------`, size `221184` bytes | Local file exists; no backup copy was found |
| Artifact root | `data/artifacts` was absent | No local artifact set was available to restore |
| Demo state | `data/demo/state.json`, mode `-rw-r--r--`, size `584` bytes | Regenerable demo metadata, not a durable application backup |
| Backup inventory | Search of `deploy`, `scripts`, `docs/release`, and `docs/deploy` found no `pg_dump`, `pg_restore`, `redis-cli`, `valkey-cli`, RDB/AOF, or archive backup automation | NOT IMPLEMENTED |
| Repository backup-like files | Outside dependencies, only `docs/release/ROLLBACK.md` matched the bounded backup/restore filename search | No checked-in backup or dump artifact |

The host-level service and disk observations agree with
[SERVER_AUDIT.md](./SERVER_AUDIT.md), but that audit is inventory evidence,
not proof that either container is used as the application's authoritative
store or that its data can be restored.

## `deploy/beatit` safety audit

### Safe behavior observed

- The launcher derives `repo_root` from its own location and keeps PID/log
  state under `.run/beatit` (`deploy/beatit:4-11`).
- `down` targets only the PIDs recorded for `frontend` and `backend`,
  removes those PID files, and does not enumerate or kill arbitrary processes
  (`deploy/beatit:26-35`). It does not remove application data.
- `up` binds FastAPI and Next.js to loopback, performs a production frontend
  build, and checks the API liveness route plus the frontend root before
  reporting readiness (`deploy/beatit:38-59`).
- `status` checks recorded PID files using `kill -0` and prints state
  (`deploy/beatit:15-24`).

### Recovery and rollback gaps

- `restart` is a stop-then-start sequence (`deploy/beatit:62-67`), not an
  atomic or health-gated replacement. A failed build or startup can leave the
  service unavailable.
- On startup timeout, `up` prints the log location and status but does not
  automatically clean up any process or PID file it may have created
  (`deploy/beatit:50-59`). Operators must inspect and recover manually.
- PID files are trusted. The script checks only whether the numeric PID exists;
  it does not verify command identity before sending `kill` in
  `down` (`deploy/beatit:13`, `deploy/beatit:29-32`). A stale PID file
  combined with PID reuse is a residual kill-safety risk.
- The launcher does not pin a release archive, record a source revision, make
  a backup, verify a backup checksum, restore a database, or run a post-restore
  data-integrity check.
- It manages neither PostgreSQL nor Valkey. Container restart, volume
  retention, authentication, snapshotting, and restore ownership are not
  encoded in this launcher.

## Persistence and backup boundaries

- The default ensemble provider is file-backed SQLite at
  `data/beatit-ensembles.sqlite3`; the path can be overridden by
  `BEATIT_ENSEMBLE_DB_PATH`
  (`python/hearttwin/storage/ensemble_store.py:141-146`).
- The Shadow Trial store uses the same SQLite path and requires the SQLite
  provider (`python/hearttwin/storage/shadow_trial_store.py:141-145`).
  The Missing Piece store also defaults to that path unless
  `BEATIT_MISSING_PIECE_DB_PATH` is set
  (`python/hearttwin/storage/missing_piece_store.py:156-158`). One file
  therefore contains multiple durable feature records and must be backed up as
  one consistency boundary.
- SQLite creates its parent directory with mode `0700` and attempts to set the
  database file to `0600` (`ensemble_store.py:65-76`; equivalent handling
  is present in the Shadow Trial and Missing Piece stores). The observed
  database mode was `0600`. This protects the live file locally but does not
  create a backup or establish backup access controls.
- Uploaded artifacts use local `ARTIFACT_ROOT` (`data/artifacts`) by default
  or the optional S3 adapter when `AWS_ENABLED=true`
  (`python/hearttwin/storage/factory.py:16-32`). The deployment README calls
  this an operator choice, but provides no retention, versioning, or restore
  test (`deploy/README.md:13-15`).
- Case state uses Redis when configured and an in-process dictionary otherwise
  (`python/hearttwin/tools/storage.py:71-97`). The fallback is explicitly
  lost on process restart; it cannot be treated as recoverable persistence.
- `.gitignore` excludes the SQLite database and artifact root
  (`.gitignore:65-73,92-94`). Git therefore cannot restore those runtime
  records.

## Documented restore path

The current documentation provides an operator outline:

1. Before an upgrade, copy the configured local artifact root and SQLite files
   to a restricted backup location (`docs/deploy/DEPLOYMENT.md:35-45`).
2. Stop only the recorded application processes and preserve logs/data
   (`docs/release/ROLLBACK.md:1-5`).
3. Restore the previously reviewed source tree or release archive, then restore
   database/SQLite/artifact backups into an explicitly verified target
   (`docs/release/ROLLBACK.md:5-6`).
4. Run `./scripts/demo-preflight.sh`, `./deploy/beatit up`, readiness, and
   system-check validation (`docs/release/ROLLBACK.md:7-10`).
5. Do not recursively delete the repository, `/home`, `/usr/data`, or the
   configured artifact root (`docs/release/ROLLBACK.md:12-13`).

This is a safe procedure outline, not a tested restore run: the documents do
not identify a concrete backup location, retention period, encryption method,
SQLite consistency method, PostgreSQL dump format, Valkey persistence mode,
backup checksum manifest, or rollback owner.

## Required release follow-up

Before marking backup/rollback complete, the deployment owner should provide
and test, without exposing secrets or patient data:

- a release archive or immutable source identifier and checksum;
- a restricted, off-host backup target with retention and encryption policy;
- an application-consistent SQLite backup procedure for the shared database;
- an explicit PostgreSQL backup/restore plan if PostgreSQL is authoritative;
- a Valkey/Redis persistence or rebuild policy for configured case state;
- artifact backup/versioning and restore verification;
- a dry-run restore into an isolated target, followed by liveness, readiness,
  system-check, record-count, and checksum checks;
- a documented RTO/RPO and an operator-owned rollback command sequence;
- a PID identity check and cleanup path for failed launcher starts.

## Final assessment

**Backup:** NOT PROVEN. Manual copy is mentioned, but no automated or tested
backup exists in this repository.

**Rollback:** PARTIALLY DOCUMENTED. The source/data preservation boundaries and
post-restore checks are described, and `deploy/beatit` avoids broad deletion;
the actual restore and service recovery path has not been exercised.

**Release gate:** DO NOT CLAIM RECOVERABLE PRODUCTION DEPLOYMENT until a
realistic backup is created, restored in isolation, and the resulting BeatIT
health and deterministic system checks pass.
