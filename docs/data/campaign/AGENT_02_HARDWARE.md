# Agent 02 — Hardware and Runtime Audit

## Plan and scope

This is the unique contribution for campaign workstream 2, “Hardware/runtime
audit.” The audit used read-only host commands and a small in-memory CUDA tensor
operation. It did not start services, pull images, download models, inspect
secrets, change configuration, or edit production code.

Audit timestamp: `2026-09-26T17:47:29Z` UTC (host-local observation)

## Result

**Conditional pass for native host CUDA/PyTorch work.** The host exposes two
NVIDIA RTX 3090 GPUs and both passed a PyTorch CUDA execution and synchronization
smoke test. CPU, RAM, disk, and `/usr/data` capacity are currently adequate for
development and local experiments.

Two runtime gaps prevent a full production-readiness claim:

1. Docker has only `runc`/containerd runtimes and defaults to `runc`; the
   NVIDIA Container Toolkit/runtime is not installed or registered, so
   container GPU pass-through is **not verified and should be treated as
   unavailable**.
2. The audited Python interpreter does not have `weave` installed even though
   `requirements.txt` declares it and `pyproject.toml` lists it under the
   optional `tracing` extra. Weave-dependent runs therefore require dependency
   installation in the intended environment.

## Evidence summary

| Area | Observed evidence | Assessment |
|---|---|---|
| Host OS/kernel | Ubuntu 24.04.5 LTS from Docker; Linux 6.8.0-139-generic, x86_64 | Suitable for the observed stack |
| CPU | Intel Core i9-10900X, 10 physical cores / 20 logical CPUs, max 4.7 GHz; AVX2 and AVX-512 flags present | Pass for CPU preprocessing and inference support |
| RAM | 125 GiB visible; 105 GiB available at sample time; 8 GiB swap, 6.2 GiB used | Capacity pass; investigate sustained swap use before heavy jobs |
| GPU | 2 × NVIDIA GeForce RTX 3090, 24,576 MiB reported by `nvidia-smi` each | Pass; 48 GiB nominal aggregate VRAM, not one pooled device |
| GPU driver | NVIDIA driver 535.288.01; both GPUs in P8 at sample time | Driver visible and operating |
| GPU sample | GPU 0: 27 C, 0% utilization, 1 MiB used; GPU 1: 32 C, 0% utilization, 1 MiB used | Idle/healthy snapshot; not a sustained benchmark |
| CUDA toolkit | `/usr/local/cuda-12.2/bin/nvcc`; CUDA 12.2, V12.2.91; `libcuda.so` and `libcudart.so.12` visible | Host toolkit and libraries visible |
| PyTorch | `2.5.1+cu121`; CUDA build 12.1; `torch.cuda.is_available()=True`; device count 2 | Native CUDA runtime pass |
| PyTorch device memory | Device 0: 25,438,126,080 bytes total / 25,164,526,816 free; device 1: 25,429,999,616 total / 25,156,452,352 free | Both devices available to PyTorch at sample time |
| CUDA execution | On each device, `[1,2,3] + [4,5,6]` returned `[5.0,7.0,9.0]` and `torch.cuda.synchronize()` succeeded | Direct execution smoke pass |
| MONAI | Distribution `1.5.2`; import succeeded | Available in audited interpreter |
| Transformers | Distribution `5.14.1`; import succeeded | Available in audited interpreter |
| vLLM | Not installed; import unavailable | Not available for local serving |
| llama.cpp | `llama-cpp-python` distribution and `llama_cpp` import unavailable | Not available for local serving |
| Python | `/opt/miniconda/bin/python3`, CPython `3.13.12` | Meets project minimum `>=3.12`; exact environment is not pinned by this audit |
| Docker | Client `29.8.1`, server `29.5.3`, API `1.54`; Compose `v5.5.1` | Engine reachable |
| Docker runtimes | Registered names: `io.containerd.runc.v2`, `runc`; default `runc` | No NVIDIA runtime registered |
| NVIDIA container runtime | `nvidia-container-runtime` and `nvidia-ctk` not found; package queries returned no NVIDIA Container Toolkit entries | Container GPU path not ready/verified |
| Root filesystem | ext4, 3.6 TiB total, 2.8 TiB used, 743 GiB available, 79% used | Adequate now; monitor growth |
| `/usr/data` | ext4 LVM mount, 2.7 TiB total, 580 GiB used, 2.2 TiB available, 22% used; backed by two NVMe devices in the observed layout | Good capacity for model/data staging |
| Other mounts | `/boot` 2.0 GiB with 1.6 GiB available; `/boot/efi` 1.1 GiB with 1.1 GiB available | No immediate capacity issue observed |

