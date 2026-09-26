# M10 Upload, Path, and File-Handling Review

**Contribution:** A17
**Scope:** API upload routes, filename/path handling, artifact storage, and request-size validation
**Review date:** 2026-09-26 UTC
**Production-code changes:** none
**Disposition:** **OPEN / FAIL** — synthetic-demo-only; upload hardening is not ready for a public or patient-data deployment.

## Method and route inventory

This review used source inspection, focused `TestClient` probes, the existing
storage tests, and the focused API/runtime test modules. No uploaded content,
credentials, or host secrets were printed.

| Surface | Current behavior | Assessment |
|---|---|---|
| `POST /api/v1/cases/{case_id}/files` | Accepts allowlisted types plus any `image/*` or `video/*`; reads the complete multipart part; checks a 200 MiB cap afterward; stores under a generated UUID. | Cap exists, but enforcement is too late and MIME is client-controlled. |
| `POST /api/v1/ecg/diagnose` | Accepts CSV by MIME or `.csv` suffix; reads the complete body; checks a 50 MiB cap afterward. | Specialized cap exists, but it is also post-buffering. |
| Feature-flagged CareGuard `POST /cases/{case_id}/vista-segment` | Calls `await file.read()` and forwards the complete bytes to VISTA without a route-level size check. | **Unbounded upload surface.** |
| Local artifact store | Uses generated UUID keys and `_safe_path()` containment checks. | Local traversal control passes the direct probe. |
| Legacy Blob path | Builds `https://blob.vercel-storage.com/{file_id}/{filename}` with the raw client filename. | Filename/path and URL-delimiter handling is unsafe; sanitize or do not interpolate it. |

Relevant source locations are `python/hearttwin/api.py:949-1007,
1077-1095`, `python/hearttwin/careguard/routes_vista.py:32-45`,
`python/hearttwin/tools/storage.py:24-59`, and
`python/hearttwin/storage/local.py:11-34`.

## Verified positive controls

### P-A17-1 — Unknown case is rejected before general upload storage

The general file route loads the case and returns `404` before reading or
persisting the multipart file (`api.py:971-975`). This prevents an upload to a
nonexistent case through that route. It is not authentication or ownership
control; case IDs remain the only application-level reference in this path.

### P-A17-2 — Basic declared content-type allowlist exists

The general route rejects content types outside the explicit set unless the
declared value starts with `image/` or `video/` (`api.py:978-988`). The focused
probe returned:

```text
unsupported_type 400 Unsupported file type 'application/x-msdownload'. Accepted: PDF, image, video, CSV, TXT, JSON, and medical volumes (CT NIfTI/.nii.gz, DICOM/.zip).
```

This is only a declaration check, not content validation; see OPEN-A17-3.

### P-A17-3 — Local artifact keys are UUIDs and traversal is guarded

`store_file()` generates a UUID before writing, so the normal local artifact
path does not use the submitted filename (`tools/storage.py:29-30,53-54`). The
local store resolves the candidate and rejects paths outside its configured
root (`storage/local.py:11-15`). The direct probe returned:

```text
local_traversal_guard ValueError artifact key escapes local storage root
stored_artifacts ['834f50fa-a72b-4f20-8d81-cc63640289f8', '8d69e45f-ae4e-4a4e-a7b6-38fad3d16fe', 'aee86d63-5056-483b-bd49-6e6f5705776f']
```

The UUIDs above are ephemeral probe artifacts, not persistent identifiers.

## Findings

### OPEN-A17-1 — P1: size limits are enforced after full buffering

The general upload calls `await file.read()` and only then compares the length
with `_MAX_UPLOAD_BYTES = 200 * 1024 * 1024` (`api.py:965,990-995`). ECG does
the same before its 50 MiB check (`api.py:1089-1091`). Therefore the configured
limit bounds accepted/stored bytes, but not peak memory, multipart parsing work,
or concurrent in-flight bodies. A caller can send multiple near-limit bodies
before the route returns a `400`.

A lowered-cap endpoint probe confirmed the check is reachable:

```text
cap_probe 400 File exceeds 0 MB limit
```

The cap was temporarily changed to 3 bytes for this probe; production code was
not changed. This test does not prove protection against a real oversized
request because the body has already been read by the time the response is
generated.

**Required before RC:** enforce an edge/server request limit before multipart
buffering, stream to a quota-controlled temporary file or bounded storage,
limit simultaneous uploads, and test over-limit and parallel near-limit
requests. Keep route-specific limits explicit and consistent.

### OPEN-A17-2 — P1: CareGuard VISTA has no upload-size or request-size guard

The feature-flagged VISTA route reads the entire `UploadFile` and passes it to
the adapter with no maximum (`careguard/routes_vista.py:32-36`). The adapter
may then forward the bytes to an external service. This route is outside the
200 MiB general upload cap and outside the 50 MiB ECG cap.

**Required before enabling CareGuard publicly:** add a shared bounded-upload
helper or an equivalent proxy limit, apply it before forwarding, cap provider
request size and processing concurrency, and add a test for rejected oversized
VISTA input.

