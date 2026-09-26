# Agent 04 — `/usr/data` model and data inventory

**Inventory time:** 2026-09-26 17:46–17:52 UTC  
**Scope:** Read-only inventory of `/usr/data` model/data artifacts, ownership,
permissions, ACLs, symlinks, and safe follow-up actions.  
**Contribution:** Unique live `/usr/data` filesystem inventory, with a
permissions/data-boundary focus complementary to the repository's local model
inventory.  
**Change boundary:** No production code, model, dataset, permission, or
filesystem content was changed. No artifact was downloaded, copied, loaded, or
hashed.

## Plan

1. Inspect the mount, capacity, top-level roots, ownership, and mode bits.
2. Bound traversal to `/usr/data` with `find -xdev`; do not scan `/proc`,
   `/sys`, or `/dev`.
3. Classify model bundles, caches, datasets, sensor/audio/video data, and
   build/scratch artifacts by path and apparent size.
4. Check representative permissions, inherited ACLs, symlink targets, and
   group/other write/read exposure.
5. Record candidates, limitations, and safe next steps without activating or
   modifying any artifact.

## Evidence

All evidence below came from live read-only commands run from the BeatIT
workspace. `du` values are apparent filesystem usage and are rounded by the
system utility. Counts are regular files unless stated otherwise.

### Filesystem and top-level roots

| Observation | Result |
|---|---|
| Mount | `/usr/data` is `/dev/mapper/data--vg-data--lv`, `ext4`, mounted `rw,relatime` |
| Capacity at audit time | 2.7T total, 580G used, 2.2T available, 22% used |
| Root mode/owner | `drwxrwsr-x` (`2775`), `root:academic technology - srv-hh-306-96 - login` |
| `/usr/data/models` | 415G; owner `923873155`, same institutional group |
| `/usr/data/923873155` | 147G; owner `923873155`, same institutional group |
| Agent scratch/target/tmp | 73M / 19G / 2.8M; build or temporary state, not BeatIT model evidence |
| Other numeric roots | `917938221`, `918856775`, `922399059`, and `922933190` were each 4K at the audit depth; no candidate artifacts were observed there |

The root and major user-owned directories have a default POSIX ACL granting
the institutional group `rwx` (with a writable ACL mask). This is broader than
the nominal owner-only interpretation of the directory names and must be part
of any deployment or data-sharing decision.

### Model and model-cache candidates

These are presence/shape candidates only. Presence does not prove license
acceptance, compatibility with BeatIT, loadability, serving configuration, or
clinical suitability.

| Candidate/root | Live apparent size | Observed artifact evidence | Permission observation | Disposition |
|---|---:|---|---|---|
| VISTA-3D bundle | 832M | `models/vista3d/models/model.pt` is 871,970,895 bytes; MONAI metadata is present | Checkpoint `0644`, `923873155:domain users`; other-readable | Strongest BeatIT-relevant optional segmentation candidate; validate only through the existing lazy adapter |
| MedGemma cache | 8.1G | `medgemma/` has config, tokenizer, and two safetensors shards | Bundle directory `0755`; sampled files `0644`, other-readable | Optional medical language/vision candidate; no local serving contract was established |
| Qwen2.5-VL cache | 16G | `qwen25vl/` has config, index, tokenizer, and model shards | Bundle directory `0755`; sampled files `0644` | Optional multimodal candidate; not a BeatIT capability claim |
| Llama 3.1 8B Instruct | 30G | Four safetensors shards plus tokenizer/config; original-format files also exist | Bundle `0755`; sampled weights `0644`, other-readable | General-language candidate; activation is not justified by inventory alone |
| Qwen3 14B | 28G | Eight safetensors shards plus index/config/tokenizer | Bundle `0755`; sampled weights `0644`, other-readable | General-language candidate; larger runtime footprint than the minimum fallback |
| Mistral Small 3.1 24B | 90G | Ten safetensors shards and a consolidated safetensors file | Bundle `0755`; sampled weights `0644`, other-readable | Large general/multimodal candidate; apparent size must be reconciled with older repository notes before use |
| Gemma 4 E4B IT | 15G | `model.safetensors`, config, tokenizer | Bundle `0755`; sampled weight `0644`, other-readable | Additional general-language candidate not listed in the older local inventory |
| Gemma 4 26B A4B IT | 49G | Two safetensors shards, index/config/tokenizer | Bundle `0755`; sampled files `0644`, other-readable | Additional large candidate; no BeatIT runtime proof |
| Nemotron/HPC cache | 87G | Hugging Face caches include Nemotron 30B Omni FP8/NVFP4, Llama 3.1 Nemotron Nano VL, C-RADIO, and Piper ONNX | Cache files are generally other-readable; cache layout uses symlinks/blobs | External service cache; do not treat as a canonical BeatIT model root |
| TraceProof model server | 9.8G | Wav2Vec2, image-detection, CLIP, and Parakeet artifacts | Root has setgid/default ACL; sampled files are readable by others | Unrelated capability family; preserve owner boundary and do not repurpose |
| Solux model data | 38G | Geospatial, local-critic, embedding, and output manifests/models | Bundle files sampled as other-readable | Unrelated task-specific model/data root |
| Emotion detection outputs | 2.7G | CREMA-D/RAVDESS `.pth` checkpoints and result directories | Sampled files other-readable | Task-specific training/results; not a BeatIT model contract |
| SkillLLM stage-2 artifacts | 1.5G | LoRA/GLiNER and safe-wrapper artifacts | Sampled files other-readable | Training artifacts; a symlink points to a broken/mismatched path (see below) |

