# Agent 05 — VISTA-3D compatibility audit

**Campaign:** BeatIT model/data verification  
**Date:** 2026-09-26 UTC  
**Scope:** Current BeatIT VISTA-3D integration, local VISTA-3D/NV-Segment artifacts,
checkpoint/runtime compatibility, and license requirements.  
**Boundary:** Read-only audit except for this report. No model download, VISTA HTTP
request, CT segmentation, or inference was performed.

## Plan

1. Read the repository integration seams and existing VISTA notes.
2. Inspect local model paths, caches, checkpoint metadata, host-service code, and
   historical output artifacts without exposing secrets.
3. Probe installed Python/ML packages and GPU/runtime state.
4. Perform a checkpoint-structure load only; do not execute a forward pass.
5. Run the focused BeatIT VISTA/CT/model/environment tests and record the final
   readiness boundary.

## Result

**Disposition: CONDITIONAL / NOT READY FOR LIVE INFERENCE OR DEPLOYMENT.**

The local checkpoint is present and structurally compatible with the installed
MONAI VISTA-3D network. BeatIT's own integration remains optional and is currently
unconfigured; its local adapter has no default runner. A separate local VISTA host
project exists, but no VISTA service is running now. The historical host result is
not treated as current inference evidence. No separate NV-Segment-CT/NV-Segment-CTMR
checkpoint or installed package was found in the searched local stores. The model
weights carry a non-commercial research/evaluation-only NVIDIA license, so public
or commercial redistribution/use requires a separate legal decision.

## Evidence

### 1. BeatIT integration boundary

| Area | Current evidence | Finding |
|---|---|---|
| Model manifest | `models/manifest.json:4-10` | `medical-segmentation` is optional, runtime `monai`, model id `vista3d-0.5.8`, default path `/usr/data/models/vista-3d-host/models/vista3d/models/model.pt`; the manifest explicitly says metadata-only and never loaded at startup. |
| Lazy registry | `python/hearttwin/models/registry.py:1-6,58-103` | Startup/status checks only filesystem metadata. Loading is caller-injected and the registry does not import torch, MONAI, or transformer APIs. |
| Local adapter | `python/hearttwin/imaging/vista3d.py:1-53` | Accepts CT and an existing file, but returns `runner is not configured` unless a caller injects a runner. It does not connect the manifest checkpoint to MONAI by itself. |
| Remote client | `python/hearttwin/tools/vista3d_client.py:73-98,127-145,147-253` | The production path is an optional external API: enabled flag plus base URL, health check, asynchronous submit, and fail-safe warnings. It does not load the local checkpoint. |
| Environment contract | `python/hearttwin/tools/env_config.py:58-75,111-116`; `.env.example:82-86` | `VISTA3D_ENABLED` defaults false. Effective readiness requires endpoint base/key configuration; current shell has no `VISTA3D_*` variables set. |
| CT pipeline | `python/hearttwin/agents/extraction_agent.py:142-177` | A non-analyzed result is retained as a warning-carrying artifact; chamber EF or other scalar values are not invented. |
| Label boundary | `python/hearttwin/tools/vista3d_client.py:35-52`; `python/hearttwin/imaging/reconstruction.py:8-19` | BeatIT treats heart as label 115, aorta as 6, and pulmonary artery as a pulmonary-vein proxy (119). It does not claim chamber-level masks. |
| NV-Segment naming | `python/hearttwin/careguard/imaging/schemas.py:12-28`; `/home/923873155/Vista-3d Host/backend/services/runtime.py:1-16` | NV-Segment names are accepted as schema/runtime aliases or comments. No separate NV-Segment model/package was found. |

The repository's core package declarations do not install the local ML runtime:
`pyproject.toml:8-24` contains no torch or MONAI dependency, and
`data/requirements-data.txt:1-2` deliberately excludes PyTorch, TensorFlow, and
MONAI. This is consistent with the optional/lazy design, but it means a deployment
must provision the VISTA runtime separately.

The filesystem-only BeatIT registry probe returned:

```text
medical-segmentation: configured=True available=True loaded=False
path=/usr/data/models/vista-3d-host/models/vista3d/models/model.pt
model_id=vista3d-0.5.8 required=False error=None
```

`available=True` means the file exists; it does not mean a network was loaded or
that inference works.

### 2. Local VISTA artifacts

The primary local bundle is present at:

```text
/usr/data/models/vista-3d-host/models/vista3d/
```

