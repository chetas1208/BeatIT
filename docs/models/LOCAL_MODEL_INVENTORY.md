# BeatIT local model inventory

Inventory date: 2026-09-26 UTC. No weights were downloaded or moved by this
campaign. Paths below are outside the repository unless explicitly noted.

## Selected/relevant artifacts

| Model | Path | Size | Format/framework | Probable purpose | Validation |
|---|---|---:|---|---|---|
| VISTA-3D 0.5.8 | `/usr/data/models/vista-3d-host/models/vista3d/models/model.pt` | 871,970,895 bytes (~832 MiB) | PyTorch checkpoint; MONAI bundle metadata | CT anatomical segmentation | `torch.load(..., map_location='cpu', weights_only=False)` succeeded in 0.52s; OrderedDict state dict |
| VISTA-3D metadata | `/usr/data/models/vista-3d-host/models/vista3d/configs/metadata.json` | 8,975 bytes | MONAI bundle metadata | Runtime/version/label contract | Read successfully; expects PyTorch 2.4.0 and MONAI 1.4.0; host is newer |
| MedGemma | `/usr/data/models/fetchhealth/Models/hpc-model-backend/models_cache/medgemma` | ~8.1 GiB | 2 sharded safetensors; Gemma3ForConditionalGeneration | Optional medical language/vision assistance | Complete-looking config/index/tokenizer set; direct inference not run because no local serving contract is configured |
| Llama 3.1 8B Instruct | `/usr/data/models/skillllm-v2/models/llama-3.1-8b-instruct` | ~30 GiB | 4 sharded safetensors; LlamaForCausalLM | General language | Complete-looking config/index/tokenizer set; not selected over the smaller medical candidate |
| Qwen3 14B | `/usr/data/models/skillllm-v2/models/qwen3-14b` | ~28 GiB | 8 sharded safetensors; Qwen3ForCausalLM | General language | Complete-looking bundle; not selected due larger VRAM footprint |
| Mistral Small 3.1 24B | `/usr/data/models/skillllm-v2/models/mistral-small-3.1-24b-instruct-2503` | ~46 GiB plus duplicate consolidated file | Sharded/consolidated safetensors; Mistral3 | General/multimodal language | Present but excessive for the minimum portfolio |

## Caches and other local storage

- Hugging Face cache: approximately 5.9G, including compact embedding and
  biomedical encoder snapshots plus unrelated vision/audio/video artifacts.
  The cache layout is blob/snapshot based; it is not a clean BeatIT model
  portfolio.
- Torch cache: approximately 5.1M.
- NVIDIA cache: approximately 11M.
- No usable MONAI cache directory was found.
- `/usr/data` contains additional task-specific models (voice, geospatial,
  image detection, and unrelated services); they are not BeatIT capabilities.

## VISTA-3D boundary

The local checkpoint is present and structurally loadable. Metadata lists CT
input, 128³ patches, 1.5 mm resampling, and cardiac labels such as heart,
aorta, IVC, pulmonary vein, and SVC. It is not evidence of patient-specific
physiology: segmentation produces anatomy, while BeatIT physiology stays
deterministic. A direct GPU segmentation smoke test is not claimed because the
bundle expects MONAI 1.4/PyTorch 2.4 and a full preprocessing/inference runner
is not configured in this repository.

## Duplicate/selection notes

The same broad model families appear in more than one service cache. BeatIT
does not copy them. The registry records capability metadata and checks paths
lazily; weights remain managed by their existing owners.
