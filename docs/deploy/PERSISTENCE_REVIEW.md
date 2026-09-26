# M10 A04 — Persistence and restart review

**Date:** 2026-09-26
**Scope:** SQLite stores, filesystem artifacts, in-process fallbacks, and
`deploy/beatit` lifecycle behavior.
**Change boundary:** This contribution changes documentation only. No
production code, data store, or running service was modified.

## Executive result

The persistence primitives are restart-capable when their configured files or
external provider remain available:

- Ensemble, Shadow Trial, and Missing Piece records use file-backed SQLite by
  default. Their focused tests pass, including subprocess/reopen coverage.
- Uploaded artifacts use `ARTIFACT_ROOT` and survive a new Python process when
  the same filesystem is retained.
- Case state and CareGuard memory intentionally fall back to bounded
  process-local dictionaries when Redis is unavailable. That state is not
  expected to survive a process restart.
- The current launcher cannot complete `up` or `restart`: it invokes
  `next build` from the repository root instead of `web/`. The standalone build
  from `web/` succeeds, so this is a launcher integration defect, not evidence
  of a frontend build failure.

**Release conclusion: NOT READY for self-host deployment until the launcher
working-directory defect is corrected and a real persistent-store restart is
verified through the deployed process path.**

## Storage inventory

| Surface | Default provider | Restart behavior | Evidence / boundary |
|---|---|---|---|
| Ensemble results | SQLite file `data/beatit-ensembles.sqlite3` | Durable across reopen and separate processes if the file path is retained | `SQLiteEnsembleStore` opens a connection per operation; focused tests and a subprocess probe passed. |
| Shadow Trial results | SQLite file, sharing `BEATIT_ENSEMBLE_DB_PATH` by default | Durable across reopen/process restart; immutable create-once semantics | `test_shadow_trial_store.py` and `test_shadow_trial_api.py` cover reopen/identity behavior. `:memory:` is rejected. |
| Missing Piece analyses | SQLite file; `BEATIT_MISSING_PIECE_DB_PATH` overrides the ensemble path | Durable across reopen/process restart if the file is retained | `test_missing_piece_store.py` passed; `:memory:` is rejected. |
| Uploaded artifacts | Local filesystem under `ARTIFACT_ROOT` unless AWS/S3 is enabled | Durable across process restart if the same root filesystem is mounted and readable | Direct subprocess probe retrieved a file written by a separate process. Local writes do not have an atomic temp-file/rename protocol. |
| Case records | Redis when `REDIS_URL` is configured and memory is enabled; otherwise `_MEMORY_STORE` | Redis survives process restart subject to Redis retention; local fallback is process-local and is lost on restart | Direct probe returned the record in the writer process and `None` in a fresh process. A configured-but-broken Redis error is not silently converted to memory. |
| CareGuard memory/audit keys | Namespaced Redis when enabled; otherwise bounded `_FALLBACK` dictionary | Redis depends on configured TTL; fallback is explicitly request/process scoped and not durable | `redis_store.py` documents and exposes `in_process_fallback`; no cross-process durability was claimed or tested here. |
| Case-memory index | In-memory index with optional Redis persistence path | Must be treated as non-durable unless the Redis path is configured and reachable | Offline tests cover the fallback; a live Redis restart/retention test was not run in this review. |

At API import time, the ensemble, Shadow Trial, and Missing Piece stores are
constructed from environment variables. A deployment must therefore set the
same database path before every process starts and must mount that path on
persistent storage. The default path is relative to the process working
directory; changing the working directory changes which database file is used.

## Evidence collected

All commands below were run from `/home/923873155/BeatIT`. The project virtual
environment was used for Python checks.

### SQLite and memory tests

Command:

```bash
./.venv/bin/python -m pytest -q \
  python/hearttwin/tests/test_ensemble_store.py \
  python/hearttwin/tests/test_shadow_trial_store.py \
  python/hearttwin/tests/test_missing_piece_store.py \
  python/hearttwin/tests/test_redis_memory.py \
  python/hearttwin/tests/test_intelligence_runtime.py
```

Observed result:

```text
45 passed in 1.19s
```

The ensemble test file includes a separate-process writer/reader test. The
Shadow Trial and Missing Piece tests cover reopen behavior and reject
`:memory:` databases, which would not survive a process restart.

### Direct filesystem and process-boundary probe

The following probe wrote through `LocalArtifactStore`, read the artifact from
a fresh subprocess, wrote case state through the no-Redis fallback, and read it
from another fresh subprocess:

```bash
./.venv/bin/python - <<'PY'
import asyncio, os, subprocess, sys, tempfile
from pathlib import Path
from python.hearttwin.storage.local import LocalArtifactStore
from python.hearttwin.tools.storage import get_case, store_case

env = os.environ.copy()
env.pop("REDIS_URL", None)
env["HEARTTWIN_REDIS_MEMORY_ENABLED"] = "true"

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory) / "artifacts"
    asyncio.run(LocalArtifactStore(root).put("case-1/report.txt", b"persisted-artifact"))
    result = subprocess.run(
        [sys.executable, "-c", "import asyncio,sys; from python.hearttwin.storage.local import LocalArtifactStore; print(asyncio.run(LocalArtifactStore(sys.argv[1]).get('case-1/report.txt')).decode())", str(root)],
        check=True, capture_output=True, text=True, env=env,
    )
    print(result.stdout.strip())

async def check_memory():
    await store_case("restart-probe", {"status": "in_process"})
    print(await get_case("restart-probe"))
    result = subprocess.run(
        [sys.executable, "-c", "import asyncio; from python.hearttwin.tools.storage import get_case; print(asyncio.run(get_case('restart-probe')))"],
        check=True, capture_output=True, text=True, env=env,
    )
    print(result.stdout.strip())

asyncio.run(check_memory())
PY
```