Observed contents include `configs/`, `docs/`, `scripts/`, `models/model.pt`,
`configs/metadata.json`, `configs/inference.json`, `scripts/inferer.py`, and
`scripts/evaluator.py`. The checkpoint is:

```text
size: 871,970,895 bytes
sha256: c92bab26d00b4a5d89fa8a383900cdeb88302fd318e5e816df0bbec7106d9a1b
format: PyTorch zip archive
mtime: 2026-06-06 21:05:49 UTC
```

A second copy exists at
`/usr/data/models/fetchhealth/Models/hpc-model-backend/models_cache/vista3d/vista3d/`.
`cmp` confirmed that its `model.pt` is byte-identical to the primary checkpoint.
This is an existing cache, not a download performed by this audit.

The local bundle metadata reports version `0.5.8`, with 133 channel definitions
(background plus 132 labels), including `6=aorta`, `115=heart`, `119=pulmonary
vein`, and `125=superior vena cava`. These values are from the local
`configs/metadata.json`, not an internet lookup.

A separate project exists at `/home/923873155/Vista-3d Host`. It contains a
FastAPI/worker service, direct-Python and `monai.bundle` runtime modes, and a
historical output directory:

```text
/home/923873155/Vista-3d Host/received_results/
  b2138aee-4527-463f-ab19-3359acefd185/
```

Its local `metadata.json` records a prior host-side job using VISTA-3D 0.5.8,
torch `2.7.1+cu118`, MONAI `1.5.2`, one RTX 3090, and 5.60 seconds runtime. The
same metadata records `output_labels: []`; the mask and metadata files exist, but
this audit did not reproduce or validate that job. It is therefore historical
artifact provenance only, not evidence of current BeatIT inference.

No VISTA process was running. The only observed listener on port 8000 belonged to
an unrelated `/home/923873155/EverFrame` process. No VISTA endpoint was contacted.

### 3. Runtime and package compatibility

Observed in the current shell (`/opt/miniconda/bin/python`, Python 3.13.12):

| Component | Observed version/state | Interpretation |
|---|---|---|
| torch | `2.5.1+cu121` | Imports successfully; CUDA build is available. |
| MONAI | `1.5.2` | Exact match to the local bundle metadata/host result. `vista3d132`, `VistaPreTransformd`, and `VistaPostTransformd` import successfully. |
| CUDA | torch reports `12.1`; `nvcc` is `12.2` | Compatible-looking for the installed cu121 wheel; not a complete service validation. |
| cuDNN | `91900` | Reported by torch. |
| GPUs | 2 x NVIDIA GeForce RTX 3090, 24 GB each; driver `535.288.01` | Hardware matches the separate host project's declared two-GPU design. |
| nibabel / pydicom | `5.4.2` / `3.0.2` | NIfTI and DICOM metadata libraries are available. |
| einops / pytorch-ignite / fire | `0.8.2` / `0.5.4` / `0.7.1` | Supporting imports required by the host bundle succeed. |
| SimpleITK | not installed | The host requirements use it for DICOM-series conversion; that path is not ready in this shell. NIfTI IO is not thereby proven end-to-end. |
| Python service image | host Dockerfile declares Python 3.10 and CUDA 12.1.1 cuDNN runtime | This differs from the current Python 3.13 shell and must be pinned/retested for deployment. |

The host service declares `torch` installed separately from the cu121 index,
MONAI `>=1.4`, `einops`, `pytorch-ignite`, `fire`, and `huggingface_hub` in
`/home/923873155/Vista-3d Host/backend/requirements.txt:25-33`. Its Dockerfile
uses `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04` and cu121 PyTorch wheels
(`/home/923873155/Vista-3d Host/docker/Dockerfile:1-3,16-20`).

### 4. Structural checkpoint test (not inference)

The audit safely loaded the checkpoint with `torch.load(..., weights_only=True,
map_location="cpu")`, instantiated MONAI `vista3d132(in_channels=1)`, and called
`load_state_dict` without a forward pass:

```text
model_class: VISTA3D
parameter_count: 217,964,982
strict_compatible: True
missing_count: 0
unexpected_count: 0
```

This establishes that the checkpoint's state-dict keys/shapes match the installed
MONAI 1.5.2 VISTA3D network. It does not establish preprocessing correctness,
GPU execution, memory headroom, output quality, latency, or API service health.

### 5. BeatIT data/job artifacts

BeatIT contains three local CT fixtures under `data/imaging-cases/` and static
VISTA capability/job records. The records for `imaging-case-000001` through
`000003` use `source="static_fallback"`, `reachable=false`, and state `failed`.
For example, `data/imaging-cases/imaging-case-000001/imaging/vista/job.json:59-101`
records the endpoint as unreachable and explicitly says: “no live segmentation
performed. No masks/volumes invented.” These records are valuable negative-path
evidence, not segmentation outputs.

