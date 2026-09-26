# M9 Information Architecture — Unified Five-Space Product

Status: **normative M9 product contract**  
Date: 2026-09-26

## Scope

M9 organizes the existing BeatIT capabilities into exactly five primary
spaces, in this order:

1. `TWIN`
2. `EXPERIMENT`
3. `COMPARE`
4. `EVIDENCE`
5. `REPORT`

There is no primary `HOME`, `DASHBOARD`, `ANALYTICS`, `ASSISTANT`, or
`SETTINGS` space. The application root resolves to `TWIN`; it does not add a
sixth navigation item. Existing numerical engines and persisted artifacts
remain authoritative. M9 changes their presentation and movement between
surfaces, not their calculations.

## Product hierarchy

```text
BeatIT
├── shared shell
│   ├── active case and source context
│   ├── five-item primary navigation
│   ├── run/status feedback
│   └── contextual utilities
├── TWIN                  /twin
│   ├── current 3D and physiology view
│   ├── longitudinal timeline
│   └── contextual component inspection
├── EXPERIMENT            /experiment
│   ├── bounded causal scenario
│   ├── plausible-twin ensemble
│   └── paired Shadow Trial
├── COMPARE               /compare
│   ├── Split Heart pair
│   ├── paired metrics and differences
│   └── comparison timing and context
├── EVIDENCE              /evidence
│   ├── source and artifact provenance
│   ├── local sensitivity and uncertainty drivers
│   └── Evidence Priority Score
└── REPORT                /report
    ├── deterministic journey summary
    ├── sources, assumptions, and limitations
    └── safety and artifact identity
```

The paths above are the canonical M9 product paths. Query parameters may carry
opaque artifact identifiers needed to restore a view, but must not contain raw
uploaded content, clinical text, or other sensitive payloads. The route/state
contract may define the exact identifier names; it must not create additional
primary routes.

## Surface ownership

Each capability has one owning space. Other spaces may show a compact,
read-only summary with a link to the owner, but must not provide a second
editor or recompute the owner's result.

| Space | User question | Owns | Requires | Does not own |
|---|---|---|---|---|
| `TWIN` | “What source-backed state am I looking at?” | The selected case snapshot, 3D heart, physiology charts, timeline cursor, source-status labels, anatomy selection, and launch of component inspection. | An active case for patient-bound content; an honest no-case state is valid. | Hypothetical controls, paired comparison, evidence ranking, or journey report composition. |
| `EXPERIMENT` | “What changes under this bounded hypothetical?” | Scenario definition and controls, deterministic causal result, plausible-twin ensemble workflow, Shadow Trial execution, effect summaries, and valid-pair selection. | An immutable origin snapshot selected in `TWIN`. | Side-by-side Split Heart interaction, evidence-priority interpretation, or report composition. |
| `COMPARE` | “How does one valid baseline/counterfactual pair differ?” | Split Heart presentation, linked or independent semantic selection, comparison clock, paired metrics, difference-only view, and pair-specific signal/provenance context. | A valid persisted Shadow Trial pair selected in `EXPERIMENT`. | Running or editing the experiment, recalculating physiology, ranking evidence, or generating new conclusions. |
| `EVIDENCE` | “What supports this view, what is uncertain, and what evidence would constrain the model?” | Cross-artifact provenance inspection, source lineage, completeness and limitations, local sensitivity, uncertainty-impact heuristic, and Evidence Priority Score for a selected modeled target. | The active origin plus a persisted ensemble; pair-effect analysis additionally requires its persisted Shadow Trial. | Data ingestion, diagnosis, treatment or measurement recommendations, expected information gain, or posterior claims. |
| `REPORT` | “What reviewable record captures this journey?” | Read-only assembly and ordering of the selected origin, scenario, ensemble/trial, pair comparison, evidence result, provenance, limitations, artifact IDs, and safety disclaimer. | A coherent artifact chain from the mandatory journey. | New physiology, new inference, artifact editing, provenance repair, or replacing any source artifact. |

### Shared-shell ownership

The shared shell owns only cross-space concerns: the active case indicator,
primary navigation, global status, responsive chrome, safety access, and
contextual utility launchers. It does not own clinical or numerical content.

The active case and selected artifact chain survive primary-space navigation.
Changing the active case is an explicit action and clears incompatible
downstream selections; ordinary navigation never silently resets or creates
artifacts. Detailed preservation and invalidation rules belong to the M9
product-state contract.

## Navigation contract

The primary navigation always contains the same five labels in the same order:

```text
TWIN  →  EXPERIMENT  →  COMPARE  →  EVIDENCE  →  REPORT
```

- `TWIN` is the default destination and is always usable.
- All five destinations remain visible even when a prerequisite is missing.
  A destination without enough context shows an honest empty state, names the
  missing prerequisite, and provides one action back to the owning space.
- Selecting a primary destination changes the work surface without changing
  the active case, origin snapshot, or valid downstream artifacts.
- Browser Back/Forward and direct links must restore the named space. If an
  artifact ID is absent, stale, mismatched, or unauthorized, the space fails
  closed to its prerequisite state; it does not substitute another artifact.
