# M10 Contribution A11 — Persistence and restart semantics review

**Review date:** 2026-09-26
**Scope:** local files, SQLite stores, PostgreSQL, Valkey/Redis, and the
application process boundary.
**Change boundary:** documentation only. No application source, database,
container, or running service was modified. No service restart was performed.

## Verdict

**PARTIAL — local SQLite/file persistence is evidenced; external-store
durability and deployed-process restart are not release-proven.**

The repository has restart-safe SQLite store primitives and a local artifact
store that can be read by a separate process when the same filesystem is
retained. Case state and CareGuard state fall back to process-local memory when
Redis is unavailable. PostgreSQL is an optional CareGuard durability layer, not
the default store for the core BeatIT API. The observed Valkey container is
reachable but has no mounted data volume and has AOF disabled. The launcher
reported both managed services stopped, so an end-to-end API
write/restart/read test remains open.

## Storage map from source

| Surface | Configuration and implementation | Restart claim | Release boundary |
| --- | --- | --- | --- |
| Ensemble results | `BEATIT_ENSEMBLE_STORE=sqlite`; default `data/beatit-ensembles.sqlite3` (`python/hearttwin/storage/ensemble_store.py:141-146`) | File-backed and reopened per operation; `:memory:` is rejected | Durable only if the exact path is retained and backed up |
| Shadow Trial results | SQLite, sharing `BEATIT_ENSEMBLE_DB_PATH` by default (`shadow_trial_store.py:141-145`) | File-backed, immutable create-once records | Same SQLite backup boundary as ensembles |
| Missing Piece results | SQLite; `BEATIT_MISSING_PIECE_DB_PATH` can override the ensemble path (`missing_piece_store.py:156-158`) | File-backed and immutable | Override must be set consistently across processes |
| Uploaded artifacts | Local `ARTIFACT_ROOT`, default `data/artifacts`; optional S3 when `AWS_ENABLED=true` (`storage/factory.py:16-32`) | Local files survive a process restart if the root filesystem is retained | `put()` writes directly to the destination; atomic write/rename and backup/restore were not proven |
| Core case records | Redis when `REDIS_URL` is set and `HEARTTWIN_REDIS_MEMORY_ENABLED` is enabled; otherwise `_MEMORY_STORE` (`tools/storage.py:61-97`) | Redis-backed records can outlive the API process; fallback records are lost on restart | Redis retention/persistence and cross-process read were not exercised here |
| CareGuard staged state and audit cache | Namespaced Redis with a configured `CAREGUARD_REDIS_TTL_SECONDS` (default 86400); otherwise bounded `_FALLBACK` dictionary (`careguard/memory/redis_store.py:22-71`) | Redis keys are TTL-bound; fallback is process-local | PostgreSQL mirror is best-effort and must not be represented as active unless configured and reachable |
| CareGuard cases/audit/feedback | Optional PostgreSQL repository selected by `DATABASE_URL` (`careguard/db/repository.py:44-154`) | Intended to survive Redis TTL and API restart | Schema migration is best-effort at startup and an unavailable database does not block startup |

The FastAPI module loads `.env` on non-pytest import (`python/hearttwin/api.py:18-33`),
then constructs the SQLite stores at import time (`api.py:119-123`). A deployed
process must therefore retain the same environment and absolute data paths; a
different working directory or environment can silently select a different
SQLite file.

## Safe probes and exact evidence

All commands below ran from `/home/923873155/BeatIT`. Secrets and private URL
values were withheld. Probes were read-only except for the temporary-directory
probe, which wrote synthetic data under a deleted `TemporaryDirectory`.

### Local SQLite file

Read-only inspection command:

```bash
./.venv/bin/python - <<'PY'
import sqlite3
from pathlib import Path
path = Path('data/beatit-ensembles.sqlite3').resolve()
with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as connection:
    tables = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    counts = {table: connection.execute(
        f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] for table in tables}
    print({"path": str(path), "tables": tables, "row_counts": counts,
           "journal_mode": connection.execute('PRAGMA journal_mode').fetchone()[0],
           "foreign_keys": connection.execute('PRAGMA foreign_keys').fetchone()[0]})
PY
```

Observed:

```text
{'path': '/home/923873155/BeatIT/data/beatit-ensembles.sqlite3',
 'tables': ['missing_piece_results', 'shadow_trials', 'twin_ensembles'],
 'row_counts': {'missing_piece_results': 0, 'shadow_trials': 2, 'twin_ensembles': 4},
 'journal_mode': 'delete', 'foreign_keys': 0}
```

