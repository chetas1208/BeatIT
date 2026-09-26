# M10 A21 — Data Retention, Backup, and Privacy Review

**Review date:** 2026-09-26  
**Scope:** application data stores, runtime traces, uploaded artifacts, backup
and restore boundaries, deletion/retention controls, and privacy safeguards.  
**Change boundary:** documentation only. No production code, data store, or
running service was modified.

## Decision

**OPEN / NOT READY for public or clinical-data deployment. Synthetic demo use
only.**

The repository contains restart-capable storage primitives, but it does not
yet provide a release-proven backup and restore process, a single retention
policy, or complete application-level deletion and access-control boundaries.
Local file permissions and redaction tests reduce risk; they do not establish
encryption, tenant isolation, provider deletion, or regulatory compliance.

## Storage and retention inventory

| Surface | Current behavior | Retention / deletion finding | Recovery boundary |
| --- | --- | --- | --- |
| Ensemble, Shadow Trial, Missing Piece | File-backed SQLite by default. The shared ensemble path is `BEATIT_ENSEMBLE_DB_PATH`; Missing Piece can override it with `BEATIT_MISSING_PIECE_DB_PATH`. | No application TTL, purge job, or case-level delete workflow was found. Records remain until an operator removes or replaces the database. | Reopen and cross-process tests pass when the exact file is retained. No exercised backup, checksum manifest, or restore drill exists. |
| Uploaded artifacts | Local `ARTIFACT_ROOT` by default; optional S3 adapter when `AWS_ENABLED=true`; legacy Vercel Blob path when its token is configured. | No artifact delete endpoint, expiration policy, lifecycle rule, versioning policy, or provider-side erasure verification was found. Local writes are direct destination writes, not a verified atomic temp-file/rename sequence. | Local artifacts survive a process restart only when the same root filesystem is mounted. S3/Blob recovery depends on external bucket/provider controls not defined here. |
| Case records | Redis when configured; otherwise module-level `_MEMORY_STORE`. | `store_case` does not set an expiry. The no-Redis fallback disappears on process restart and is not a backup. No user-facing case deletion route was found in the audited API. | Redis restart and retention were not tested. A fresh process correctly does not see a no-Redis case record. |
| Case-memory index | Always kept in process memory; best-effort Redis copy when configured. | Redis writes use ordinary `SET`/set membership without an application TTL or purge workflow. Similar-case summaries may therefore outlive the originating case unless the operator cleans the namespace. | Treat as non-durable unless Redis persistence and backup are separately configured and tested. |
| CareGuard case/audit/feedback | Redacted Redis namespace with a configurable TTL; when Postgres is configured, audit events are mirrored to durable Postgres tables. | Redis default TTL is 86,400 seconds and bounded to 60 seconds–7 days. The Postgres mirror is durable, but no retention or purge migration was found; Redis expiry therefore does not remove the Postgres copy. | Postgres survives Redis TTL only when configured and healthy. Postgres backup/restore is outside the BeatIT launcher and was not exercised. |
| Local trace fallback / SSE | Traces and run metadata are held in process memory. SSE resumes only from the in-process local list. | No retention bound, delete operation, or restart persistence exists for the local trace store. External Weave retention is provider-controlled and not established by this repository. | Traces are lost on process restart in local mode. A Weave URL is not a backup contract. |
| Demo state | `data/demo/state.json` contains synthetic fixture hashes and release metadata. | Regenerable demo metadata, not a customer-data backup. `scripts/reset-demo.sh` removes this explicit file only. | Recreated by `scripts/seed-demo.sh`; this does not restore application records or uploaded artifacts. |

The existing persistence review provides the direct restart evidence: SQLite
and retained local artifacts were readable from a fresh process, while the
no-Redis case fallback returned `None` after the writer process exited
([PERSISTENCE_REVIEW.md](../../deploy/PERSISTENCE_REVIEW.md)). The backup review
found no automated `pg_dump`, `pg_restore`, Redis/Valkey snapshot, archive
backup, or verified restore artifact
([M10_BACKUP_ROLLBACK_REVIEW.md](../../deploy/M10_BACKUP_ROLLBACK_REVIEW.md)).

## Backup and recovery assessment

### Confirmed

- SQLite constructors use restrictive local modes where supported: parent
  directory `0700` and database file `0600` were observed in the persistence
  probe.
- The deployment documentation identifies the SQLite and artifact paths and
  warns operators to copy them before upgrades.
- `docs/release/ROLLBACK.md` describes a bounded manual rollback and does not
  instruct operators to recursively delete broad directories.
- `deploy/beatit down` targets only recorded application PIDs and does not
  remove application data.

### Not release-proven

- No application-consistent SQLite backup command or restore test exists for
  the shared database containing multiple feature stores.
- No ownership, persistence mode, snapshot schedule, TTL policy, or restore
  test is encoded for Redis/Valkey case state or case-memory data.
