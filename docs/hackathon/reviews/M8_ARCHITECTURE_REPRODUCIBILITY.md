# M8 Architecture & Reproducibility Review (Reviewer D)

Status: **conditional pass**  
Date: 2026-09-26

## Pass

- Single numerical authority: canonical `_evaluate` / persisted `projection_base`.
- Deterministic `analysis_id` derived from ensemble id, target, and engine version.
- Immutable SQLite persistence; idempotent reads; API sub-resources slice stored payloads without recomputation drift.
- Versioned methods: `uncertainty-impact-heuristic-v1`, `evidence-priority-score-v1`, `m8-evidence-map-v1`.
- Golden fixtures lock impact-ranking invariants and shadow-effect driver presence.

## Conditional

- Process-local sensitivity cache is optional and not yet wired into the engine hot path (documented module + tests only).
- Frontend displays backend payloads only; shadow-effect targets require explicit API request fields in UI (bounded surface).

## Fail

- None blocking Tier-1 release scope.