Filesystem evidence:

```text
-rw------- 221184 data/beatit-ensembles.sqlite3
no SQLite sidecar files (*.sqlite3-wal or *.sqlite3-shm)
```

The constructors create parent directories with mode `0700`, attempt to set
database files to `0600`, open a connection per operation, and set a five-second
SQLite timeout plus a 5000 ms busy timeout (`ensemble_store.py:65-80`; the
Shadow Trial and Missing Piece stores have the same protections). This supports
reopen and separate-process visibility, but does not provide backup, encryption,
foreign-key enforcement, or a deployed volume guarantee.

### Temporary separate-process proof

The synthetic probe created one SQLite database and one artifact root in a
temporary directory. A writer subprocess saved an ensemble, Shadow Trial, and
Missing Piece record and an artifact; a fresh reader subprocess reopened the
same paths.

Observed result:

```json
{"artifact": "synthetic-artifact", "db_mode": "0o600", "ensemble": {"kind": "synthetic", "persisted": true}, "missing_piece": {"completeness": {}, "dominant_uncertainty_drivers": [], "evidence_constraints": [], "evidence_ranking": [], "limitations": ["Synthetic restart probe."], "provenance": {"analysis_id": "probe-analysis", "assumptions": ["Synthetic fixture."], "ensemble_id": null, "model_version": "m8-missing-piece-v1", "ranking_method": "evidence-priority-score-v1", "sensitivity_method": "finite_difference", "shadow_trial_id": null, "source": "derived"}, "safety_disclaimer": "Educational cardiac simulation only. Not for diagnosis or treatment decisions. SIMULATION ONLY. DualBeat is not a medical device, does not provide medical advice, and all outputs are simulated educational estimates.", "sensitivities": [], "sensitivity_availability": {}, "target_metric": "stroke_volume_ml"}, "parent_mode": "0o700", "shadow_trial": {"status": "complete", "synthetic": true}}
```

This is direct cross-process evidence for the three SQLite tables and local
artifacts, not proof that a deployed API process uses the same paths.

Focused test command:

```bash
./.venv/bin/python -m pytest -q \
  python/hearttwin/tests/test_ensemble_store.py \
  python/hearttwin/tests/test_shadow_trial_store.py \
  python/hearttwin/tests/test_missing_piece_store.py \
  python/hearttwin/tests/test_redis_memory.py \
  python/hearttwin/tests/careguard/test_careguard_db.py
```

Observed result:

```text
40 passed in 1.05s
```

The tests cover store recreation, an ensemble separate-process read, immutable
Shadow Trial/Missing Piece records, rejection of `:memory:`, and unconfigured
PostgreSQL/Redis fallback behavior. They do not restart the deployed API.

### PostgreSQL container

Read-only container probes:

```bash
docker exec ghostrange-postgres-dev pg_isready -q
docker exec ghostrange-postgres-dev psql -U ghostrange -d ghostrange -Atqc \
  "SELECT current_database(), current_user, current_setting('server_version'), pg_is_in_recovery();"
docker exec ghostrange-postgres-dev psql -U ghostrange -d ghostrange -Atqc \
  "SELECT table_schema || '.' || table_name FROM information_schema.tables
   WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1;"
```

Observed:

```text
pg_isready exit=0
ghostrange|ghostrange|16.15|f
public.event_log
public.range_seq_counters
```

The container was healthy and had a writable mounted `/var/lib/postgresql/data`
volume. Docker metadata showed `restart_count=0` and restart policy `no` at the
time of review. The observed database did not contain the three tables expected
by the CareGuard migration (`careguard_cases`, `careguard_audit`, and
`careguard_feedback`). Therefore this probe proves a healthy PostgreSQL service,
not application-schema readiness or CareGuard persistence.

The current shell had `DATABASE_URL` unset. The private `.env` contains a
non-empty `DATABASE_URL` value, but its credential was not used or printed in
this review. The CareGuard migration is invoked only when `CAREGUARD_ENABLED`
mounts the router and catches migration exceptions without blocking startup
(`careguard/api.py:46-56`, `api.py:1334-1347`). A deployment must run and verify
the migration against its intended database rather than infer readiness from a
running PostgreSQL container.

