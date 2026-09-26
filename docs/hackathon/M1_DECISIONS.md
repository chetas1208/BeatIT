# M1 decisions

- **BeatIT is the product name; DualBeat remains lineage.** Renaming the Python package and API namespaces would expand risk without improving the M1 foundation.
- **Registry before mesh rewrite.** The current procedural renderer is retained as geometry while semantic IDs and bindings become stable.
- **One imperative clock.** A shared clock is used instead of independent `requestAnimationFrame` phase refs so the heart and flow stay synchronized and future ECG/PV/Split Heart consumers can share timing.
- **Deterministic visual particles.** Existing random particle seeds were replaced with a stable low-discrepancy sequence so renders are reproducible.
- **No new dependency.** The repository has no frontend test runner, so M1 uses strict TypeScript/build validation and keeps the clock/registry dependency-free for straightforward future unit tests.
- **No backend formula changes.** Cardiac calculations, provenance, safety, and API contracts are outside the frontend M1 seam and remain untouched.
