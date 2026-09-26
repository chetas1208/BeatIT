"use client";

/*
 * Frontend half of apply_context_event(context, event_type, value)
 * (python/hearttwin/assistant/context_resolver.py) — see
 * docs/assistant/wave3/context-and-orchestration.md for the backend function this
 * mirrors, and docs/assistant/wave4/contextual-interaction.md for the exact
 * component click / timeline scrub / pair-open call sites a future wave must edit
 * to actually call emitContextEvent from real user interactions. Nothing in this
 * repo calls emitContextEvent yet — this module is standalone this wave.
 *
 * Built on Zustand (already the store primitive for web/lib/store.ts and
 * web/lib/twin/comparison/store.ts) rather than a hand-rolled listener array:
 * store.getState()/setState() work outside any component, so emitContextEvent
 * stays a plain, framework-agnostic function callable from a Three.js pointer
 * handler or a bare onChange, while useContextEvent/useCurrentAssistantContext
 * stay thin hook wrappers around the same store — the same split every other
 * store in this codebase already uses.
 */

import { useEffect, useRef } from "react";
import { create } from "zustand";
import type { ConversationContext } from "@/types/assistant";

/**
 * Matches python/hearttwin/assistant/context_resolver.py's ContextEventType
 * exactly (five event types, one target field each). Do not add a sixth here
 * without adding it to _EVENT_FIELD on the backend first — the two lists must
 * stay identical.
 */
export type ContextEventType =
  | "component_selected"
  | "snapshot_selected"
  | "pair_opened"
  | "scenario_created"
  | "target_metric_changed";

export interface AssistantContextEvent {
  event_type: ContextEventType;
  value: string;
  /** Client receive time (ms epoch); local bookkeeping only, not sent to the backend. */
  at: number;
}

/**
 * The 5 ConversationContext fields these events touch, derived from Agent 16's
 * real `ConversationContext` (web/types/assistant.ts, landed mid-task — this
 * file was updated to reuse it rather than keep the local placeholder type it
 * started with) so field names/types have exactly one source of truth. Not the
 * full ConversationContext itself: this store only ever accumulates from UI
 * events, so it never learns `conversation_id`/`audience`/etc. — those belong
 * to the conversation session, not a click/scrub/pair-open event.
 */
export type AssistantContext = Pick<
  ConversationContext,
  "component_id" | "snapshot_id" | "pair_id" | "scenario_id" | "target_metric"
>;

const EMPTY_CONTEXT: AssistantContext = {
  component_id: null,
  snapshot_id: null,
  pair_id: null,
  scenario_id: null,
  target_metric: null,
};

// One event maps to exactly one context field — a lookup table, not an
// if/elif chain, mirroring _EVENT_FIELD in context_resolver.py so the two can
// be diffed at a glance.
const EVENT_FIELD: Record<ContextEventType, keyof AssistantContext> = {
  component_selected: "component_id",
  snapshot_selected: "snapshot_id",
  pair_opened: "pair_id",
  scenario_created: "scenario_id",
  target_metric_changed: "target_metric",
};

interface ContextEventStore {
  context: AssistantContext;
  lastEvent: AssistantContextEvent | null;
  emit: (eventType: ContextEventType, value: string) => void;
}

const useContextEventStore = create<ContextEventStore>((set) => ({
  context: EMPTY_CONTEXT,
  lastEvent: null,
  emit: (event_type, value) =>
    set((state) => ({
      context: { ...state.context, [EVENT_FIELD[event_type]]: value },
      lastEvent: { event_type, value, at: Date.now() },
    })),
}));

/**
 * Records one UI context-update event and folds it into the accumulated
 * session context. Callable from anywhere — not just inside a React component
 * — matching how a canvas pointer handler or a plain onChange would call it.
 *
 * This does NOT post to the backend `apply_context_event` endpoint (none
 * exists yet per docs/assistant/wave3/context-and-orchestration.md) — it only
 * keeps the frontend's own accumulated context in sync so
 * useCurrentAssistantContext() and getSuggestedActions() have something to
 * read this wave. A future wave that adds the endpoint should call it from
 * here, in `emit`, alongside (or instead of) the local state update.
 */
export function emitContextEvent(eventType: ContextEventType, value: string): void {
  useContextEventStore.getState().emit(eventType, value);
}

/**
 * Subscribes `callback` to every future emitted event. Only events emitted
 * after the hook mounts are delivered — no replay of prior session history —
 * matching how useTraceStream treats new live events vs. the backfilled store.
 */
export function useContextEvent(callback: (event: AssistantContextEvent) => void): void {
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    return useContextEventStore.subscribe((state, previous) => {
      if (state.lastEvent && state.lastEvent !== previous.lastEvent) {
        callbackRef.current(state.lastEvent);
      }
    });
  }, []);
}

/** The accumulated context built from every event emitted so far this session. */
export function useCurrentAssistantContext(): AssistantContext {
  return useContextEventStore((state) => state.context);
}