Observed result:

```text
persisted-artifact
{'status': 'in_process'}
None
```

This is direct evidence that the local artifact root is process-independent
when retained, while the no-Redis case fallback is not.

### SQLite cross-process and file permissions

The separate-process probe created a nested SQLite path, saved an ensemble in
one process, and read it in another. Observed result:

```text
{"sqlite_cross_process": {"source": "writer", "value": 42}, "database_mode": "0o600", "parent_mode": "0o700"}
```

The SQLite constructors create the parent directory with mode `0700` and set
the database file to `0600` where the host filesystem permits it. This does not
replace host-level backup, encryption-at-rest, ownership, or disk monitoring.

### Launcher syntax and status

Commands:

```bash
bash -n deploy/beatit
deploy/beatit status
```

Observed result:

```text
bash -n deploy/beatit: PASS
backend STOPPED
frontend STOPPED
```

The `down` path reports that it targets only PIDs recorded under
`.run/beatit`. No existing service was stopped during this review.

### Isolated launcher lifecycle attempt

To avoid the existing services on ports 8000 and 3001, the launcher was
invoked with `BEATIT_API_PORT=18765` and `BEATIT_WEB_PORT=18766`:

```bash
BEATIT_API_PORT=18765 BEATIT_WEB_PORT=18766 ./deploy/beatit up
BEATIT_API_PORT=18765 BEATIT_WEB_PORT=18766 ./deploy/beatit restart
BEATIT_API_PORT=18765 BEATIT_WEB_PORT=18766 ./deploy/beatit down
```

Observed result for both `up` and `restart`:

```text
> Build error occurred
Error: > Couldn't find any `pages` or `app` directory. Please create one under the project root
```

The launcher executes the build as:

```bash
cd "$repo_root"
"$repo_root/web/node_modules/.bin/next" build
```

Because the application is under `web/`, Next.js searches the repository root
and exits before `uvicorn` or `next start` is launched. The subsequent launcher
status remained `backend STOPPED` and `frontend STOPPED`. `down` completed
without targeting an unrelated process.

For comparison, the owning-directory build was run directly:

```bash
(cd web && ./node_modules/.bin/next build)
```

Observed result: exit code `0`, with the expected App Router routes generated.

### Existing-service preflight boundary

Command:

```bash
deploy/beatit preflight
```

Observed result: Python, Node, curl, fixtures, and the model manifest were
ready, but the HTTP checks returned `404` for `/api/health/live`,
`/api/health/ready`, `/api/v1/system-check`, and `/api/v1/models/status`.
`deploy/beatit preflight` targets port 8000, where an already-running service
responded; it does not prove the failed isolated launcher instance was healthy.

## Restart matrix

| Scenario | Result | Confidence |
|---|---|---|
| Reopen SQLite store in the same Python process | Passed by focused tests | High for store primitive |
| Read SQLite record from a separate Python process | Passed by test and direct probe | High for retained file path |
| Read local artifact from a separate Python process | Passed by direct probe | High for retained artifact root |
| Re-read case state after process restart with Redis unset | Correctly absent (`None`) | High; fallback is intentionally non-durable |
| CareGuard fallback after process restart | Not run as a subprocess test in this review | Behavior is documented as non-durable; live boundary remains unverified |
| API restart with default database path and existing records | Not run end-to-end | Blocked by launcher build defect |
| Launcher `up` / `restart` / frontend readiness | Failed before process start | P0 release blocker |
| Reverse proxy plus restart | Not run | nginx example is configuration only; no live proxy was exercised |
| Redis-backed restart and TTL retention | Not run | Requires a configured test Redis and explicit retention window |
| S3 artifact restart | Not run | Requires AWS credentials and a controlled bucket |

## Risks and unverified boundaries

1. **Launcher working directory:** `deploy/beatit` must build and start Next.js
   from `web/`. Until corrected, the documented self-host path is not
   runnable.
2. **Relative SQLite path:** the default `data/beatit-ensembles.sqlite3`
   depends on the process working directory. Use an absolute path in a
   service definition and back up that exact file.
3. **Artifact atomicity:** `LocalArtifactStore.put` writes directly to the
   destination. A crash or concurrent reader during a write was not tested;
   there is no verified temporary-file/rename protocol in this review.
4. **Fallback loss is intentional:** no-Redis case state and CareGuard fallback
   memory are not a backup mechanism. A readiness check must not present them as
   durable patient/session state.
5. **PID ownership:** `down` kills a recorded PID if it is alive, but the
   launcher does not verify the PID still belongs to the expected BeatIT
   command. PID reuse and stale PID-file handling were not stress-tested.
6. **Process supervision:** `nohup` is not a service supervisor. Crash restart,
   boot persistence, graceful drain, log rotation, and health-driven restart
   were not verified.
7. **Deployment storage:** no container, reverse proxy, or deployed host was
   exercised in this contribution. Persistent volumes, permissions, backup,
   restore, and disk-full behavior remain deployment work.
8. **Data sensitivity:** file and SQLite mode checks are local observations;
   they do not establish encryption, authenticated multi-user isolation, or
   production compliance.

## Required follow-up before release

- Correct the launcher's Next.js working directory and verify `up`, `restart`,
  readiness, and `down` on isolated ports.
- Set absolute persistent paths for SQLite and artifacts in the deployment
  environment.
- Run a deployed-process restart test: write a synthetic record, restart the
  actual service, retrieve it, and verify the same artifact root/database file
  was used.
- Exercise reverse proxy routing, persistence backup/restore, disk-full/error
  handling, and Redis-backed retention with synthetic data only.
- Add ownership checks or a supervisor contract before treating the launcher as
  a production process manager.
