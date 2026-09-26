"use client";

import { useCallback, useEffect, useState } from "react";
import type { HeartSelectionState } from "@/lib/heart/contracts";
import { clearHover, focusComponent, hoverComponent, resetHeartInteraction, selectComponent } from "@/components/heart/interaction/selection";

const INITIAL: HeartSelectionState = { selectedId: null, hoveredId: null, focusedId: null, mode: "none" };

export function useHeartInteraction() {
  const [state, setState] = useState<HeartSelectionState>(INITIAL);
  const hover = useCallback((id: string | null) => setState((current) => id ? hoverComponent(current, id) : clearHover(current)), []);
  const select = useCallback((id: string) => setState((current) => focusComponent(selectComponent(current, id), id)), []);
  const clear = useCallback(() => setState(resetHeartInteraction()), []);
  const resetFocus = useCallback(() => setState((current) => ({ ...current, focusedId: null, mode: current.selectedId ? "selected" : "none" })), []);
  useEffect(() => { const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") clear(); }; window.addEventListener("keydown", onKeyDown); return () => window.removeEventListener("keydown", onKeyDown); }, [clear]);
  return { state, hover, select, clear, resetFocus };
}