- No PostgreSQL dump/restore procedure, backup destination, or purge procedure
  is encoded for the optional CareGuard durable mirror.
- No artifact backup manifest, checksum inventory, encryption-at-rest proof,
  off-host destination, or provider deletion proof exists.
- No deployed restart test has written synthetic data, restarted the actual
  service, and verified that the same database and artifact root were used.
- The launcher is not a backup system or a process supervisor. Its documented
  rollback remains an operator procedure, not a tested recovery control.

## Privacy and data-flow boundaries

### Controls that are present

- `LocalArtifactStore` resolves keys beneath `ARTIFACT_ROOT` and rejects path
  traversal.
- Uploads allowlisted by content type are capped at 200 MiB, although the
  request body is read into memory before the size check.
- Trace sanitization redacts configured PII keys, byte payloads, obvious SSN,
  email, long-ID, and date patterns, trims arrays, and avoids raw uploaded
  content. File metadata can still include file IDs, filenames, content types,
  and sizes.
- CareGuard de-identification tests cover identifier removal, relative dates,
  text redaction, and opaque IDs. CareGuard audit events are structured and
  redacted before Redis/Postgres writes.
- Server-only secrets are intended to remain outside `NEXT_PUBLIC_*` browser
  variables, as described in the self-hosting documentation.

### Open privacy risks

- Case and trace routes have no demonstrated authentication, authorization, or
  tenant isolation. Possession of a case identifier is not an acceptable
  production access boundary.
- A case can reference an uploaded artifact, but the audited API inventory did
  not find a corresponding application-level delete operation that removes
  both the reference and stored bytes from every configured backend.
- Redaction is pattern/key based, not a proof that arbitrary uploaded text,
  filenames, model prompts, or provider logs contain no identifiers.
- External Weave, model, S3, Blob, Redis, and Postgres providers each have
  independent logging, retention, access, and deletion behavior. The repo does
  not configure or verify their data-residency, encryption, legal-hold, or
  erasure settings.
- Local SQLite and artifact permissions are host observations only. They do
  not establish encryption at rest, encrypted backups, restricted operator
  access, or protection from a compromised host.
- The current no-Redis fallback is convenient for local operation but silently
  changes durability semantics by making case data process-local. Readiness
  and release documentation must expose this as a limitation, not describe it
  as recoverable persistence.
- A retention policy must account for duplicate copies: live stores, Redis
  snapshots, PostgreSQL audit rows, SQLite backups, artifact backups, local
  traces, Weave traces, provider logs, and operator exports.

## Required release controls

Before accepting non-synthetic or public deployment, the release owner must
define and verify:

1. A data classification and retention table for every store, including a
   maximum lifetime, deletion trigger, legal-hold exception, and owner.
2. An authenticated, authorized case boundary with tenant isolation and an
   auditable delete/export workflow for case metadata, artifacts, traces,
   Redis keys, SQLite rows, Postgres rows, backups, and external providers.
3. A restricted off-host backup target with encryption, retention, rotation,
   immutable source/release identifiers, and checksum manifests.
4. Consistent backup procedures for the shared SQLite file, Redis/Valkey,
   optional Postgres, and the configured artifact backend. Backups must be
   taken from quiesced or application-consistent state.
5. An isolated restore drill using synthetic data that verifies row counts,
   artifact hashes, case references, trace boundaries, and
   `/api/v1/system-check` after restore.
6. A restart and expiry drill for every configured backend, including proof
   that expired Redis data is not still available through Postgres, backups,
   local traces, or provider consoles.
7. Provider-specific privacy review for Weave, model endpoints, S3/Blob,
   Redis, and Postgres before any identifiable data is permitted.
8. Upload streaming/quotas, request limits, and failure cleanup so rejected or
   interrupted uploads cannot leave untracked retained bytes.

## Verification record

| Check | Result |
| --- | --- |
| Read-only storage and deployment source audit | PASS; inventory recorded above |
| SQLite reopen and separate-process evidence | PASS at primitive level; see linked persistence review |
| Local artifact separate-process evidence | PASS at primitive level; no deployed-volume proof |
| No-Redis case restart behavior | PASS for intentional loss; not durable |
| CareGuard de-identification/redaction tests | PASS for covered fixtures; not arbitrary-content proof |
| Backup/restore drill | NOT RUN / no implemented release procedure |
| Retention and deletion drill across all backends | NOT RUN / no unified policy |
| Public authenticated access and tenant-isolation test | NOT PROVEN |
| Production privacy/compliance decision | FAIL; synthetic demo only |

## Final status

**M10 data retention gate: INCOMPLETE.** The deterministic demo may use
synthetic fixtures and the documented local reset path. Do not claim durable
recovery, complete deletion, privacy compliance, or suitability for clinical or
identifiable data until the controls above are implemented and exercised.
