# M10.5 Ship Decision

## Decision: **DO NOT SHIP**

The deterministic local product and its major backend persistence seams are
verified. Release certification is withheld because browser E2E, public
proxy/TLS deployment, external dependency fault injection, live model runtime,
and patient-data security hardening are not closed.

This decision is conservative and evidence-based; it does not indicate that
the local synthetic demo path is broken.

**Latest automated evidence (2026-09-26):** `./scripts/verify-release.sh --deep`
passed end-to-end for env, secrets, **1314** pytest, frontend runtime, API
persistence, loopback deployment, demo preflight, and HTTP case pipeline smoke.
See `artifacts/release-verification.json` and `docs/release/E2E_RESULTS.md`.
