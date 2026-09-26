# Campaign Agent 03 — Local model and snapshot inventory

**Inventory time:** 2026-09-26 UTC  
**Scope:** read-only inventory of model artifacts, Hugging Face cache/snapshot
layouts, and MONAI/VISTA-3D bundle completeness signals under the permitted
local roots.  
**Contribution:** unique local-model filesystem evidence, complementary to the
capability audit and the `/usr/data` permission/data inventory.  
**Change boundary:** only this report was written. No model was downloaded,
moved, deleted, hashed, loaded, or used for inference. No secret value was
printed or recorded.

## Plan

1. Read the repository instructions and inspect the pre-existing model
   documentation without treating it as current filesystem proof.
2. Inspect the BeatIT repository, `/home/923873155` caches, `/usr/data`,
   `/var/lib`, and mounted local directories with bounded, read-only searches.
3. Locate checkpoint extensions, MONAI/VISTA bundle markers, and Hugging Face
   `models--*/snapshots` layouts.
4. Record exact paths, rounded directory sizes, shard/file counts, and
   completeness signals while separating serving candidates from training,
   metadata-only, and unrelated service-owned artifacts.
5. Report limitations and a safe disposition; do not infer runtime readiness
   from file presence.

## Evidence

All checks were run locally from `/home/923873155/BeatIT`. Search commands were
filesystem-only; no network client, package manager, model loader, or inference
runner was invoked.

### Search roots and storage boundaries

| Root/check | Live result |
|---|---|
| BeatIT repository | One model-like artifact: `python/hearttwin/research/ecg_dx/model.joblib` |
| `/home/923873155/.cache/huggingface` | Present, 8.1G; 24 Hugging Face repository directories |
| `/home/923873155/.cache/torch` | Present, 5.1M; no model checkpoint inventory claimed |
| `/home/923873155/.cache/monai` | Absent |
| `/home/923873155/.modelscope` | Present, 12K; no model snapshot observed |
| `/models`, `/data`, `/opt/models` | Absent |
| `/var/lib` | No model-weight extensions or Hugging Face/MONAI snapshot directories found |
| `/mnt`, `/media` | No model-weight extensions found; both resolve to the root filesystem rather than distinct mounts |
| `/usr/data` | Separate `ext4` mount, 2.7T total, 580G used, 2.2T available; model roots and caches are present |

The broad home traversal pruned Docker/container storage, Git metadata,
`node_modules`, virtual environments, Python `site-packages`, and unrelated
build caches. `EverFrame*` was identified but not expanded into a second
project-wide model catalog; its model ownership is outside this BeatIT
contribution. This prevents unrelated artifacts from being misrepresented as
BeatIT dependencies.

### BeatIT-local artifact

| Path | Size | Format/use signal | Completeness signal | Disposition |
|---|---:|---|---|---|
| `/home/923873155/BeatIT/python/hearttwin/research/ecg_dx/model.joblib` | 3,475,594 bytes (~3.31 MiB) | Regular Joblib artifact beside `classifier.py`, `features.py`, and `train.py` | Single-file repository artifact; no HF/MONAI manifest expected | Present local ECG research artifact; not loaded or promoted by this inventory |

The repository's `.venv` `.pth` files were environment plumbing, not model
weights, and were excluded from the inventory.

### Hugging Face cache and snapshot evidence

Completeness labels below are structural only:

- **Complete-looking:** a snapshot has the expected config, tokenizer, and
  model file/shard sequence; no broken snapshot symlink or `.incomplete` file
  was observed.
- **Partial/metadata-only:** a repository directory or snapshot exists, but
  standard model weights or the expected serving files are absent.
- **Unresolved:** non-standard layouts or service-owned caches need an owner
  contract before they can be selected.

