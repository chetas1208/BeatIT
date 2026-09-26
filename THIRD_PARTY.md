# Third-Party Software, Models, and Data

This file records third-party components evidenced by BeatIT's package manifests,
model registry, and data provenance files. It is an attribution aid, not legal
advice and not a replacement for the license text supplied by each project or
dataset.

BeatIT does not currently contain a top-level project license. Do not infer that
the repository's own source code is open source, or that third-party licenses
grant permission to use BeatIT code. Before redistribution, preserve upstream
notices and review the exact versions in `pnpm-lock.yaml`, `web/pnpm-lock.yaml`,
and the deployed Python environment.

## Application dependencies

The tables cover direct dependencies declared in `web/package.json`,
`pyproject.toml`, and `requirements.txt`. Lockfiles also contain transitive
packages whose notices remain the responsibility of a distributor.

### Frontend

| Component | Role in BeatIT | Upstream license |
|---|---|---|
| Next.js, React, React DOM | Web application and rendering | MIT |
| Three.js, React Three Fiber, Drei | 3D cardiac visualization | MIT |
| Plotly.js, react-plotly.js | Physiological charts | MIT |
| Motion | Interface animation | MIT |
| Zustand | Client state | MIT |
| Zod | Runtime schema validation | MIT |
| Phosphor Icons | Icons | MIT |
| OpenAI JavaScript SDK | Optional provider client | Apache-2.0; provider terms also apply |
| Anthropic TypeScript SDK | Optional CareGuard provider client | MIT; provider terms also apply |
| Tailwind CSS and PostCSS integration | Styling/build tooling | MIT |
| TypeScript, ESLint, eslint-config-next | Development and validation tooling | Apache-2.0 / MIT as applicable |

### Python backend

| Component | Role in BeatIT | Upstream license |
|---|---|---|
| FastAPI, Uvicorn, Pydantic | HTTP API, server, and contracts | MIT |
| NumPy | Numerical arrays and deterministic computation | BSD-3-Clause |
| SciPy | Scientific computation | BSD-3-Clause |
| HTTPX | Outbound HTTP clients | BSD-3-Clause |
| Pillow | Image handling | HPND |
| pypdf | PDF parsing | BSD-3-Clause |
| python-multipart | Upload parsing | Apache-2.0 |
| python-dotenv | Local environment loading | BSD-3-Clause |
| Redis Python client | Optional Redis persistence/memory | MIT |
| OpenAI Python SDK | Optional provider-neutral language client | Apache-2.0; provider terms also apply |
| CopilotKit Python package | Copilot backend integration | MIT; verify the selected release and any separately hosted service terms |
| Mangum | Optional ASGI adapter | MIT |
| boto3 | Optional AWS/Bedrock client | Apache-2.0 |
| Anthropic Python SDK | Optional CareGuard language client | MIT; provider terms also apply |
| PyYAML | Optional CareGuard configuration | MIT |
| psycopg | Optional CareGuard PostgreSQL client | LGPL-3.0-only |
| pytest, pytest-asyncio | Test tooling | MIT / Apache-2.0 |

Version ranges in the Python manifests are not a reproducible license inventory.
Generate a version-pinned software bill of materials from the release environment
before distributing binaries or containers.

## Optional models and model-facing integrations

| Component | Repository status | Licensing/usage boundary |
|---|---|---|
| VISTA-3D | Optional local medical-segmentation adapter. `models/manifest.json` references a VISTA-3D 0.5.8 checkpoint outside this repository; weights are not bundled. | MONAI/VISTA-3D software and model artifacts have their own notices and terms. Verify the license shipped with the exact checkpoint before use or redistribution. A code license must not be assumed to cover model weights or training data. |
| MONAI | Runtime named by the VISTA registry; not a declared BeatIT application dependency. | Apache-2.0 for the upstream software. This does not establish rights to a separate checkpoint. |
| Laya | Optional routing adapter and deterministic fallback are present in source; Laya is not declared as an installed package in the audited manifests. | No Laya code or license file was found vendored in this repository. Obtain and preserve the license for any separately installed Laya distribution before shipping it. |
| AWS Bedrock / OpenAI / Anthropic services | Optional hosted language providers behind provider-aware adapters. | Cloud services, not redistributed software. Account, model-provider, acceptable-use, and data-processing terms apply. They are not numerical authorities for BeatIT physiology. |
| NVIDIA Build / Nemotron | Historical evaluation material only; the active assistant architecture documents this route as removed. | Do not represent NVIDIA inference as an active runtime dependency. Historical benchmark artifacts remain subject to the service/model terms that applied when generated. |