The current live filesystem contains more model families than
[`docs/models/LOCAL_MODEL_INVENTORY.md`](../../models/LOCAL_MODEL_INVENTORY.md)
lists. That repository document remains useful for BeatIT selection context,
but its model-size and candidate claims should not be treated as a complete
current `/usr/data` manifest.

### Data and non-model artifacts

| Root | Live apparent size and shape | Permission/data-boundary observation | Safe interpretation |
|---|---:|---|---|
| `/usr/data/923873155/EverFrame_Datasets` | 62G; 18G extracted `GRAB`; 1,350 `.npz`, 28 `.bz2`, and two `.zip` files (largest observed ZIP: `LARa_smplh_gendered.zip`, 12,680,397,693 bytes) | All 1,383 regular files were other-readable by mode bits; 26 were group-writable; the sampled archive was `0664` with effective group write through ACL | Separate project-owned dataset; do not expose or move into BeatIT data without provenance/license and owner approval |
| `/usr/data/923873155/mmcsg/MMCSG` | 70G; 60G audio, 6.4G video, ~2.2G each accelerometer and gyroscope; 530 each of `.wav`, `.mp4`, `.json`, `.rttm`, `.tsv`, and 1,060 `.npy` sensor files | All 3,718 regular files were other-readable by mode bits; 1,031 were group-writable; sampled metadata was `0664` with effective group write through ACL | Large multimodal dataset; treat metadata, voice, video, and sensor streams as potentially sensitive until provenance/access review is complete |
| `/usr/data/923873155/llm-models/hf_cache` | 15G; Qwen2.5-7B-Instruct Hugging Face cache with blobs/snapshots/locks | 33 regular files; 32 group-writable and 32 other-readable by mode bits; cache is not a clean model manifest | Cache/recovery material; do not use as an application dependency without pinning snapshot and checksums |
| `/usr/data/r8g-agentg-scratch/r8g.auredb` | 73M with assets/blobs/manifests/segments/WAL | Shared group/setgid scratch root | AUREDB scratch state, outside BeatIT scope; do not delete or repurpose |
| `/usr/data/r8g-agentg-target` | 19G, primarily Rust `debug/` output; `release/` is 198M | Group-writable build output | Build cache, not model/data evidence; no cleanup performed |
| `/usr/data/923873155/skillllm-thesis-build-deps` and `skillllm-thesis-tools` | 280M and 76M | User/group-owned toolchain files | Toolchain/build dependencies, not portable model artifacts |

### Permission, ACL, and link scan

The bounded `find /usr/data -xdev` scan found:

| Check | Result |
|---|---:|
| Regular files | 42,916 |
| Files with group or other write mode bits | 30,700 |
| Files with other-write mode bits | 0 |
| Directories | 3,506 |
| Directories with group or other write mode bits | 2,956 |
| Files with other-read mode bits | 42,029 |
| Symlinks | 1,547 |
| Absolute symlinks leaving `/usr/data` | 2 |
| Broken symlinks | 1 |

The two absolute links are TraceProof GenConViT weights pointing into
`/home/923873155/TraceProof/...`; they create a portability and packaging
dependency. The broken relative link is:

