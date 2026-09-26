# M8 Decisions (milestone-local)

Canonical product decisions also appear in root [`Decisions.md`](../../Decisions.md).

1. Tier-1 only for release: local finite differences + labeled uncertainty-impact heuristic + Evidence Priority Score.
2. No fake Sobol/Shapley/EIG terminology at the public boundary.
3. Shadow Trial effect sensitivity uses same-sample pairing with **fixed scenario targets**.
4. Cross-parameter ranking requires normalized sensitivity; raw derivatives stay unit-specific.
5. Evidence map is a small reviewed allowlist; callers cannot add silent mappings.
6. Persistence: immutable SQLite keyed by deterministic `analysis_id`.
7. 3D/spatial uncertainty: scalar mapped annotations only; no fabricated geometric fields.
8. LLM may paraphrase deterministic `MissingPieceResult`; it must not re-rank evidence.
