import type { HeartInteractionMode, HeartSelectionState } from "@/lib/heart/contracts";

export const EMPTY_HEART_SELECTION: HeartSelectionState = {
  selectedId: null,
  hoveredId: null,
  focusedId: null,
  mode: "none",
};

function modeFor(state: Omit<HeartSelectionState, "mode">): HeartInteractionMode {
  if (state.focusedId) return "focused";
  if (state.selectedId) return "selected";
  if (state.hoveredId) return "hover";
  return "none";
}

function withDerivedMode(
  state: Omit<HeartSelectionState, "mode">,
): HeartSelectionState {
  return { ...state, mode: modeFor(state) };
}

export function selectComponent(
  state: HeartSelectionState,
  componentId: string,
): HeartSelectionState {
  if (!componentId) return state;
  return withDerivedMode({ ...state, selectedId: componentId });
}

export function deselectComponent(
  state: HeartSelectionState,
  componentId?: string,
): HeartSelectionState {
  if (componentId && state.selectedId !== componentId) return state;
  return withDerivedMode({ ...state, selectedId: null });
}

export function hoverComponent(
  state: HeartSelectionState,
  componentId: string,
): HeartSelectionState {
  if (!componentId) return state;
  return withDerivedMode({ ...state, hoveredId: componentId });
}

export function clearHover(state: HeartSelectionState): HeartSelectionState {
  return withDerivedMode({ ...state, hoveredId: null });
}

export function focusComponent(
  state: HeartSelectionState,
  componentId: string,
): HeartSelectionState {
  if (!componentId) return state;
  return withDerivedMode({ ...state, focusedId: componentId });
}

export function clearFocus(state: HeartSelectionState): HeartSelectionState {
  return withDerivedMode({ ...state, focusedId: null });
}

/** Clears transient and persistent interaction state. Safe for ESC and background clicks. */
export function resetHeartInteraction(): HeartSelectionState {
  return EMPTY_HEART_SELECTION;
}

export interface InteractionController {
  getState(): HeartSelectionState;
  subscribe(listener: (state: HeartSelectionState) => void): () => void;
  select(componentId: string): void;
  deselect(componentId?: string): void;
  hover(componentId: string): void;
  clearHover(): void;
  focus(componentId: string): void;
  clearFocus(): void;
  reset(): void;
  handleEscape(event: Pick<KeyboardEvent, "key" | "preventDefault">): boolean;
  handleBackgroundPointerDown(): void;
}

export function createInteractionController(
  initialState: HeartSelectionState = EMPTY_HEART_SELECTION,
): InteractionController {
  let state = { ...initialState, mode: modeFor(initialState) };
  const listeners = new Set<(nextState: HeartSelectionState) => void>();

  const update = (nextState: HeartSelectionState): void => {
    if (
      nextState.selectedId === state.selectedId &&
      nextState.hoveredId === state.hoveredId &&
      nextState.focusedId === state.focusedId &&
      nextState.mode === state.mode
    ) {
      return;
    }
    state = nextState;
    listeners.forEach((listener) => listener(state));
  };

  return {
    getState: () => state,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    select: (componentId) => update(selectComponent(state, componentId)),
    deselect: (componentId) => update(deselectComponent(state, componentId)),
    hover: (componentId) => update(hoverComponent(state, componentId)),
    clearHover: () => update(clearHover(state)),
    focus: (componentId) => update(focusComponent(state, componentId)),
    clearFocus: () => update(clearFocus(state)),
    reset: () => update(resetHeartInteraction()),
    handleEscape: (event) => {
      if (event.key !== "Escape") return false;
      event.preventDefault();
      update(resetHeartInteraction());
      return true;
    },
    handleBackgroundPointerDown: () => update(resetHeartInteraction()),
  };
}
