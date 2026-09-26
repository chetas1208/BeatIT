# BeatIT Model Download Decisions

## Decision: no download

No model was downloaded or moved during this campaign.

The capability audit found that BeatIT's cardiac physiology, EF/SV/CO/MAP/QTc,
PV-loop, ensemble, Shadow Trial, Missing Piece, and fallback behavior are
deterministic. Embeddings and learned ECG inference are not required by the
current path. The local VISTA checkpoint is optional and structurally loadable,
but no compatible request-serving runner or endpoint is configured.

| Capability | Candidate | Local result | Download decision |
|---|---|---|---|
| Clinical language | local HF snapshots/provider-neutral adapter | Artifacts exist outside BeatIT, but no approved serving contract or active provider | Do not download; fallback remains authoritative |
| 3D segmentation | VISTA-3D 0.5.8 MONAI bundle | Checkpoint and metadata present; load smoke passed; inference runner absent | Do not download/repackage |
| Embedding | optional provider-neutral path | Not used by current evidence lookup | Not required |
| Learned ECG | none required | Deterministic ECG parsing/formulas cover current path | Not required |

Any future VISTA activation must pin the bundle's expected MONAI/PyTorch
versions, verify its license/use restrictions, and run a bounded inference
fixture before public exposure.
