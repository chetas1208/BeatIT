# BeatIT Final Architecture

```mermaid
flowchart TD
  Evidence[Evidence and provenance] --> Twin[Temporal cardiac twin]
  Twin --> Physics[Deterministic physiology core]
  Physics --> Ensemble[Seeded plausible-twin ensemble]
  Ensemble --> Trial[Same-sample Shadow Trial]
  Trial --> Compare[Split Heart comparison]
  Ensemble --> Missing[Bounded sensitivity and Missing Piece]
  Twin --> Heart[Semantic procedural 3D heart]
  Compare --> Heart
  Missing --> Report[Unified computational report]
  Local[Optional local/provider-neutral models] -. explain/extract only .-> Twin
  Health[Live/readiness/system status] --> Local
  Health --> Physics
```

## Authority boundaries

- Python deterministic physiology is the authority for numerical outputs.
- M5.5 ensemble, M6 Shadow Trial, and M8 Missing Piece contracts remain
  versioned and backend-authoritative.
- Next.js composes state and renders visualizations; it does not reimplement
  physiology or silently repair persisted results.
- Local model/runtime calls explain, extract, or summarize only. They never
  calculate cardiac physiology.
- VISTA-3D is optional imaging infrastructure and is not required for startup
  or the procedural demo heart.

## Self-host boundary

FastAPI and Next.js bind to loopback under `deploy/beatit`; nginx/Caddy handles
public routing, TLS, payload limits, compression, and SSE buffering. PostgreSQL,
Valkey, and artifact storage are external dependencies only when explicitly
configured. The current local SQLite/file-backed stores must not be described as
an authenticated multi-user clinical data platform.
