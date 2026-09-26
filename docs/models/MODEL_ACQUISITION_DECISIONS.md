# Model acquisition decisions

## Decision: no download

No model was downloaded. The relevant local VISTA-3D checkpoint is already
available, and local language candidates are already present under `/usr/data`.
Downloading another copy would increase disk and VRAM pressure without closing
a demonstrated capability gap.

## Minimum portfolio

| Capability | Decision | Reason |
|---|---|---|
| 3D medical segmentation | Reuse local VISTA-3D checkpoint | Relevant CT bundle exists and its state dict loads; expose through the optional adapter and preserve procedural-heart fallback |
| Explanations/Q&A | Keep provider-neutral endpoint with deterministic fallback; MedGemma is the local candidate for a future explicit local server | The current app already has a provider-neutral intelligence boundary; no safe local serving endpoint or structured-output smoke test is configured |
| Embeddings/retrieval | Skip | Current provenance/evidence lookup is deterministic and does not require semantic retrieval |
| ECG deep model | Skip | Existing ECG feature extraction and deterministic cardiac formulas cover the current demo; no measured gap justifies another checkpoint |
| OCR | Skip | Existing PDF/image extraction is sufficient for current fixtures; no OCR gap was demonstrated |

## Activation policy

Set `BEATIT_SEGMENTATION_MODEL` to an approved checkpoint path (or use the
metadata manifest default on this host). Set `BEATIT_LANGUAGE_MODEL` only when
a local inference server/loader has been validated. The model registry never
loads weights during API startup. Every optional capability must continue to
degrade to procedural geometry, deterministic reports, or provenance lookup.
