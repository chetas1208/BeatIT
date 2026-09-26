# Model and imaging runtime review

**Date:** 2026-09-26 UTC  
**Scope:** `python/hearttwin/models/registry.py` and
`python/hearttwin/imaging/vista3d.py` (read-only inspection). No code was
modified.

| # | Finding | Disposition |
|---|---|---|
| 1 | **Checkpoint resolution is inconsistent.** `ModelRegistry.status()` and `load()` apply `BEATIT_MODEL_ROOT`, but `Vista3DSegmenter.segment_volume()` calls `configured_path()` without that root. A relative checkpoint can therefore appear available in the registry while segmentation reports it missing. | **Fix before local imaging use.** Expose one registry/path-resolution method and use it from the adapter. Add a regression test covering a relative path plus `BEATIT_MODEL_ROOT`. |
| 2 | **Loaded-state ownership is split.** The adapter obtains a checkpoint path with `get_model()` and invokes its injected runner directly; it never calls `ModelRegistry.load()`. Registry status can consequently report `loaded: false` after the runner has loaded the model. | **Clarify and align.** Either route loading through the registry or report runner-owned lifecycle separately; do not present the registry flag as authoritative for this adapter until then. |
| 3 | **Filesystem and runtime boundaries are under-validated.** The adapter accepts an arbitrary `VolumeInput.path`, checks only `is_file()`, and passes it to the runner; model paths likewise lack resolved-root/symlink policy, and runner exceptions are not converted to the adapter’s warning result. | **Harden before request-facing exposure.** Restrict inputs to server-owned/allowlisted roots, resolve and validate paths, and translate expected runner failures into an incomplete result with safe diagnostics. |

