# M2 component interaction

Interaction states are `none → hover → selected → focused`. Pointer hover updates only the semantic ID; click selects and focuses; ESC and background pointer misses reset the selection. The selected component opens a progressive inspector with anatomy, current twin state, findings, provenance, limitations, and a report action.

The current procedural heart does not contain independently authored chamber meshes. M2 therefore uses an explicit semantic proxy layer, documented as a geometry limitation. Proxy IDs are stable and renderer-facing; UI code never depends on raw mesh names.

The camera controller interpolates toward component focus targets and returns to the default pose on deselection. Electrical nodes use the same cardiac clock as contraction and flow and are visualization-only, not a patient-specific electrophysiology solver.