## Commands and interpretation

The following read-only probes were used; outputs are summarized above rather
than copied wholesale:

```text
date -u
uname -a
getconf LONG_BIT
nproc
lscpu
free -h
awk on /proc/meminfo (MemTotal, MemAvailable, SwapTotal, SwapFree, huge pages)
df -hT -x tmpfs -x devtmpfs
lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,RO
findmnt -rn -o TARGET,FSTYPE
nvidia-smi -L
nvidia-smi --query-gpu=... --format=csv,noheader
nvcc --version
/proc/driver/nvidia/version
ldconfig -p (libcuda/libcudart entries)
docker version
docker info (CPU, memory, runtimes, default runtime)
docker compose version
command -v nvidia-container-runtime
command -v nvidia-ctk
dpkg-query for NVIDIA Container Toolkit packages
python --version and interpreter metadata
importlib.metadata for torch, monai, transformers, vllm, llama-cpp-python,
  llama_cpp, and selected BeatIT dependencies
PyTorch CUDA availability/device/memory queries
PyTorch tensor add plus cuda synchronize on both devices
```

The CUDA smoke test allocated only two three-element tensors per GPU. It proves
that the audited host interpreter can execute CUDA work, not that a target model
fits, that multi-GPU parallelism is configured, or that a container can access
the devices.

## Repository/runtime alignment

The inspected project metadata requires Python `>=3.12` and declares the core
web/API stack. `requirements.txt` includes `weave>=0.51.0`; `pyproject.toml`
places Weave in the optional `tracing` extra. Neither file declares PyTorch,
MONAI, transformers, vLLM, or llama.cpp. The installed ML packages are therefore
host-environment capabilities rather than a reproducible dependency set for the
repository as inspected.

The audited environment reported these selected versions:

```text
fastapi=0.136.0
numpy=2.5.2
scipy=1.17.1
pydantic=2.13.4
openai=2.36.0
uvicorn=0.45.0
redis=8.0.0
copilotkit=0.1.94
pytest=9.0.3
weave=NOT_INSTALLED
```

These are observations only; no package was installed or upgraded during the
audit.

## Limitations and risks

- The GPU, RAM, utilization, and free-space values are point-in-time samples;
  they do not establish sustained thermal, power, throughput, or contention
  behavior.
- No model was loaded and no benchmark was run. VRAM fit, model quality,
  inference latency, multi-GPU sharding, and MONAI workload compatibility remain
  unverified.
- No Docker container was launched. Because the NVIDIA runtime/toolkit is absent
  from the observed Docker configuration, a containerized CUDA smoke test is an
  explicit follow-up, not a result of this audit.
- Swap has 6.2 GiB used despite 105 GiB available RAM. This may be historical or
  workload-related; heavy jobs should be monitored for additional swapping.
- The root volume is 79% full. It has substantial free capacity, but model/image
  downloads should be directed to `/usr/data` and retained artifacts should be
  managed before the volume becomes constrained.
- The driver/toolkit/PyTorch combination is observed as driver 535.288.01,
  toolkit 12.2, and PyTorch CUDA build 12.1. The tensor smoke test passed, but
  any compiled extension should still be tested against its exact build matrix.
- Weave was not imported because it is not installed. No network connectivity,
  API credentials, Weave project, Redis endpoint, or external deployment was
  tested, and no secret values were read or recorded.
- Package import emitted third-party CPU/GPU discovery logs while importing the
  ML stack; these were not treated as failures because the targeted imports and
  CUDA test completed successfully.

## Final disposition

**CONDITIONAL PASS — native host hardware and CUDA runtime available.**

**BLOCKED for GPU-enabled Docker execution and Weave-dependent execution until
the NVIDIA Container Toolkit/runtime and the repository’s tracing dependency are
installed and verified in the intended runtime environment.** This report is
complete for Agent 02; no production files or host configuration were changed.
