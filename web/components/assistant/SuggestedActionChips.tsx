"use client";

/*
 * Presentational only: renders getSuggestedActions()'s output as clickable
 * chips and reports the choice via onSelect. Wiring onSelect into an actual
 * chat panel (Agent 16's conversation component, once it lands) is left to
 * whoever integrates this — this component takes context as a plain prop and
 * has no store subscription of its own, so it works the same whether that
 * context comes from useCurrentAssistantContext() (web/lib/assistant/
 * contextEvents.ts) or a hardcoded value in a test/story.
 */

import {
  getSuggestedActions,
  type SuggestedActionsContext,
} from "@/lib/assistant/suggestedActions";

interface SuggestedActionChipsProps {
  context: SuggestedActionsContext;
  onSelect: (action: string) => void;
  className?: string;
}

export function SuggestedActionChips({
  context,
  onSelect,
  className = "",
}: SuggestedActionChipsProps) {
  const actions = getSuggestedActions(context);
  if (actions.length === 0) return null;

  return (
    <div
      className={`flex flex-wrap items-center gap-1.5 ${className}`}
      role="group"
      aria-label="Suggested questions"
    >
      {actions.map((suggestion) => (
        <button
          key={suggestion.action}
          type="button"
          data-status="idle"
          onClick={() => onSelect(suggestion.action)}
          className="ht-chip cursor-pointer transition-colors hover:border-[var(--ht-signal-line)] hover:text-ink"
        >
          {suggestion.label}
        </button>
      ))}
    </div>
  );
}
