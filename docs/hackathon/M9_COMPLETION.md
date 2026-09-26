# M9 Unified Product Experience Completion

Status: **INCOMPLETE — product shell delivered; live browser and reload gates open**  
Date: 2026-09-26

## Delivered

- A single BeatIT shell with exactly five primary spaces: TWIN, EXPERIMENT,
  COMPARE, EVIDENCE, and REPORT.
- Mode routes `/twin`, `/experiment`, `/compare`, `/evidence`, and `/report`,
  with a fail-closed invalid-mode route and compatibility root `/`.
- Drawer navigation with Escape, outside-click, focus entry/restoration, Tab
  containment, and body-scroll protection.
- Typed product context, privacy-safe mode-only URLs, deterministic report
  contracts, explicit source-status badges, return-to-Twin action, and an
  honest Compare prerequisite state.
- Existing HeartScene, causal explorer, Shadow Trial, Split Heart, plausible
  twins/Missing Piece, provenance, and computational report surfaces composed
  without changing numerical engines.
- M9 information architecture, state, interaction, design, human-factors,
  accessibility, performance, test-matrix, QA, decisions, and adversarial
  review documentation.

## Verification

```text
web TypeScript                         passed
web scoped ESLint                      passed
web product runtime tests              3 passed
web Next production build              passed
HTTP / /twin /experiment /compare      200
HTTP /evidence /report                 200
HTTP invalid mode                      404
git diff --check                       passed for tracked M9 scope
```

The full Python regression command was also run: **1227 passed, 4 failed, 5
skipped, 6 xfailed**. The four failures are pre-existing assistant/adversarial
expectation mismatches (`test_assistant_router.py` and
`test_decision_adversary.py`); no M9 Python files changed.

## Agent gate

At least 20 substantive, reviewed M9 contributions are recorded in
`M9_AGENT_PLAN.md`, including preflight, product contracts, interaction/design
audits, surface reviews, synthetic/medical/accessibility/security/performance
reviews, and responsive/architecture checks. Duplicate or placeholder work is
not counted.

## Open gates

- Mandatory browser journey, WebGL, responsive, keyboard, and assistive-
  technology sign-off could not run: Chromium lacks `libasound.so.2` and the
  Playwright Firefox executable is unavailable.
- Persisted artifact rehydration is not implemented for direct reloads;
  comparison/evidence/report context remains in current in-memory stores.
- Click-to-inspect provenance is partially delivered: `ProvenanceBadge`,
  `ProvenanceInspectPanel`, and `InspectableClaim` support keyboard-open source
  inspection; universal metric-level wiring remains open.
- M5.5, M6, and M7 inherited gates remain open as documented in preflight.
- Python baseline failures above must be resolved or explicitly quarantined
  before a release claim.

M9 is therefore ready for the next integration war-room audit, but not ready
to claim a fully verified product release or to start M10 automatically.
