# BeatIT M2 agent plan

The lead integrator owns shared integration, `HeartScene.tsx`, app shell composition, final review, and validation. Agents have disjoint write scopes.

| Agent | Responsibility | Owned files/directories | Dependencies | Expected output | Status |
|---|---|---|---|---|---|
| 01 | Registry audit | `web/lib/heart/registry.ts`, `docs/hackathon/M2_ANATOMY_AUDIT.md` | M1 registry | coverage audit and safe corrections | integrated/reviewed |
| 02 | Picking and interaction | `web/components/heart/interaction/` | shared contracts | semantic hover/click state primitives | integrated/reviewed |
| 03 | Camera focus | `web/components/heart/camera/` | shared contracts | focus/reset controller | integrated/reviewed |
| 04 | Anatomy knowledge | `web/lib/heart/knowledge/` | registry | curated anatomy metadata | lead-integrated |
| 05 | Patient bindings | `web/lib/heart/patient/` | contracts, existing types | evidence-backed component adapter | integrated/reviewed |
| 06 | Provenance/evidence | `web/lib/heart/evidence/`, `web/components/heart/evidence/` | patient bindings | provenance model and display primitives | integrated/reviewed |
| 07 | Inspector UI | `web/components/heart/inspector/` | knowledge, patient, evidence | progressive disclosure inspector | integrated/reviewed |
| 08 | Component reports | `web/lib/heart/report/`, `web/components/heart/report/` | knowledge, patient, evidence | deterministic report model and view | integrated/reviewed |
| 09 | Visual interaction state | `web/components/heart/visual/` | registry, contracts | semantic render-state helpers | integrated/reviewed |
| 10 | Integration QA | `web/lib/heart/__tests__/`, `docs/hackathon/M2_QA.md` | all contracts | deterministic tests and QA matrix | integrated/reviewed |
| 11 | Electrical layer | `web/components/heart/electrical/` | registry, cardiac clock | visualization-only electrical layer | integrated/reviewed |
| 12 | AHA interaction | `web/lib/heart/aha/` | registry, contracts | lead-integrated through registry/adapter |
| 13 | Performance review | `docs/hackathon/M2_PERFORMANCE.md` | M1/M2 architecture | lead-integrated |
| 14 | Safety language audit | `docs/hackathon/M2_SAFETY_AUDIT.md` | all user-facing M2 copy | lead-integrated |
| 15 | CareGuard debt | `web/components/careguard/`, `web/lib/careguardApi.ts`, `web/lib/store.ts` | existing APIs/types | lead-integrated |

After implementation, the lead agent stopped parallel editing, reviewed every owned change, integrated only coherent work, and dispatched two independent adversarial reviewers (architecture and medical/data integrity). Twelve sub-agents were actually used across implementation and review; the remaining rows document lead-owned integration work.

## Adversarial review status

- Architecture reviewer: completed; findings addressed include canonical report ownership, single clock driver, electrical mounting, reduced-motion invalidation, and interaction-state alignment. Remaining proxy-geometry and generic-focus limitations are documented.
- Medical/data-integrity reviewer: completed; global-vs-regional finding leakage and LCx normalization were corrected, and global outputs are labeled explicitly.
