# M10.5 Reproducibility

- Synthetic seed is idempotent and records SHA-256 fixture hashes.
- Release golden manifest is generated from checked-in source fixtures.
- Seeded ensemble responses are byte-identical across repeated requests in
  temporary SQLite verification.
- Shadow Trial replay is idempotent and preserves same-sample identity.
- Missing Piece responses reload exactly from temporary SQLite.
- Remote/browser reproducibility remains open.
