# M10 Release Blockers

## P0 — do not ship

- No exercised public reverse-proxy deployment with TLS, SSE buffering, and
  restart evidence.
- No supported-browser accessibility/WebGL/reload sign-off.
- Synthetic/demo-only privacy boundary remains: no authentication, restricted
  CORS policy, or hosted multi-user persistence authority.

## P1 — release evidence open

- Full frontend runtime has nine inherited failures documented in
  `M10_REGRESSION_REVIEW.md`.
- Model, network, backend, and database fault injection has not been run.
- Persistence restore and subprocess restart have not been demonstrated for
  every claimed artifact store.
- The contribution-count gate is closed at 22 reviewed, non-duplicative
  contributions; technical release gates below remain open independently.

## P2 — cleanup after the war room

- Resolve package-manager ignored-build-script policy so `pnpm` wrappers can be
  used as the primary frontend evidence command.
- Remove or quarantine remaining inherited frontend runtime contract failures.
- Replace deprecation warnings in future maintenance work.

## Explicit WONTFIX for M10

- No new physiology, uncertainty, causal, evidence, or visualization method.
- No clinical validation, diagnosis, treatment, or emergency behavior.
- No claim that a local benchmark is hosted-capacity evidence.
