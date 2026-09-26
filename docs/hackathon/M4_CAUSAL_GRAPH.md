# M4 causal graph

The M4 graph is a typed explanation of deterministic propagation. It is not an
LLM plan and it does not infer physiology from prose. `web/lib/twin/scenario/
propagation.ts` owns the graph definition and explicit relationships.

## Core path

```text
parameter change
  ├─ preload ───────────────→ EDV ─┐
  ├─ afterload ─────────────→ ESV ─┼→ SV → CO
  ├─ contractility ─────────→ ESV ─┘  ↑
  └─ heart rate ─────────────────────┘

SVR → MAP
```

Each edge carries a signed direction and a deterministic source reference. The
propagation result contains node deltas, affected node IDs, paths, warnings,
and the `deterministic: true` marker. UI code only renders this result.

## Scientific boundary

These are bounded educational relationships built on the project's canonical
identities (`SV = EDV - ESV`, `EF = SV / EDV`, `CO = HR × SV / 1000`). They are
not calibrated patient-specific predictions. The local language model may
explain a completed trace later; it may not create nodes, edges, or numeric
values.
