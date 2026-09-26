# M4 scenario model

An observed `TwinSnapshot` is copied into an immutable origin record. A
scenario holds that origin, a detached hypothetical state, its explicit
parameter changes, derived component deltas, and provenance. The observed
timeline is never written to during propagation.

```text
observed snapshot
      │
      ├─ originSnapshotId + originTimestamp
      └─ deep clone
             │
             ▼
      deterministic scenario state
```

Scenario history is a local value stack (`past`, `present`, `future`) so undo,
redo, and reset do not mutate the source timeline or a shared singleton. Local
persistence uses a versioned JSON envelope and rejects malformed/non-JSON
values.

All scenario surfaces must say **HYPOTHETICAL SIMULATION**. A scenario result
is not clinical evidence, a diagnosis, or a treatment recommendation.
