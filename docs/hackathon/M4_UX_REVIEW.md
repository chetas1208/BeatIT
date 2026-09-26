# M4 UX accessibility review

**Scope:** Static review of the ScenarioPanel controls, causal graph, scenario
inspector, and responsive layout. No code was modified.

## Findings and dispositions

1. **Scenario controls do not expose the full state.** Each range has an
   accessible name, but the displayed baseline and delta are adjacent visual
   text, not described by the slider; changing a value also has no announced
   result. (`ParameterControls.tsx:29-49`)
   **Disposition:** Fix before acceptance. Associate current/baseline/delta
   text with each input and provide a concise status announcement after
   `Experiment`, `Reset`, `Undo`, or `Redo`.

2. **The causal graph has weak semantics for non-visual users.** The graph is
   a labelled generic `div`; its causal arrows are explicitly hidden from
   assistive technology, so the node sequence and relationships are not
   presented as a structured graph or equivalent text. (`CausalGraph.tsx:10-31`)
   **Disposition:** Fix before demo. Expose the graph as a named region with
   an ordered/list representation or hidden relationship text such as
   “preload affects end-diastolic volume,” while retaining the visual paths.

3. **The inspector/layout creates a difficult narrow and zoomed experience.**
   The desktop center rail contains the vertically scrolling ScenarioPanel,
   while each delta table enforces a `42rem` minimum and adds horizontal
   scrolling. This can require nested scrolling and lose table context at
   mobile widths or 200% zoom. (`AppShell.tsx:134-161`, `Panel.tsx:86-89`,
   `ScenarioInspector.tsx:69-72`)
   **Disposition:** Fix before demo. Keep one predictable scroll path and
   reflow the delta table into stacked metric rows below the responsive
   breakpoint; verify keyboard navigation at 320 CSS px and 200% zoom.