| Cache/repository path | Size | Observed shape | Completeness signal |
|---|---:|---|---|
| `/home/923873155/.cache/huggingface/hub/models--*` | 8.1G aggregate | 24 repos; 11 have non-empty snapshots, 13 are metadata-only | 7 repos have standard config/model/tokenizer sets: ColBERT, Laya, E5-small, MedCPT article/query, MiniLM, and ModernFinBERT. The other snapshot-bearing entries are partial or non-standard. 0 `.incomplete` files and 0 broken snapshot links observed. |
| `/home/923873155/.cache/huggingface/hub/models--intfloat--e5-small-v2` | 129M | `config.json`, `model.safetensors`, tokenizer files | Complete-looking embedding snapshot; not configured as BeatIT embedding runtime |
| `/home/923873155/.cache/huggingface/hub/models--ncbi--MedCPT-Article-Encoder` | 419M | `config.json`, `model.safetensors`, tokenizer files | Complete-looking biomedical encoder snapshot; no BeatIT runtime binding |
| `/home/923873155/.cache/huggingface/hub/models--ncbi--MedCPT-Query-Encoder` | 419M | `config.json`, `model.safetensors`, tokenizer files | Complete-looking biomedical encoder snapshot; no BeatIT runtime binding |
| `/home/923873155/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2` | 88M | `config.json`, `model.safetensors`, pooling/tokenizer files | Complete-looking embedding snapshot; not proof of semantic retrieval availability |
| `/home/923873155/.cache/huggingface/hub/models--colbert-ir--colbertv2.0` | 419M | `config.json`, `model.safetensors`, tokenizer files | Complete-looking encoder snapshot; no application selection evidence |
| `/usr/data/923873155/llm-models/hf_cache/models--Qwen--Qwen2.5-7B-Instruct` | 15G | One snapshot, 14 regular files, four sequential safetensors shards, config, tokenizer, merges/vocabulary | Complete-looking snapshot; no checksum or inference validation performed |
| `/usr/data/models/hpc-nemotron-backend/data/models/hf_cache/models--nvidia--Nemotron-3-Nano-Omni-30B-A3B-Reasoning-{FP8,NVFP4}` | 33G / 21G | Four FP8 shards and three NVFP4 shards with config, tokenizer, generation, and processor metadata | Complete-looking snapshots; owned by an external HPC service cache, not a BeatIT contract |
| `/usr/data/models/hpc-nemotron-backend/data/models/hf_cache/models--nvidia--Llama-3.1-Nemotron-Nano-VL-8B-V1` | 17G | One `model.safetensors` plus config/tokenizer/processor files | Complete-looking snapshot; a duplicate 17G `hub/` copy also exists |
| `/usr/data/models/hpc-nemotron-backend/data/models/hf_cache/hub/models--Systran--faster-whisper-base.en` | 141M | `model.bin`, config, tokenizer, vocabulary | Complete-looking audio snapshot; unrelated to BeatIT cardiac capability |
| `/usr/data/models/hpc-nemotron-backend/data/models/hf_cache/models--nvidia--C-RADIOv2-H` | 32K | Snapshot/refs metadata with no meaningful weight set | Metadata-only/partial |
| `/usr/data/models/hpc-nemotron-backend/data/models/hf_cache/hub/models--nvidia--Nemotron-3-Nano-Omni-30B-A3B-Reasoning-FP8` | 280K | Hub metadata and six config/processor files | Metadata-only duplicate; not equivalent to the 33G complete-looking cache |
| `/usr/data/models/traceproof/traceproof-model-server/model_weights/huggingface/hub/models--*` | 3.1G across three model repos; 7.4G HF root including blobs | CLIP, Wav2Vec2, and AI-image-detection snapshot repos; direct weights also exist beside the cache | Wav2Vec2 and image-detection repos have config/processor/model files; CLIP snapshot is sparse. Service-owned and unresolved for BeatIT |
| `/home/923873155/Nvidia Models Host/hpc-nemotron-backend/data/hf_cache` | 4K | Empty/metadata-only cache at this home-side path | Not a usable local snapshot; canonical-looking copies are under `/usr/data` |

The 12K home-cache entries for models such as Qwen3, Kokoro, CLIP, and several
video models have no snapshot directory or weight files. They are recorded by
the aggregate count as metadata-only, not as available models.

### MONAI and direct checkpoint bundles

| Bundle/root | Size | Artifact evidence | Completeness signal |
|---|---:|---|---|
| `/usr/data/models/vista-3d-host/models/vista3d` | 832M | `models/model.pt` is 871,970,895 bytes; `configs/metadata.json` is 8,975 bytes; `configs/inference.json`, labels, docs, and scripts are present | Strongest MONAI/VISTA bundle signal: checkpoint plus inference/metadata/label contract. Prior repository inventory records a CPU structural load, but this pass did not load it. |
| `/usr/data/models/fetchhealth/Models/hpc-model-backend/models_cache/vista3d/vista3d` | 832M | Byte-identical-size duplicate path with the same `model.pt` and config structure | Complete-looking duplicate; owner/service boundary unresolved |
| `/usr/data/models/fetchhealth/Models/hpc-model-backend/models_cache/medgemma` | 8.1G | Two safetensors shards, `model.safetensors.index.json`, config, tokenizer model/config | Complete-looking sharded bundle; no local serving configuration or load test |
| `/usr/data/models/fetchhealth/Models/hpc-model-backend/models_cache/qwen25vl` | 16G | Five safetensors shards, index, config, tokenizer | Complete-looking sharded bundle; external service-owned |
| `/usr/data/models/fetchhealth/Models/hpc-model-backend/models_cache/rad_dino` | 840M | Multiple safetensors weights including a compatible-backbone file plus config | Weight-bearing bundle; standard completeness is not proven without its owner manifest |
| `/usr/data/models/fetchhealth/Models/hpc-model-backend/models_cache/medsam2` | 1006M | Two `.pt` files, including a SAM2 Hiera checkpoint | Weight-bearing but unresolved; no standard config/index signal was found in the bounded marker scan |
| `/usr/data/models/skillllm-v2/models/llama-3.1-8b-instruct` | 30G | Four safetensors shards plus original-format consolidated file, index/config/tokenizer | Complete-looking base-model bundle with duplicate format files |
| `/usr/data/models/skillllm-v2/models/qwen3-14b` | 28G | Eight sequential safetensors shards, index/config/tokenizer | Complete-looking base-model bundle |
| `/usr/data/models/skillllm-v2/models/mistral-small-3.1-24b-instruct-2503` | 90G | Ten safetensors shards plus a consolidated safetensors file, index/config/tokenizer | Complete-looking but duplicated and large; not a BeatIT runtime selection |
| `/usr/data/models/skillllm-v2/models/gemma-4-e4b-it` | 15G | Single safetensors file, config, tokenizer | Complete-looking base-model bundle |
| `/usr/data/models/skillllm-v2/models/gemma-4-26b-a4b-it` | 49G | Two safetensors shards, index/config/tokenizer | Complete-looking sharded base-model bundle |

