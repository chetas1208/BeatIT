# BeatIT computational credibility

## Authority and reproducibility

The M5.5 ensemble API is a versioned Python contract (`m5.5-ensemble-projection-v1`). It samples validated
input distributions with a recorded seed, rejects out-of-support or
physiologically invalid samples, propagates accepted inputs through deterministic
cardiac calculations, and returns the accepted samples plus descriptive
statistics and provenance. The frontend consumes that response; it is not a
second numerical authority.

The ensemble payload is stored in a local SQLite provider keyed by its stable
ID. Retrieval therefore survives an API process restart when the configured
database path is retained. The explicit provider is `sqlite`; an in-memory
provider is not used as an implicit production fallback. Storage failures are
returned as an explicit service-unavailable response rather than silently
discarding an ensemble.

This local provider is a hackathon persistence seam, not an authenticated
patient-data store. The database and API must remain on a trusted development
or demo network; production deployment requires authenticated ownership checks,
restricted CORS, encryption/retention controls, and a hosted data provider.
The local database directory is created with owner-only permissions and its
SQLite file is excluded from version control.

## Interpretation limits

The model is an educational digital-twin demonstrator. Input distributions are
bounded proxies and currently assume independence because no validated joint
correlation model is available. The 5th–95th percentiles summarize accepted
deterministic simulations; they do not estimate a patient's probability or a
clinical confidence/credible interval. Synthetic replay inputs remain synthetic
and are labeled as such.

No output should be used for diagnosis, treatment, emergency triage, or medical
decision-making. Existing safety disclaimers remain part of the API surface.

## Evidence status

The Python 3.13 regression suite, backend contract tests, six canonical golden
ensemble fixtures, subprocess persistence test, frontend TypeScript/build
checks, frontend lint, and an alias-aware frontend adapter runtime smoke test
have evidence. The frontend does not reproduce the backend vectors; it maps
the versioned response contract. Browser and assistive-technology validation
remain environment-dependent. Pointwise PV-loop uncertainty is intentionally
unavailable, and component uncertainty is limited to explicitly mapped scalar
outputs.
