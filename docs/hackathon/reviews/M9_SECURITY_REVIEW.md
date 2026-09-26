# M9 Security Review

Reviewed: 2026-09-26 UTC  
Method: read-only source/configuration audit. No implementation files changed.

## Verdict

**CONDITIONAL / SYNTHETIC DEMO-ONLY. NOT SAFE FOR PATIENT DATA.**

The client has bounded mode routes, does not persist case payloads in browser
storage, and does not expose provider credentials in the reviewed code. The
backend remains unauthenticated, returns patient-bearing case state by ID, and
uses wildcard credentialed CORS. M9's documented opaque-artifact deep-link and
reload contract is not implemented by the current route shell.

## Findings

### PASS — mode URLs contain no clinical payload or credentials

- `web/app/[mode]/page.tsx:5-8` accepts only the five `isBeatITMode` values;
  invalid modes use `notFound()`.
- `web/lib/product/navigation.ts:3-20` writes only `/${mode}` to history.
  It does not serialize patient notes, files, measurements, model output,
  tokens, or credentials.

### OPEN — documented deep-link privacy/lineage contract is not implemented

- `docs/hackathon/M9_PRODUCT_STATE.md:230-250` requires bounded opaque IDs,
  backend authorization, lineage checks, and safe handling of copied links.
- The current route reads only the pathname mode and ignores query parameters;
  it cannot rehydrate or validate case, snapshot, ensemble, scenario, trial, or
  analysis identity. Current URLs must not be presented as private record links.

### PASS — no patient-data browser persistence found

- `web/components/safety/DisclaimerModal.tsx:13-18,36-42` stores only the
  boolean disclaimer acknowledgment.
- `web/lib/store.ts:131-173` keeps case/results/traces in memory and resets to
  empty state; no `sessionStorage`, `indexedDB`, or cookie-based case storage
  was found under `web/`.

### OPEN — unauthenticated case and upload access exposes patient-bearing state

- `python/hearttwin/api.py:730-735` returns the complete case for a supplied
  `case_id` without authentication, ownership, or tenant checks.
- `python/hearttwin/api.py:913-952` accepts medical uploads and preserves
  filenames/storage metadata after checking only case existence.
- `python/hearttwin/tools/storage.py:50-80` stores complete case JSON in Redis
  or process memory; the model can include notes, files, source metadata, and
  derived cardiac state.

### OPEN — wildcard credentialed CORS

- `python/hearttwin/api.py:111-117` sets `allow_origins=["*"]`,
  `allow_credentials=True`, and all methods/headers.
- `web/lib/api.ts:109-127` currently sends no application auth header, so no
  active browser-session theft path was found in the client. The server default
  is still unsafe for any future cookie or bearer-auth deployment.

### PASS — safety/demo labeling is visible, but not access control

- `web/components/safety/DisclaimerModal.tsx:45-75` states educational use,
  no diagnosis, and no treatment recommendations.
- `python/hearttwin/api.py:104-108` labels the API educational-only; normal
  case responses carry the canonical disclaimer.
- `docs/hackathon/M9_PREFLIGHT.md` already records security as demo-only.

The disclaimer does not provide authentication, consent, privacy, retention,
encryption, or de-identification. Keep all demo records synthetic and visibly
non-patient.

### PASS — no credential leakage found in the reviewed source

- `web/.env.example` uses placeholders; `web/lib/api.ts` reads only the public
  `NEXT_PUBLIC_API_BASE` and adds no provider/API-key headers.
- `python/hearttwin/api.py:378-413` exposes configuration booleans/labels, not
  keys or tokens.
- `.gitignore:16-18,24-38` and `web/.gitignore:33-36` exclude env files,
  credentials, private keys, and common medical uploads.

This is a repository finding only; deployment settings, logs, browser tooling,
and external Weave/Redis traces were not inspected.

## Source-audit disposition

Keep M9 **synthetic/demo-only**. Before patient data: add authentication and
ownership checks, restrict CORS, implement authorized opaque-ID rehydration and
lineage validation, minimize/encrypt/retain data under policy, and verify that
secrets are absent from bundles, URLs, logs, screenshots, and third-party
traces.