### Training and unrelated model stores

| Path | Size | Evidence and completeness interpretation |
|---|---:|---|
| `/usr/data/models/skillllm-v2/results` | 21G | Multiple training checkpoints with adapter and optimizer files; run-level completeness and serving compatibility are not established |
| `/usr/data/models/skillllm-v2/Extract_jobDesc` | 19G | BERT-style training checkpoints and optimizer state; training artifacts, not a selected BeatIT language model |
| `/usr/data/models/skillllm-v2-stage2/artifacts/skillllm_v2` | 1.5G | LoRA/GLiNER and wrapper artifacts; some are evaluation/smoke outputs rather than standalone bases |
| `/usr/data/models/solux-models` | 38G | Geospatial, remote-sensing, local-critic, and Clay model files; complete ownership/runtime contracts belong to Solux |
| `/usr/data/models/traceproof/traceproof-model-server/model_weights` | 9.8G | Direct Wav2Vec2, Parakeet, CLIP, and image-detection weights; unrelated TraceProof service store |
| `/usr/data/models/emotion-detect` | 2.7G | CREMA-D/RAVDESS training/result checkpoints; not a BeatIT model contract |

These roots are evidence that local model capacity exists, not evidence that
BeatIT may use the models. No license, provenance, tenant permission, runtime
compatibility, or clinical suitability was inferred.

## Result

1. BeatIT itself contains one small Joblib ECG artifact and no repository-local
   HF/MONAI weight tree.
2. A VISTA-3D/MONAI bundle is present in two `/usr/data` locations with the
   expected checkpoint, metadata, inference, and label files. It is the
   clearest local BeatIT-relevant model candidate, but the duplicate ownership
   and serving contract must be resolved before activation.
3. The home HF cache is mixed: 11 of 24 repository directories have non-empty
   snapshots, while 13 are metadata-only. Seven have standard encoder/model
   marker sets; the remainder must not be called complete.
4. `/usr/data` contains complete-looking MedGemma, Qwen-VL, LLM, Nemotron, and
   other service-owned bundles, as well as training-only and metadata-only
   caches. They are not automatically BeatIT capabilities.
5. No `.incomplete` files or broken links were observed in the audited HF
   snapshot trees. That signal does not establish model correctness or
   loadability.

## Risks and limitations

- This is a point-in-time inventory; downloads, training, cleanup, and cache
  deduplication can change sizes and snapshot state.
- `du -sh` is rounded apparent usage and includes cache/blob duplication; it is
  not a deduplicated storage total.
- Snapshot completeness is inferred from filenames, shard sequences, config,
  tokenizer, refs, and link state. No checksums, JSON semantic validation,
  archive validation, or model loading was performed.
- A complete-looking base model is not a serving endpoint. The BeatIT registry
  must continue to report configured, available, loaded, and serving states
  separately.
- `EverFrame*`, Docker storage, package environments, and generated build
  trees were not expanded into this BeatIT-specific catalog. Their presence is
  not being claimed absent.
- No secrets were inspected. Environment variable names were not needed for
  this inventory, and no credential values appear in this report.

## Final disposition

**DONE — bounded read-only local model inventory recorded.** The local model
evidence is sufficient for selection planning, with VISTA-3D as the strongest
BeatIT-relevant optional bundle and several complete-looking language/vision
bundles available only as external or service-owned candidates. No model is
promoted to runtime availability by this report; integration, provenance,
license, and loadability checks remain **OPEN**.
