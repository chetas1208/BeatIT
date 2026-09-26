# M2 decisions

- Keep the procedural M1 geometry and add semantic proxy picking; replacing the working heart model would create unsupported anatomy claims.
- Use one canonical patient/report adapter. The report barrel delegates to `patient/adapter.ts` so status, evidence, limitations, and missing-data behavior cannot drift.
- Treat backend `LCx` and frontend `LCX` as the same canonical territory during lookup.
- Exclude the backend `global_systolic` observation from AHA segment-level findings; it describes global LV function.
- Keep electrical animation visualization-only and clock-driven; do not invent patient conduction velocities.
- Repair CareGuard's two inherited TypeScript integration errors at their source without weakening compiler settings.
