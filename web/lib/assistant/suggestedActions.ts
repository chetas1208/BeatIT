/*
 * Pure mapping from the accumulated assistant context to 2-4 contextual
 * suggestion chips, per docs/assistant/GLOBAL_ARCHITECTURE.md's "INTERACTIVE
 * SUGGESTIONS" examples (component selected -> "Explain this component" /
 * "Show evidence" / "Compare over time" / "Why uncertain?"; compare/pair
 * context -> "Explain the difference" / "Show causal path" / "Inspect PV
 * change"). No I/O, no React — safe to call from a component, a test, or
 * SuggestedActionChips.tsx alike.
 *
 * Deliberately no heuristics beyond what the spec names: snapshot_id or
 * target_metric alone (without a selected component or open pair) fall
 * through to the generic starter set below, rather than inventing a third
 * bespoke suggestion list the spec never described.
 */

export interface SuggestedAction {
  label: string;
  /** Prompt text to send into the chat when this chip is chosen. */
  action: string;
}

export interface SuggestedActionsContext {
  component_id?: string | null;
  snapshot_id?: string | null;
  pair_id?: string | null;
  target_metric?: string | null;
  product_space?: string | null;
}

const COMPONENT_ACTIONS: readonly SuggestedAction[] = [
  { label: "Explain this component", action: "Explain this component" },
  { label: "Show evidence", action: "Show evidence" },
  { label: "Compare over time", action: "Compare over time" },
  { label: "Why uncertain?", action: "Why uncertain?" },
];

const PAIR_ACTIONS: readonly SuggestedAction[] = [
  { label: "Explain the difference", action: "Explain the difference" },
  { label: "Show causal path", action: "Show causal path" },
  { label: "Inspect PV change", action: "Inspect PV change" },
];

const GENERIC_ACTIONS: readonly SuggestedAction[] = [
  { label: "What's the current EF?", action: "What's the current EF?" },
  { label: "Explain this twin", action: "Explain this twin" },
  { label: "Show recent findings", action: "Show recent findings" },
];

/**
 * Pair context wins over component context when both are set — an open
 * comparison is the more specific state a user is looking at. Falls back to
 * generic starters otherwise.
 */
export function getSuggestedActions(
  context: SuggestedActionsContext,
): SuggestedAction[] {
  if (context.pair_id) return [...PAIR_ACTIONS];
  if (context.component_id) return [...COMPONENT_ACTIONS];
  return [...GENERIC_ACTIONS];
}
