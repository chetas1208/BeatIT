# BeatIT Release Checklist

## Release candidate gates

- [ ] Scope freeze accepted; no new science or primary product surface.
- [x] Deterministic demo fixture and seed/reset commands exist.
- [x] Liveness/readiness/system-status endpoints exist and are tested.
- [x] Direct Python suite is green with documented skips/xfails.
- [x] Direct frontend TypeScript, scoped lint, runtime, and production build pass.
- [ ] Self-host reverse proxy exercised on the target public hostname.
- [ ] Persistence restart evidence for every claimed artifact store.
- [ ] Browser keyboard/AT/WebGL evidence in a supported browser environment.
- [ ] Chaos evidence for model, network, backend, and database failures.
- [ ] Security, scientific integrity, and credibility reviews closed.
- [ ] Three-minute demo rehearsed repeatedly on the release candidate.

Current decision: **DO NOT SHIP yet**. Open gates are recorded in
`docs/hackathon/M10_COMPLETION.md` and `M10_WAR_ROOM.md`.