### OPEN-A17-3 — P1: content validation trusts the client-declared MIME type

The general route accepts every `image/*` and `video/*` declaration and does
not inspect magic bytes, extension consistency, archive structure, image
dimensions, video duration, or decompression ratio. The probe uploaded arbitrary
bytes with media declarations and received `200`:

```text
client_mime_only image/png 200 image/png
client_mime_only video/mp4 200 video/mp4
```

The ECG route similarly allows a filename ending in `.csv` even when the MIME
type is not CSV (`api.py:1084-1087`); parsing is attempted only after the full
body is buffered.

**Required before RC:** validate a bounded prefix and format-specific metadata,
reject MIME/extension/content mismatches where applicable, limit image/video
dimensions and archive expansion, and keep unsupported content from reaching
extractors or external providers.

### OPEN-A17-4 — P1: raw filenames are accepted without length or safe-display limits

The submitted filename is copied into `UploadedFile.filename` and returned in
the response (`api.py:997-1004`). There is no length, control-character,
Unicode-normalization, or basename policy. A 4,100-character filename was
accepted:

```text
filename_4096 200 4100
```

The filename is not the local UUID key, so this is not a demonstrated local
filesystem escape. It remains a metadata/logging/UI risk and becomes a storage
path risk on provider-backed paths.

**Required before RC:** cap filename length, reject or normalize control
characters, retain an opaque display-safe name or a safe basename, and avoid
using the client name as a provider path component.

### OPEN-A17-5 — P1: the legacy Blob URL interpolates an unescaped filename

When `BLOB_READ_WRITE_TOKEN` is configured, `tools/storage.py:37-44` places the
raw filename directly after the UUID in the Blob URL. A fake client captured
this URL for a filename containing traversal and URL delimiters:

```text
blob_url https://blob.vercel-storage.com/5ca88bd8-ddf4-437a-b24e-79dbc68b43c2/../escape?x=1#frag
```

The actual UUID is nondeterministic and is shown only as probe output. The
`?` and `#` are URL delimiters, while `..` changes the apparent path. The
provider may normalize or reject it, but the application must not rely on that
behavior. The same helper also creates `httpx.AsyncClient()` inline without an
explicit close (`tools/storage.py:37`), which can leak connection-pool
resources under repeated uploads.

**Required before RC:** use an opaque provider key and pass the user filename
only as sanitized metadata, URL-encode any unavoidable path segment, use an
async context manager or shared bounded client, and test provider rejection and
fallback cleanup.

### OPEN-A17-6 — P1: no application-wide request-size, quota, or upload abuse boundary

The FastAPI setup installs CORS middleware but no request-body middleware,
upload semaphore, per-case quota, rate limit, or authenticated ownership check
(`api.py:103-117`). The route-local byte checks therefore do not protect
multipart parser memory, concurrent request count, or repeated storage writes.
This overlaps the API reliability and security reviews but is independently
material to file handling.

**Required before public deployment:** establish the trusted edge limit and
backend limit in one documented contract, authenticate/authorize case access,
rate-limit upload and extraction routes, cap per-file/per-case/tenant storage,
and verify behavior through concurrent and repeated-request tests.

## Test record

All commands were run from `/home/923873155/BeatIT` against the current
worktree. The system Python lacked the repository dependencies; the checked-in
`.venv` was used for executable test runs.

| Command / probe | Result |
|---|---|
| `./.venv/bin/pytest -q python/hearttwin/tests/test_intelligence_runtime.py python/hearttwin/tests/test_api_routes.py` | **24 passed, 21 warnings in 1.34s** |
| `TestClient`: normal upload, `../escape.txt`, `nested/../../escape.txt` | All returned `200`; response filenames preserve the submitted name; local artifacts were UUID-named. |
| `TestClient`: `application/x-msdownload` | `400` unsupported type. |
| `TestClient`: temporary 3-byte general cap with 4-byte payload | `400 File exceeds 0 MB limit`; confirms route check, not early rejection. |
| `TestClient`: arbitrary bytes declared `image/png` and `video/mp4` | Both returned `200`; demonstrates declared-MIME trust. |
| `TestClient`: 4,100-character filename | `200`, response filename length `4100`. |
| `LocalArtifactStore._safe_path(root, '../outside')` | `ValueError artifact key escapes local storage root`. |
| Fake Blob client with `../escape?x=1#frag` filename | Captured raw delimiters in the provider URL. |
| Source scan for `UploadFile`, `await file.read`, and size guards | General route: 200 MiB post-read; ECG: 50 MiB post-read; CareGuard VISTA: read with no route cap. |

## Release decision

**Upload/file-handling gate: FAIL.** The default local UUID storage and basic
type rejection are useful controls, and the focused regression tests pass. They
do not establish safe public request handling. Before a release can accept
anything beyond synthetic demo data, the project needs early body-size
enforcement, a bounded CareGuard upload path, content/filename validation, safe
provider keys, upload quotas/concurrency controls, and adversarial tests for
oversized, malformed, archive, path-like, and repeated uploads.
