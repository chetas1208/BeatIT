# Local model benchmark record

Audit date: 2026-09-26 UTC.

## VISTA-3D checkpoint metadata/load smoke

| Measure | Result |
|---|---|
| Artifact | `/usr/data/models/vista-3d-host/models/vista3d/models/model.pt` |
| File size | 871,970,895 bytes (~832 MiB) |
| CPU checkpoint load | PASS; 0.52 seconds; `OrderedDict` state dict |
| GPU inference latency/throughput | NOT RUN |
| VRAM | NOT MEASURED |
| Output validity | Not applicable to a checkpoint-only load |

The missing GPU figures are intentional: loading a checkpoint is not a
segmentation benchmark, and the bundled preprocessing/network runner was not
configured against this host's newer MONAI/PyTorch versions. No synthetic
clinical performance is claimed.

## Language candidates

MedGemma (~8.1 GiB), Llama 3.1 8B (~30 GiB), Qwen3 14B (~28 GiB), and Mistral
Small 3.1 24B (~46 GiB plus a consolidated copy) were inventoried. No language
model was loaded or benchmarked because BeatIT has no approved local serving
configuration for these artifacts. The existing provider-neutral runtime and
deterministic fallback remain the measured path.