```text
/usr/data/models/skillllm-v2-stage2/artifacts/mistral-small-3.1-24b-skillspan-lora
  -> ../../SkillLLM_v2/results/skillspan_baselines/mistral-small-3.1-24b-instruct-2503/training
```

The target spelling/case does not resolve in the live tree. No link was
rewritten.

Representative ACL evidence:

- `/usr/data` and major user roots have default `group:<institutional-group>:rwx`
  and default `mask::rwx` entries.
- The VISTA checkpoint is nominally `0644`; its inherited institutional-group
  ACL is read-effective and its `other` entry is read-only.
- The EverFrame ZIP and MMCSG metadata samples are `0664`; their inherited
  institutional-group ACL is write-effective while `other` remains read-only.
- No `other::w` or other-write mode bit was observed in the full bounded scan.

## Result

1. `/usr/data` is healthy and spacious for local artifact retention, but it is
   a shared, group-accessible filesystem rather than an isolated private model
   vault.
2. VISTA-3D is present at the expected path and is the clearest BeatIT model
   candidate. MedGemma is also present, while the filesystem contains many
   unrelated language, geospatial, audio, vision, and training artifacts.
3. The live tree contains two substantial user data families, EverFrame and
   MMCSG, whose modalities and group ACLs require an explicit data-owner and
   provenance decision before any BeatIT integration.
4. The older repository model inventory is partial relative to the live tree;
   the live Mistral bundle is approximately 90G, and Gemma/Nemotron/Qwen-VL
   roots were also observed.
5. No artifact was proven runnable, compatible, licensed for BeatIT, served by
   the application, or suitable for patient-facing use. No model was loaded.

## Safe next steps

These are recommendations only; none were executed in this inventory.

1. **Owner and access review:** Ask the owners of the institutional ACL and
   each dataset root whether group read/write access is intended. Do not apply
   blanket `chmod` or ACL changes: model caches may be shareable while audio,
   video, sensor, or extracted datasets may require narrower access.
2. **Create an approved manifest:** For only the VISTA-3D and any explicitly
   selected BeatIT candidate, record absolute path, owner/group, exact bytes,
   modification time, license/provenance, and SHA-256 in a controlled manifest.
   Hashing should be scheduled and approved because it reads large weights.
3. **Reconcile repository documentation:** Update the model inventory only
   after owner approval and a deliberate selection decision; retain the
   distinction between presence, loadability, serving, and promotion.
4. **Repair portability before activation:** Resolve or remove the broken
   SkillLLM symlink under its owning project, and replace absolute TraceProof
   links with an owner-approved canonical root or explicitly mark them
   unavailable. This agent did not change either link.
5. **Keep BeatIT integration lazy and optional:** If VISTA-3D is evaluated,
   use the existing registry/adapter and a CPU-safe smoke test in an isolated
   environment. Preserve the procedural/deterministic fallback and do not
   copy weights into the repository or download duplicates.
6. **Treat MMCSG/EverFrame as restricted until cleared:** Verify dataset
   license, deidentification/provenance, retention, and access policy before
   using even metadata in BeatIT fixtures or demos. Do not ingest raw media.
7. **Separate disposable build state:** Leave AUREDB scratch, Rust target, and
   temporary roots to their owners. Any cleanup must be a separately approved,
   path-specific operation with a current process/lock check.

## Risks and limitations

- This is a point-in-time inventory; concurrent downloads, training jobs, or
  cleanup can change sizes, links, and permissions.
- `du` reports apparent usage, not deduplicated storage or physical extents.
- Mode-bit scans do not replace a complete ACL, identity/group-membership,
  export, backup, or mount-policy review. ACL samples were checked only on
  representative roots/files.
- File names and bundle structure are evidence of presence, not proof of
  correctness, license, provenance, privacy status, or model compatibility.
- No checksums, archive extraction, model loading, inference, network access,
  download, or production API test was performed.
- The scan intentionally stayed within `/usr/data` and used `-xdev`; it did
  not recursively inspect `/proc`, `/sys`, or `/dev`.

## Final disposition

**DONE — bounded read-only `/usr/data` inventory recorded.** The only
repository artifact added by this contribution is this report. No production
files, external artifacts, permissions, symlinks, models, or datasets were
modified, downloaded, moved, or deleted. Integration and permission changes
remain **OPEN** pending explicit owner/provenance review.