### Valkey/Redis container

Read-only probes:

```bash
docker exec ghostrange-valkey-dev valkey-cli PING
docker exec ghostrange-valkey-dev valkey-cli DBSIZE
docker exec ghostrange-valkey-dev valkey-cli CONFIG GET appendonly
docker exec ghostrange-valkey-dev valkey-cli CONFIG GET save
docker exec ghostrange-valkey-dev valkey-cli INFO persistence
```

Observed:

```text
PONG
0
appendonly
no
save
3600 1 300 100 60 10000
rdb_saves:0
rdb_last_bgsave_status:ok
aof_enabled:0
```

Docker metadata showed:

```text
image=valkey/valkey:7-alpine
health=healthy
restart_count=0
restart_policy={"Name":"no","MaximumRetryCount":0}
mounts=(none)
```

This instance was reachable and empty, with RDB save rules configured but no
completed RDB save reported and no AOF. A container-layer database without a
mounted volume is not a release-grade persistence boundary: a container
recreation can discard it. No Redis/Valkey write, `SAVE`, `BGSAVE`, restart, or
delete operation was issued.

The application Redis client uses standard `redis.asyncio` and `REDIS_URL`
(`tools/redis_client.py:18-46`). Normal core case writes use `SET` without a
TTL (`tools/storage.py:68-69`); CareGuard writes use a default 86400-second TTL
(`careguard/memory/redis_store.py:52-60`). The code does not establish the
server's RDB/AOF policy, volume, backup, or restore contract.

### Application process boundary

The safe launcher probe was:

```bash
./deploy/beatit status
```

Observed:

```text
backend STOPPED
frontend STOPPED
```

An unrelated process was already listening on `127.0.0.1:8000`; GET requests to
the expected health routes returned HTTP 404. No service was stopped or
restarted to avoid changing shared runtime state. Consequently, this review did
not claim API-level write → process restart → read durability.

## Restart matrix

| Boundary | Evidence | Result |
| --- | --- | --- |
| Reopen SQLite store in the same process | Focused tests | PASS |
| Read SQLite records from a fresh process | Temporary synthetic probe and ensemble test | PASS |
| Read local artifact from a fresh process | Temporary synthetic probe | PASS |
| No-Redis core case fallback across processes | `tools/storage.py` uses module `_MEMORY_STORE` | EXPECTED LOSS; not durable |
| CareGuard fallback across processes | `redis_store.py` uses module `_FALLBACK` | EXPECTED LOSS; not durable |
| PostgreSQL service reachability | `pg_isready` and read-only `SELECT` | PASS for observed container only |
| CareGuard PostgreSQL schema | Catalog listing lacked expected tables | OPEN |
| Valkey reachability | `PING` returned `PONG` | PASS |
| Valkey data durability | No volume, AOF disabled, `rdb_saves:0` | OPEN / NOT PROVEN |
| API write, restart, and read | No launcher service was running; no restart performed | NOT RUN |
| Backup and restore | No backup/restore command was executed | NOT PROVEN |

## Gaps and release actions

1. Set absolute `BEATIT_ENSEMBLE_DB_PATH`, `BEATIT_MISSING_PIECE_DB_PATH`, and
   `ARTIFACT_ROOT` values on persistent mounted storage. Verify the values in
   the actual service environment after startup.
2. Decide which store is authoritative for each deployment. Do not describe
   local SQLite or in-process memory as shared durable state.
3. Provision the intended PostgreSQL database, run the idempotent CareGuard
   migration, and verify the three expected tables with a read-only catalog
   check. Treat best-effort migration failure as a readiness failure for any
   deployment that enables CareGuard durability.
4. Give Valkey/Redis an explicit persistent volume or managed persistence
   policy, authentication/network boundary, retention policy, and tested
   backup/restore procedure. Verify a synthetic key survives the actual
   service restart; do not use patient data for this test.
5. Run the deployed-process test: save one synthetic ensemble, Shadow Trial,
   Missing Piece record, artifact, and configured case record; restart the
   actual supervised service; read each record back and compare hashes.
6. Add a supervisor/health-gated restart contract. The current `nohup` launcher
   does not prove crash recovery, boot persistence, graceful drain, or
   rollback restoration.

**A11 release disposition: OPEN.** The local SQLite/file primitives are
credible for a synthetic single-host demo, but external-store durability and
the real service restart boundary remain unverified.