### 6. Focused verification

Command:

```bash
python -m pytest -q \
  python/hearttwin/tests/test_vista3d_client.py \
  python/hearttwin/tests/test_ct_pipeline_integration.py \
  python/hearttwin/tests/test_models.py \
  python/hearttwin/tests/test_env_config.py
```

Result: **96 passed, 1 warning in 3.13s**. The warning is a Pydantic
`datetime.utcnow()` deprecation from test execution; no VISTA test failed.

## Checkpoint/runtime/license requirements

### Minimum technically supported shape

- VISTA-3D bundle root must contain the official-style `configs/`, `models/`, and
  `scripts/` tree.
- `model.pt` must be the VISTA-3D 0.5.8 checkpoint compatible with
  `monai.networks.nets.vista3d132(in_channels=1)`.
- Native direct-Python execution requires torch with CUDA support (or an explicit
  CPU debug mode), MONAI 1.5.2-compatible APIs, the bundle's `scripts` modules,
  `einops`, and `pytorch-ignite`. A real CT requires NIfTI/DICOM preprocessing;
  the host's DICOM conversion additionally requires SimpleITK.
- The host's declared deployment baseline is Python 3.10 in a CUDA 12.1.1
  cuDNN runtime with cu121 PyTorch wheels. The current shell is a useful
  structural compatibility check, not a substitute for reproducing that image.
- BeatIT's supported production seam is currently the external, env-gated API.
  A live run needs `VISTA3D_ENABLED=true`, a reachable `VISTA3D_API_BASE`, the
  endpoint key/secret, and a health response before submission. The local model
  file does not satisfy those remote-service requirements.

### License requirements

The local VISTA bundle's `LICENSE` separates code from weights:

- Bundle code is Apache License 2.0.
- Model weights are under the NVIDIA License. Section 3.3 limits the Work and
  derivatives to **non-commercial research or evaluation**; Section 3.1 requires
  the complete license and notices on redistribution.
- The same license disclaims warranties and does not grant NVIDIA trademark
  rights. `docs/data_license.txt` also carries a Medical Segmentation Decathlon
  third-party-license notice.

Accordingly, do not package the checkpoint into a public/commercial BeatIT
deployment or demo artifact without confirming that the intended use is within
the NVIDIA weights license and retaining the required notices. The checkpoint is
currently outside this repository, which avoids an accidental commit but does
not resolve downstream deployment rights.

## Risks and open gates

1. **Live inference is unverified.** No forward pass, real CT job, GPU memory
   measurement, output-label check, or current API health check was run.
2. **BeatIT local path is incomplete by design.** `Vista3DSegmenter` needs an
   injected runner; simply seeing `available=True` in the registry does not wire
   the checkpoint into extraction.
3. **Version drift exists.** Historical host metadata used torch 2.7.1+cu118;
   this shell uses torch 2.5.1+cu121. Structural loading passed, but full
   preprocessing/inference still needs a pinned environment test.
4. **DICOM conversion gap.** SimpleITK is absent from the current shell even
   though the host service requires it.
5. **No NV-Segment implementation was located.** The schema aliases are not
   evidence of an NVIDIA NV-Segment-CT/NV-Segment-CTMR runtime or checkpoint.
6. **Historical output is weak evidence.** The separate host artifact's metadata
   reports no output labels and was not regenerated during this audit.
7. **License may block the intended public demo.** The weights are research/eval
   only unless legal review establishes otherwise.
8. **Data linkage remains bounded.** The local imaging records are deidentified,
   imaging-only fixtures and explicitly are not verified same-subject clinical
   records; they must not be presented as patient-specific validation.

## Final disposition

**Accepted as a unique campaign contribution: structural compatibility and local
artifact audit complete.**

**Release gate:** hold VISTA/NV-Segment live enablement. BeatIT may continue to
run its deterministic, non-imaging fallback with VISTA disabled. Before enabling
imaging, a separately authorized verification should pin the host environment,
install/verify SimpleITK if DICOM is required, run a deidentified CT through the
actual service or injected runner, confirm non-empty/expected labels and mask
provenance, measure GPU/memory behavior, verify endpoint authentication, and
obtain license approval for the deployment/demo context. Until those gates pass,
the honest status is **checkpoint present and structurally loadable; live
VISTA-3D inference unverified and not claimed**.
