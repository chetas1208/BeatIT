# M10.5 Verification Matrix

Legend: **PASS** = executed evidence this campaign · **PARTIAL** = local/subsystem only · **OPEN** = not closed · **N/A** = optional capability

| Capability | Unit | Integration | API | Browser | Persistence | Failure | Offline | Provenance | Status |
|---|---|---|---|---|---|---|---|---|---|
| Semantic Heart | PASS | PASS | PASS (operate) | PARTIAL | N/A | PARTIAL | PASS | PASS | PARTIAL |
| CardiacClock / timeline | PASS | PASS | PASS | PARTIAL | N/A | OPEN | PASS | PASS | PARTIAL |
| Anatomy / LV inspect | PASS | PASS | PASS | OPEN | N/A | OPEN | PASS | PARTIAL | PARTIAL |
| Causal experiment | PASS | PASS | PASS | OPEN | N/A | OPEN | PASS | PASS | PARTIAL |
| Probabilistic twin | PASS | PASS | PASS | OPEN | PASS | PARTIAL | PASS | PASS | PARTIAL |
| Shadow Trial | PASS | PASS | PASS | OPEN | PASS | PARTIAL | PASS | PASS | PARTIAL |
| Split Heart | PASS | PASS | PARTIAL | OPEN | N/A | OPEN | PASS | PASS | OPEN |
| Missing Piece | PASS | PASS | PASS | OPEN | PASS | PASS (no model) | PASS | PASS | PARTIAL |
| Report | PASS | PARTIAL | PARTIAL | OPEN | PARTIAL | OPEN | PASS | PARTIAL | OPEN |
| Local language model | N/A | PARTIAL | PASS (status) | N/A | N/A | PARTIAL | PASS | N/A | OPTIONAL |
| VISTA-3D | N/A | OPEN | OPTIONAL | N/A | N/A | PARTIAL | PASS (procedural) | N/A | OPTIONAL |
| Storage / SQLite | PASS | PASS | PASS | N/A | PASS | OPEN | PASS | PASS | PARTIAL |
| Deployment | N/A | PASS | PASS | PARTIAL (HTTP) | OPEN | PARTIAL | PASS | N/A | PARTIAL |

Evidence commands: `./scripts/verify-release.sh --deep`, `docs/release/E2E_RESULTS.md`.
