# M4 decisions

1. **Observed and hypothetical states stay separate.** Scenario code deep
   clones state and stores origin metadata; no scenario value becomes evidence.
2. **The physiology engine is deterministic.** Explicit formulas and bounds
   produce every numeric result. Model providers are explanation-only.
3. **The first parameter set is deliberately small.** Five defensible inputs
   are more auditable than a broad control surface with unsupported pathways.
4. **PV and 3D views are projections.** They react to scenario values for the
   demo, but the app does not claim quantitative geometric deformation.
5. **No new model download.** Existing local VISTA-3D is reused at the adapter
   boundary; language and retrieval remain independently optional.
6. **Provider failure is isolated.** The deterministic twin and scenario engine
   do not require a model endpoint, GPU, Redis, or Weave.
