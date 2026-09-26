# BeatIT Final Hardware and Runtime Audit

Date: 2026-09-26 UTC

| Surface | Observed result | Disposition |
|---|---|---|
| GPUs | 2 x NVIDIA RTX 3090, 24 GiB each | Native CUDA available |
| Driver/CUDA | NVIDIA driver 535.288.01; CUDA 12.2 toolkit | Pass for native host smoke |
| PyTorch | 2.5.1+cu121; CUDA tensor execution passed on both GPUs | Pass |
| CPU/RAM/disk | 20 logical CPUs; 125 GiB RAM; 3.6 TiB root; 2.7 TiB `/usr/data` | Pass for local cohort work |
| MONAI/transformers | Installed | Compatibility requires model-specific validation |
| vLLM/llama.cpp | Not installed | No local serving claim |
| Docker GPU runtime | NVIDIA Container Toolkit not registered | GPU container deployment open |
| Weave package | Not available in the audited Python environment | Local trace fallback only |
| Synthea/NeuroKit2 | No usable local installation found | Campaign uses deterministic local generator/ECG fixture path |

The audit used bounded host commands (`nvidia-smi`, `free`, `lscpu`, `df`,
`findmnt`, Python package probes) and did not scan `/proc`, `/sys`, or `/dev`
recursively. No secret values were recorded.

## Decision

Native deterministic/CUDA verification is available. Live language serving,
VISTA request inference, GPU Docker execution, and Weave tracing remain open.
