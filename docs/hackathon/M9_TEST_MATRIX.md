# M9 Test Matrix

This matrix is the release checklist for each of the five product spaces. A
build or TypeScript pass does not substitute for browser evidence.

| Space | Load | Keyboard | Error | Empty | Synthetic/model offline | Reload | Deep link | Responsive |
|---|---|---|---|---|---|---|---|---|
| TWIN | heart, timeline, anatomy, source | focus heart controls and timeline | backend unavailable | no case/timeline | synthetic badge and no live claim | preserve safe route, clear stale data | `/twin` | 360px and wide |
| EXPERIMENT | causal controls, run state, Shadow Trial | labels, sliders, buttons, live status | failed run retains reason | no selected snapshot/ensemble | hypothetical and synthetic labels | no stale result after origin change | `/experiment` | controls stack |
| COMPARE | paired split heart and phase controls | both heart views and clock | invalid pair | no selected pair | counterfactual boundary | close/reopen without recomputation | `/compare` | split collapses |
| EVIDENCE | uncertainty/provenance/Missing Piece | target selector, disclosure, retry | API failure | no ensemble/evidence | unavailable is explicit | no stale analysis | `/evidence` | tables scroll |
| REPORT | all sections and limitations | headings, links, disclosures | partial session | empty sections | status legend | route-only context, no patient URL data | `/report` | readable single column |

## Automated gates

- `web/node_modules/.bin/tsc --noEmit`
- `web/node_modules/.bin/eslint components/product components/layout/AppShell.tsx lib/product app/[mode]/page.tsx`
- `web/node_modules/.bin/next build`
- `git diff --check`

## Browser gate

Run the mandatory journey in `M9_QA.md` in a real browser at 360px and a wide
viewport. Record focus, escape/outside close, resize, WebGL, and assistive
technology evidence separately. The inherited environment currently lacks a
working Chromium audio library and Firefox, so no browser signoff is implied by
the automated commands above.