The deterministic cardiac engine is BeatIT source code, not a third-party model.
External language models may route or explain tool output; they do not establish
canonical physiological values.

## Datasets and terminology sources

No dataset entry below permits BeatIT to merge unrelated subjects into one
patient. Missing modalities must remain missing. Preserve source attribution,
version, modification notices, and provenance in every redistributed derivative.

| Source | Repository use/status | License or access terms | Public redistribution boundary |
|---|---|---|---|
| PTB-XL 1.0.3 | Real ECG demo cases and local research data | CC BY 4.0; PhysioNet DOI `10.13026/kfzx-aw45` | Permitted with attribution, license link, and modification notice. Do not commit unnecessary raw WFDB data. |
| UCI Heart Failure Clinical Records | Real clinical demo cases | CC BY 4.0; DOI `10.24432/C5Z89R` | Permitted with attribution, license link, and modification notice. It contains no raw ECG or echo modality. |
| eICU Collaborative Research Database Demo 2.0.1 | Deidentified structured EHR data used by the data pipeline | ODbL 1.0 | Preserve attribution and ODbL notices for redistribution and derived databases. |
| MIMIC-IV Clinical Database Demo 1.0 | Separate deidentified validation/demo cohort | ODbL 1.0 per the repository's preserved source notice | Keep separate from other cohorts; repository policy limits patient-level publication and requires attribution. |
| MIMIC-IV, MIMIC-IV-ECG, MIMIC-IV-ECHO | Optional credentialed local data | PhysioNet credentialing and applicable DUA/module terms | Do not commit or publicly re-host patient rows, identifiers, waveforms, measurements, or DICOM. Use only in an approved controlled environment. |
| CAMUS and TED | Local imaging research/evaluation | CC BY-NC-SA 4.0 plus publisher research-only wording recorded by the repository | `NO_GO` for the public demo pending written terms clarification. |
| Clinical Ultrasound Image Repository | Local imaging/VISTA evaluation | CC BY-NC 4.0 | Not approved for the sponsored public demo; do not publicly mirror artifacts. |
| EchoNet-Dynamic | Reference or optional registered local data | Dataset-specific Stanford/AIMI terms | No videos in Git; confirm current terms for any use or hosting. |
| Synthea | Synthetic fallback generation | Apache-2.0 | Keep records explicitly labeled synthetic and non-PHI. |
| RxNorm / RxNav | Medication normalization terminology/API metadata | U.S. National Library of Medicine terms | Review NLM terms for redistributed terminology content; identifiers and links alone do not confer rights to unrelated drug data. |
| openFDA drug-label API | Public label evidence metadata | U.S. FDA/openFDA terms and source-specific label notices | Preserve source links and do not present retrieved text as patient-specific advice. |
| FHIR | Interoperability format and terminology references | HL7 FHIR license and trademark terms | FHIR compatibility does not grant rights to source clinical data or third-party code systems. |

Repository-generated fixtures under `fixtures/hearttwin/` and the synthetic
cohort are described as synthetic and non-PHI. Their structure may be informed
by public datasets, but the fixture documentation states that source dataset
contents were not copied. This statement does not change BeatIT's currently
unspecified project-source license.

## Preserved notices and authoritative repository records

- `data/LICENSES.md` records packaged data licenses and preserved raw-source
  notice locations.
- `data/demo/real-cases/LICENSE_MANIFEST.json` records public-demo gates for real
  demo sources.
- `docs/data/REAL_DATA_LEGAL_MATRIX.md` records credentialed-data restrictions.
- `docs/data/OPEN_DATA_SOURCE_MATRIX.md` records source versions and local/public
  use boundaries.
- `models/manifest.json` records optional model artifacts without bundling them.

If this summary conflicts with an upstream license, dataset agreement, DUA, or
preserved source notice, the upstream terms control. Resolve ambiguity before
publishing data, checkpoints, containers, or a public demo.
