"use client";

/*
 * useFocusTrap — keeps keyboard focus inside a container while `active`
 * (for the slide-in chat panel / any dialog-like surface under
 * components/assistant), closes on Escape, and restores focus to whatever
 * was focused before the panel opened (the trigger button) once it closes
 * or unmounts.
 *
 * nextTrapFocusTarget is exported standalone so the tab-cycling decision can
 * be unit-tested without a real DOM — it only compares element identity.
 */

import { useEffect, useRef, type RefObject } from "react";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

export function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
}

/**
 * Given the focusable elements in tab order, where the browser's default Tab
 * handling would leave the trap (or nowhere yet), returns the element to
 * refocus — or null when the default browser behavior already stays inside
 * the trap and nothing needs overriding.
 */
export function nextTrapFocusTarget(
  focusable: readonly HTMLElement[],
  active: Element | null,
  shiftKey: boolean,
): HTMLElement | null {
  if (focusable.length === 0) return null;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const index = active ? focusable.indexOf(active as HTMLElement) : -1;

  if (shiftKey) {
    return index <= 0 ? last : null;
  }
  return index === -1 || index === focusable.length - 1 ? first : null;
}

export function useFocusTrap(
  containerRef: RefObject<HTMLElement | null>,
  active: boolean,
  onClose: () => void,
): void {
  const restoreRef = useRef<HTMLElement | null>(null);
  // Ref so the effect doesn't need onClose in its dependency array — callers
  // pass a fresh closure on every render. Synced in its own effect (not
  // during render) since mutating a ref while rendering is disallowed.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    if (!active) return;
    const container = containerRef.current;
    if (!container) return;

    restoreRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;

    const focusable = getFocusableElements(container);
    (focusable[0] ?? container).focus({ preventScroll: true });

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;

      const target = nextTrapFocusTarget(
        getFocusableElements(container),
        document.activeElement,
        event.shiftKey,
      );
      if (target) {
        event.preventDefault();
        target.focus();
      }
    };

    // Capture phase so this wins even if a child stops propagation on bubble.
    document.addEventListener("keydown", handleKeyDown, true);
    return () => {
      document.removeEventListener("keydown", handleKeyDown, true);
      restoreRef.current?.focus({ preventScroll: true });
      restoreRef.current = null;
    };
  }, [active, containerRef]);
}
