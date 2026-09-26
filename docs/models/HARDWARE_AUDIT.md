# BeatIT local hardware audit

Audit date: 2026-09-26 UTC. Commands were run on the host serving this
workspace; values are a point-in-time snapshot and should be refreshed before
production capacity planning.

| Resource | Observed |
|---|---|
| GPU | 2 x NVIDIA GeForce RTX 3090 |
| VRAM | 24,576 MiB per GPU (approximately 24 GiB) |
| NVIDIA driver | 535.288.01 |
| CUDA / PyTorch | CUDA 12.1 build; `torch 2.5.1+cu121`; `torch.cuda.is_available()` true; 2 devices visible |
| CPU | Intel Core i9-10900X @ 3.70 GHz; 20 logical CPUs |
| RAM | 125 GiB total; approximately 107 GiB available during audit |
| Swap | 8 GiB configured; approximately 196 MiB free during audit, so large loads should avoid swap |
| Root disk | 3.6T total; 759G available; 79% used |
| `/usr/data` | 2.7T total; 2.2T available; 22% used |
| Python | 3.13.12 |
| MONAI | 1.5.2 |
| Transformers | 5.14.1 |
| Hugging Face Hub | 1.24.0 |
| ONNX Runtime | 1.25.1 |
| Docker | Server 29.5.3; `runc` default runtime; no NVIDIA container runtime shown |

The installed CUDA stack is usable from the host Python process. Docker GPU
execution is not established by this audit. The swap state is a capacity risk:
do not concurrently load multiple large language models during development.