- A summary card in a non-owning space links to its owner. It must not look like
  another primary destination or open a competing full-page workflow.
- Every space keeps source lineage and the canonical safety disclaimer
  available. `EXPERIMENT`, `COMPARE`, `EVIDENCE`, and `REPORT` must preserve
  the hypothetical/simulated boundary in visible language.

### Local hierarchy by space

Local controls are subordinate to the primary space and do not become primary
navigation items:

- `TWIN`: current state first, timeline second, component details on demand.
  “Physiology Simulation” is a view of the selected twin, not a sixth space.
- `EXPERIMENT`: scenario first, plausible twins second, Shadow Trial third.
  This order reflects the artifact prerequisites.
- `COMPARE`: paired hearts first, differences second, signal/provenance context
  third.
- `EVIDENCE`: provenance and coverage first, uncertainty drivers and local
  sensitivity second, evidence priorities third.
- `REPORT`: journey summary first, supporting artifact sections second,
  sources/limitations/safety last. These sections are one report, not tabs that
  behave as separate destinations.

## Hidden from primary navigation

The following remain reachable only in context, by direct link, or behind a
feature/developer boundary. None may become a sixth primary item:

- Case creation, upload, intake, and case switching: launched from the shared
  case control, then returns to `TWIN`.
- Component inspector and the existing component-report panel: opened from a
  selected anatomy item in `TWIN` or `COMPARE`. A component report is a detail
  overlay and is distinct from the primary `REPORT` space.
- Scenario inspector, causal graph, ensemble sample picker, Shadow Trial pair
  picker, and Missing Piece target controls: nested in their owning spaces.
- Provenance drawers, assumptions, raw artifact IDs, and source-detail panels:
  contextual disclosures, primarily linked to `EVIDENCE`.
- Cardiology Copilot, the unified assistant, suggested actions, and generated
  artifact detail: contextual utilities that may move the user to an owning
  space but never replace the five-space navigation.
- Agent trace, Weave evaluation, Redis status, system checks, diagnostics, and
  observability: demo/developer utilities, not patient-journey destinations.
- Safety disclaimer modal, loading, empty, error, unavailable, and permission
  states: application states, not destinations.
- CareGuard console, runner, and case-browser routes: separate feature-gated
  product surfaces outside the M9 cardiac-twin journey.
- Settings, account, help, and deployment/admin controls: utility destinations
  if later needed, never primary M9 spaces.

Hidden means absent from the five-item primary navigation, not removed or
concealed from users who need the function. Contextual controls must remain
keyboard reachable, named, and discoverable from their owning surface.

## Mandatory journey

The acceptance journey is one continuous, reversible chain:

```text
TWIN
  selected case + immutable origin snapshot
    ↓
EXPERIMENT
  bounded scenario + persisted ensemble + Shadow Trial + selected valid pair
    ↓
COMPARE
  inspected baseline/counterfactual pair
    ↓
EVIDENCE
  selected modeled target + provenance + uncertainty analysis
  + evidence-priority result
    ↓
REPORT
  deterministic report over the exact artifact chain
    ↓
TWIN
  return to the same case and origin snapshot without mutation
```

The required actions are:

1. In `TWIN`, activate a case, select an eligible source snapshot, and verify
   its observed/derived/interpolated/synthetic lineage.
2. Continue to `EXPERIMENT`, fork that snapshot, apply a bounded hypothetical,
   generate or select its persisted plausible-twin ensemble, run the
   same-sample Shadow Trial, and select one valid pair.
3. Continue to `COMPARE` and inspect the pair identity, baseline and
   counterfactual states, modeled deltas, and limitations.
4. Continue to `EVIDENCE`, select the modeled target to explain, and inspect
   the artifact provenance, coverage, local sensitivity, uncertainty-impact
   heuristic, Evidence Priority Score, and limitations for that target.
5. Continue to `REPORT` and open the report bound to those exact artifact IDs.
   The report must include source classifications, hypothetical/simulated
   labels, unavailable fields, limitations, and the safety disclaimer.
6. Use `Return to Twin` to restore the same case and origin snapshot. The
   scenario, trial, evidence result, and report remain available as downstream
   artifacts, but none modifies the observed timeline.

This sequence is the mandatory end-to-end acceptance path, not a locked
wizard. Users may revisit an earlier space. If they change an upstream
selection, incompatible downstream artifacts become explicitly stale or
unavailable; they are never silently rebound. Existing valid artifacts may be
opened directly by deep link, subject to the same identity checks.

## Acceptance checks

M9 satisfies this information architecture only when all of the following are
true:

- Primary navigation contains exactly the five specified spaces, in order.
- Each space presents its owned capability and links out for non-owned work.
- Missing prerequisites produce truthful states and a clear recovery action.
- The mandatory journey can be completed without returning to an old dashboard
  or opening a hidden utility as a required step.
- Direct links and browser history preserve space and artifact identity without
  placing sensitive payloads in the URL.
- `Return to Twin` restores the original source context without mutating it.
- No surface relabels simulated output as observed evidence, an uncertainty
  heuristic as probability/information gain, or any output as diagnosis or
  treatment guidance.
