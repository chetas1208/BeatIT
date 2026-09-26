# Medication Evidence Source Matrix

Federated, source-specific adapters with priorities, versioning, and license gates.
No single dataset is the source of clinical truth; no scraping.

| Source | Tier | Role | May hard-block? | Config |
|---|---|---|---|---|
| RxNorm | A | drug identity, RxCUI, ingredient, brand/generic | no (identity only) | `RXNORM_API_BASE` |
| RxClass | A | therapeutic/ATC/MED-RT class, class members | no | `RXCLASS_API_BASE` |
| DailyMed SPL | A | **preferred label**: contraindications, warnings, interactions, renal/hepatic/pregnancy, effective date | **yes** | `DAILYMED_API_BASE` |
| openFDA label | A | label fallback | **yes** | `OPENFDA_API_BASE`, `OPENFDA_API_KEY` |
| FDA Orange Book | A | generic-equivalence (TE codes) | no (equivalence only) | `ORANGE_BOOK_DATA_PATH` |
| DDInter 2.0 | B | supplemental drug–drug / duplication leads | **no** | `DDINTER_DATA_PATH`, `DDINTER_ENABLED` |
| DrugCentral | B | enrichment / cross-reference | **no** | `DRUGCENTRAL_DATA_PATH` |
| SIDER 4.1 | B | supplemental adverse-effect signal | **no** | `SIDER_DATA_PATH` |
| DrugBank | C | licensed enrichment | only if licensed | `DRUGBANK_*` (disabled w/o license) |
| Kaggle / scraped / blogs | D | **prohibited as authority** (dev fixtures only) | never | — |

## Policy rules (enforced)

- **DrugBank refuses to load** unless `DRUGBANK_LICENSE_CONFIRMED=true` and a data path
  is set (`source_registry.drugbank_loadable()`), and is never copied from mirrors.
- **DDInter alternatives** are leads only — never displayed until independently verified
  (normalize → guideline relevance → official label → full patient-specific re-check).
- **SIDER** can never hard-block and never marks an alternative "safer".
- **openFDA adverse-event reports** are never used as contraindication proof — label
  endpoint only.
- **Orange Book** equivalence does not resolve an ingredient-level contraindication; if
  the ingredient is the conflict source, generic equivalents are excluded.
- **Tier D** may be used only for UI fixtures / normalization stress tests, labeled
  *non-authoritative development fixture*.

## Offline demo posture

No official datasets are on the machine. The offline corpus
(`fixtures/careguard/corpus/`) provides short, clearly-labeled **synthetic** stand-ins
with real `canonical_source` URLs and computed hashes, so the engine runs without
network. Configure `*_DATA_PATH` (or `CAREGUARD_ALLOW_EXTERNAL_RESEARCH=true`) to use
approved licensed data. Ingestion scripts (`scripts/careguard/`) verify license,
version, checksum, and schema outside user requests.
